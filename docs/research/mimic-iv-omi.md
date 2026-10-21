# What MIMIC-IV-ECG and linked MIMIC-IV data can say about OMI

Research for [the-dr-lazy/delmir#11](https://github.com/the-dr-lazy/delmir/issues/11), carried out 2026-10-21 from public documentation, schemas, the open [MIMIC-IV demo](https://physionet.org/content/mimic-iv-demo/2.2/), the CMS code tables and published papers. Credentialed access ([#2](https://github.com/the-dr-lazy/delmir/issues/2)) is not granted yet, so nothing here was counted on the full credentialed data. Demo figures come from 100 patients and only show shape, never rates. Every claim links to its source, and anything I could not confirm is marked **unverified**.

## Answer

**MIMIC-IV can give proxy labels for MI, for STEMI by wall or artery, and for "PCI of an acute occlusion during AMI". It cannot give angiography-confirmed labels.** No released module holds catheterisation reports, and no table has coronary dominance, a lesion segment or TIMI flow. So none of the three facts [#4](https://github.com/the-dr-lazy/delmir/issues/4) needs to derive a culprit vessel is available as data.

What it can give:

- **MI and STEMI by coded diagnosis.** ICD-10-CM codes name the artery for STEMI: I21.01 left main, I21.02 LAD, I21.11 RCA, I21.21 LCx. NSTEMI is I21.4 and type 2 MI is I21.A1. ICD-9-CM 410.xy names only the wall. These diagnoses cover a whole stay and carry no time.
- **A conventional troponin T with timestamps.** Itemid 51003, in ng/mL, with a 99th percentile below 0.01 and ">0.10 suggests acute MI", charted to the minute. Troponin I is essentially absent.
- **Catheterisation and PCI by date only.** These come from `procedures_icd` (ICD-9 or ICD-10-PCS) and `hcpcsevents` (CPT/HCPCS). ICD-10-PCS counts arteries but never names them. The HCPCS vessel modifiers (LC, LD, LM, RC, RI) are not released. One code, **C9606**, and its CPT analogue 92941 (unverified), bills PCI of an *acute total or subtotal occlusion during AMI*. That is the closest structured signal to OMI anywhere in MIMIC-IV.
- **Possibly some cath findings in free text.** Discharge summaries are the only released notes that might quote cath findings (culprit, TIMI). That is unverified: no public sample shows it, and it needs credentialed access and a measuring pass.

**Nobody has published OMI or culprit-vessel labels from MIMIC-IV.** Every MIMIC MI label I found comes from discharge ICD codes, and the largest effort is Strodthoff et al. 2024 with MIMIC-IV-ECG-Ext-ICD. The OMI and culprit models (Al-Zaiti 2023, Herman 2024, Gustafsson 2026) all use private cohorts where the angiography was adjudicated.

**What this means for [#30](https://github.com/the-dr-lazy/delmir/issues/30).** MIMIC-IV labels are always **proxy labels** in the glossary's sense:

- **OMI** can be approximated by combinations such as: an index ECG in the ED, then same-stay PCI (best of all C9606/92941), a STEMI or NSTEMI code, and a rising troponin T. TIMI flow is never in the data.
- **Culprit vessel** can be approximated only for coded STEMIs in the ICD-10 era, through the artery-named I21 subcodes. These map to #4's outcomes, but they come from billing and not from the lesion.
- **STEMI-negative OMI** cannot be told apart from NOMI with any structured field. NSTEMI coding plus occlusion-PCI billing (C9606/92941) is the only lead.

## 1. Modules and access

| Module | Version | Access | What matters for OMI |
|---|---|---|---|
| [MIMIC-IV-ECG](https://physionet.org/content/mimic-iv-ecg/1.0/) | 1.0 (2023-09-15) | **Open** (ODbL 1.0): "Anyone can access the files". v1.0 removed sensitive free text and "the project access has been changed to open instead of requiring credentialling" | Waveforms, machine statements and measurements, ECG times, note links |
| [MIMIC-IV](https://physionet.org/content/mimiciv/3.1/) (hosp, icu) | 3.1 (2024-10-11) | Credentialed, with CITI training and DUA | Admissions, `labevents` (troponin), `diagnoses_icd`, `procedures_icd`, `hcpcsevents`, `icu.procedureevents`. Covers 2008–2022 (v3.0 added 2020–2022) |
| [MIMIC-IV-ED](https://physionet.org/content/mimic-iv-ed/2.2/) | 2.2 | Credentialed | `edstays` (in and out times), `diagnosis` (ED discharge ICD), triage, vitals. Covers 2011–2019. **No lab table**: ED labs are in `hosp.labevents` |
| [MIMIC-IV-Note](https://physionet.org/content/mimic-iv-note/2.2/) | 2.2 | Credentialed | Only `discharge` (331,794) and `radiology` (2,321,355) notes. **No ECG, cath or echo reports** |
| [MIMIC-IV-ECHO](https://physionet.org/content/mimic-iv-echo/1.0.1/) | 1.0.1 | Credentialed | DICOM TTEs for 7,228 studies (2017–2019), and `structured_measurement.csv` for 206,488 studies (2008–2022). Reports "will be made available under the MIMIC-IV-Note module", so they are not released yet |
| [MIMIC-IV-ECG-Ext-ICD](https://physionet.org/content/mimic-iv-ecg-ext-icd-labels/1.0.1/) | 1.0.1 (2024-08-30) | Credentialed | Per ECG: linked ED stay and admission, ED and hospital discharge ICD-10-CM lists, `ecg_taken_in_ed`, `ecg_no_within_stay`, patient-level folds |

Issue #2's list of DUAs to sign should also cover **MIMIC-IV-ECG-Ext-ICD**, which saves rebuilding the ECG-to-stay link, and **MIMIC-IV-ECHO**, for LV function.

## 2. What MIMIC-IV-ECG alone contains

From the [project page](https://physionet.org/content/mimic-iv-ecg/1.0/) and the [module docs](https://mimic.mit.edu/docs/iv/modules/ecg/):

- **Size and format.** About 800,000 diagnostic 12-lead ECGs from about 160,000 patients, recorded 2008–2019. Each is 10 s at 500 Hz, stored as WFDB (`.hea` + `.dat`), 90.4 GB in all. About 5% are held back as a hidden test set. The ECGs are both "inpatient and outpatient" ([record_list docs](https://mimic.mit.edu/docs/iv/modules/ecg/record_list.html)).
- **`record_list.csv`.** Columns `subject_id, study_id, file_name, ecg_time, path`.
- **`machine_measurements.csv`.** Columns:
  - `subject_id, study_id, cart_id, ecg_time`
  - `report_0` … `report_17`: one machine statement per column
  - `bandwidth, filtering`
  - `rr_interval, p_onset, p_end, qrs_onset, qrs_end, t_end` in ms
  - `p_axis, qrs_axis, t_axis` in degrees

  These are global measurements only; per-lead values "may be released in a future version". **No ST amplitude is released.** ST information exists only as statement text, for example "\*\*\* CONSIDER ACUTE ST ELEVATION MI \*\*\*", "Inferior ST elevation, CONSIDER ACUTE INFARCT", "Anterior infarct, old" and "Lateral ST-T changes suggest myocardial injury/ischemia" ([preview](https://physionet.org/content/mimic-iv-ecg/1.0/machine_measurements.csv), [dictionary](https://physionet.org/files/mimic-iv-ecg/1.0/machine_measurements_data_dictionary.csv)). In the preview, `29999` and `32767` look like sentinels for missing values; that is my reading and is not documented.
- **`waveform_note_links.csv`.** Columns `subject_id, study_id, waveform_path, note_id, note_seq, charttime`; note ids look like `10000032-EK-4` ([docs](https://mimic.mit.edu/docs/iv/modules/ecg/waveform_note_links.html)). "A little more than 600,000 cardiologist reports are available for the ~800,000 diagnostic ECGs", but the report text itself has **not been released**. It is promised for MIMIC-IV-Note "at a later date", and a maintainer confirmed it was "not released publicly yet" ([mimic-code#1728](https://github.com/MIT-LCP/mimic-code/issues/1728)). For now the links only show *that* a cardiologist read an ECG.

Machine statements are an ECG-derived label, and so they are circular as an OMI target. They are useful only as a baseline: a "STEMI-criteria machine" comparator in the spirit of ADR 0001.

## 3. Linking ECGs to patients, ED stays and admissions

- **Keys.** `subject_id` is matched by medical record number. No ECG file has `hadm_id` or `stay_id`, so an ECG links to `hosp.admissions` (`admittime` to `dischtime`) and `ed.edstays` (`intime` to `outtime`) by `subject_id` and a time window ([project page](https://physionet.org/content/mimic-iv-ecg/1.0/)). MIMIC-IV-ECG-Ext-ICD has already done this "by comparing recording times to patient admission, discharge, and potential death times", but it does not publish its window ([Ext-ICD](https://physionet.org/content/mimic-iv-ecg-ext-icd-labels/1.0.1/)).
- **Overlap.** "Approximately 55% of the ECGs overlap with a hospital admission and 25% overlap with an emergency department visit"; the rest are outpatient or otherwise outside a stay ([project page](https://physionet.org/content/mimic-iv-ecg/1.0/)). MIMIC-IV-ED only covers 2011–2019.
- **Date shifting.** There is one shift per patient, into 2100–2200, and intervals within a patient are kept ([MIMIC-IV](https://physionet.org/content/mimiciv/3.1/), [record_list docs](https://mimic.mit.edu/docs/iv/modules/ecg/record_list.html)). Calendar time across patients is lost. For example, whether a stay is in the ICD-9 or ICD-10 era can only be read from `icd_version`.
- **Precision.** `ecg_time` is stored to the second, but the preview rows all end in `:00`, which in practice means minute resolution (observed, not documented). Lab `charttime` and `storetime` are `TIMESTAMP(0)`, and `edstays` times are timestamps.
- **Clock caveat.** The project page warns: "The date and time for each ECG were recorded by the machine's internal clock, which in most cases was not synchronized with any external time source. As a result, the ECG time stamps could be significantly out of sync with the corresponding time stamps in the MIMIC-IV Clinical Database" ([project page](https://physionet.org/content/mimic-iv-ecg/1.0/), checked verbatim). No size is given. Any ECG-before-troponin or ECG-in-ED-stay rule needs padding, and #30 should measure the offset once it has access, for example the ECG-time minus ED-`intime` distribution.

## 4. Troponin in `labevents`

- **Itemids** ([demo d_labitems](https://physionet.org/files/mimic-iv-demo/2.2/hosp/d_labitems.csv.gz)):
  - 51003 Troponin T
  - 51002 and 52642 Troponin I
  - 52598 Troponin I point-of-care
  - also 50911 CK-MB and 50963 NT-proBNP

  The official concept [`cardiac_marker.sql`](https://github.com/MIT-LCP/mimic-code/blob/main/mimic-iv/concepts/measurement/cardiac_marker.sql) uses only 51003. It notes that troponin I "is not measured in MIMIC-IV" and that 52598 is "rare/poor quality". In the demo, all 278 troponin rows are 51003.
- **Assay and thresholds.** A maintainer says the 51003 rows "are all the same assay" and that it is a conventional, not high-sensitivity, test. He quotes the BIDMC lab manual: 99th percentile <0.01 ng/mL, MI >0.10 ng/mL, and 0.01–0.10 a grey zone ([mimic-code#935](https://github.com/MIT-LCP/mimic-code/issues/935)). The result comment usually says "cTropnT > 0.10 ng/mL suggests Acute MI". **Unverified**: whether a high-sensitivity assay arrived during 2020–2022, because v3.x `d_labitems` is credentialed. That matters only for ECG-less years, since MIMIC-IV-ECG ends in 2019.
- **Shape of the values.**
  - Unit `ng/mL`, reference range 0–0.01, and `flag = abnormal` above the range.
  - In the demo, 145 of 278 rows have NULL `valuenum` and keep "<0.01" in `comments`, so a parser must read the comments.
  - `priority` is STAT or ROUTINE.
  - ED-drawn labs can have NULL `hadm_id` (81 of 278 demo rows), so they must be joined by time ([labevents docs](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html)).
- **Timing.** `charttime` is "usually the time at which the specimen was acquired". In the demo, the median wait from `charttime` to `storetime` is 89 min. No documented sampling frequency exists. In the demo there is a median of 2 troponins per encounter with troponin, and a maximum of 13. The full-data frequency around an ECG is for #30 to measure.
- A 2026 audit preprint of MIMIC-IV found 6,189 ED encounters with a dynamic troponin T rise. Only 79.4% had an ECG report linked within −1 h to +2 h, and angiographic thrombus evidence was available for 0 of them ([Research Square rs-11206793](https://www.researchsquare.com/article/rs-11206793/v1), under review).

## 5. Catheterisation and PCI

- **`hosp.procedures_icd`** has the columns `subject_id, hadm_id, seq_num, chartdate DATE, icd_code, icd_version`. It gives a **date only**, the date "does not strictly correlate with seq_num", and it lists only procedures the hospital billed ([docs](https://mimic.mit.edu/docs/iv/modules/hosp/procedures_icd.html)).
  - **ICD-9-CM** ([CMS v32](https://www.cms.gov/medicare/coding/icd9providerdiagnosticcodes/downloads/icd-9-cm-v32-master-descriptions.zip)):
    - 00.66 PTCA; 36.06/36.07 bare-metal or drug-eluting stent; 36.04 intracoronary thrombolysis
    - 37.22/37.23 left, or left and right, heart catheterisation
    - 88.53–88.57 angiocardiography and coronary arteriography
    - 00.40–00.43 vessel counts and 00.45–00.48 stent counts. These are generic, not coronary-specific, and name no artery.
  - **ICD-10-PCS** ([CMS 2026 tables](https://www.cms.gov/files/zip/2026-icd-10-pcs-code-tables-and-index.zip)):
    - `027` Dilation of coronary arteries, where character 4 is the number of arteries (0 one to 3 four or more) and character 6 the device
    - `02C` Extirpation (thrombectomy)
    - `B21` coronary fluoroscopy

    Guideline B4.4 makes the coronary arteries "a single body part that is further specified by number of arteries treated" ([PCS guidelines](https://www.cms.gov/files/document/2025-official-icd-10-pcs-coding-guidelines.pdf)), so **no PCS code names the LAD, LCx or RCA**.
- **`hosp.hcpcsevents`** has the columns `subject_id, hadm_id, chartdate DATE, hcpcs_cd CHAR(5), seq_num, short_description`, with no time and **no modifier column** ([docs](https://mimic.mit.edu/docs/iv/modules/hosp/hcpcsevents.html)).
  - The HCPCS vessel modifiers LC, LD, LM, RC and RI, which would name the treated artery, are therefore lost.
  - CPT descriptions are withheld for licensing reasons ([d_hcpcs](https://mimic.mit.edu/docs/iv/modules/hosp/d_hcpcs.html)).
  - The demo has 93454/93455 (coronary angiography), 92921, 92980 and C9600 ([demo](https://physionet.org/files/mimic-iv-demo/2.2/hosp/hcpcsevents.csv.gz)).
  - **C9606** is "percutaneous transluminal revascularization of acute total/subtotal occlusion during acute myocardial infarction … single vessel" ([CMS HCPCS](https://www.cms.gov/files/zip/october-2026-alpha-numeric-hcpcs-file.zip)). Its CPT analogue **92941** (descriptor not retrieved, **unverified**) is billed when the operator treats an acute occlusion. It is the nearest structured trace of an OMI, though billing practice, not TIMI flow, decides whether it is used.
- **`icu.procedureevents`** has real `starttime`/`endtime`. Items include 225430 "Cardiac Cath", 229577/229578 "Cath Lab (Received)/(Sent)" and 225427 "Angiography" ([docs](https://mimic.mit.edu/docs/iv/modules/icu/procedureevents.html), [demo d_items](https://physionet.org/files/mimic-iv-demo/2.2/icu/d_items.csv.gz)). But it covers only ICU (MetaVision) patients, and "absence does not indicate the procedure was not conducted". In the demo, `endtime` is `starttime` + 1 min, a charting time rather than the procedure time. For a patient who reaches the ICU after the cath lab, "Cath Lab (Sent/Received)" may bound the door-to-cath time; that is unverified on full data.

**Timing consequence.** PCI is known only to the day. "ECG before cath" can be shown only for an ED ECG whose stay ends in an admission with PCI dated the same day or the next. Sub-day ordering, such as "the last ECG before reperfusion", is not possible except from ICU charting.

## 6. Diagnosis codes

From the [CMS FY2026 ICD-10-CM tabular](https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip) and [ICD-9-CM v32](https://www.cms.gov/medicare/coding/icd9providerdiagnosticcodes/downloads/icd-9-cm-v32-master-descriptions.zip). The codes are in `hosp.diagnoses_icd` (stay level) and `ed.diagnosis` (ED discharge).

| Code | Meaning | Maps to #4's rule |
|---|---|---|
| I21.01 | STEMI, left main | reason **left main** |
| I21.02 | STEMI, LAD | **LAD** |
| I21.09 | STEMI, other anterior-wall artery | none (territory only) |
| I21.11 | STEMI, RCA | **RCA** |
| I21.19 | STEMI, other inferior-wall artery | none |
| I21.21 | STEMI, LCx | **LCx** |
| I21.29 / I21.3 | STEMI, other or unspecified site | none |
| I21.4 | NSTEMI | none, and possibly a STEMI-negative OMI |
| I21.9 / I21.A1 / I21.A9 | AMI unspecified / type 2 / other type | Not-OMI candidates (type 2) or uncertain |
| I22.x | Subsequent MI within 4 weeks | uncertain |
| 410.xy (ICD-9) | x = wall (0 anterolateral … 6 true posterior, 7 subendocardial, 9 unspecified); y = episode (1 initial, 2 subsequent) | territory only, so at most an infarct-territory proxy |

The artery subcodes are coded from physician documentation, probably the cath report, but they give the system, not the lesion. Ramus, OM and diagonal culprits land wherever the coder puts them, and graft culprits have no code of their own. I21.B (coronary microvascular dysfunction, FY2025) postdates MIMIC. **Unverified**: how often BIDMC coders used the artery subcodes rather than I21.09/.19/.29. That count is for #30.

## 7. Notes: culprit vessel or TIMI flow in text?

- **Not released**: ECG reports, cath reports, echo reports and cardiology consult notes. MIMIC-IV-Note 2.2 has only discharge and radiology notes ([PhysioNet](https://physionet.org/content/mimic-iv-note/2.2/), [docs](https://mimic.mit.edu/docs/iv/modules/note/), [mimic-code#1678](https://github.com/MIT-LCP/mimic-code/issues/1678)). An HTML comment in the discharge docs mentions OP/AO operating-room note types that are not released ([discharge docs](https://mimic.mit.edu/docs/iv/modules/note/discharge.html)).
- **Discharge summaries** have a hospital course and pertinent results. Report text is known to be pasted into them: echo findings such as "LEFT ATRIUM: Mild \_\_\_" show up there ([mimic-code#1507](https://github.com/MIT-LCP/mimic-code/issues/1507)). So a cath summary ("Cardiac cath: … 100% proximal LAD … TIMI 0 … DES") may be quoted in some summaries. That is **unverified**: no public sample exists, and de-identification replaces some text with `___`.
- **Only route to #4's facts.** Free-text extraction from discharge summaries is the only possible source of culprit segment, dominance and pre-PCI TIMI in MIMIC-IV. Even where it works, it is a proxy in the glossary's sense, a summary written by someone other than the angiographer. #30 should measure, on credentialed data, what fraction of PCI stays mention a culprit artery, a segment (proximal/mid/distal) and TIMI before deciding to build on it.

## 8. Which of #4's angiographic facts MIMIC-IV can supply

| #4 fact | Structured source | Text source | Verdict |
|---|---|---|---|
| Dominance | none | possibly in discharge-summary cath text (unverified) | **No** structured source |
| Culprit finding (none / uncertain / lesions) | partial: PCI on the stay suggests a lesion; cath without PCI suggests none or uncertain (or CABG); C9606/92941 suggests an acute occlusion | possibly | **Proxy only** |
| Culprit lesion SYNTAX segment | none; PCS counts arteries, HCPCS modifiers are dropped | possibly as "proximal LAD"-style text, rarely as segment numbers (unverified) | **No**. System-level proxy only, from I21.01/.02/.11/.21 |
| Graft lesion (kind, native target) | ICD-10-PCS has bypass-graft fluoroscopy (B212/B213), and PCI on a graft is, as far as I know, coded in `027` without the graft named (unverified) | possibly | **No** |
| Pre-PCI TIMI flow | none | possibly | **No** |

So #4's rule cannot run on MIMIC-IV as data. The only vessel labels are ICD-derived proxies at system level, and only for coded STEMIs.

## 9. Published work

| Work | Labels | Window | Positives | Code |
|---|---|---|---|---|
| Strodthoff, Lopez Alcaraz, Haverkamp, *EHJ Digital Health* 2024 ([PMC11284007](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11284007/)) | ED or hospital discharge ICD-10-CM (ICD-9 mapped), 1,076 codes | ECG inside the stay; the label is the whole stay, with no ECG-to-event order | test fold of ED ECGs (7,694 ECGs): I21 282, I21.0 20, I21.1 13, I21.4 196 | [AI4HealthUOL/ECG-MIMIC](https://github.com/AI4HealthUOL/ECG-MIMIC); labels released as [MIMIC-IV-ECG-Ext-ICD](https://physionet.org/content/mimic-iv-ecg-ext-icd-labels/1.0.1/) |
| Lopez Alcaraz et al., MDS-ED ([arXiv 2407.17856](https://arxiv.org/abs/2407.17856)) | Same ICD scheme, 1,428 codes, plus deterioration outcomes | inputs from the first 90 min of the ED stay | I21.09 n=401 | [AI4HealthUOL/MDS-ED](https://github.com/AI4HealthUOL/MDS-ED) |
| McKeen et al., ECG-FM, *JAMIA Open* 2025 ([PMC12530324](https://pmc.ncbi.nlm.nih.gov/articles/PMC12530324)) | Labels parsed from machine statements, including a composite "MI" | same ECG | n/a | [bowang-lab/ECG-FM](https://github.com/bowang-lab/ECG-FM) |
| Lopez Alcaraz & Strodthoff, CardioLab, *Sci Rep* 2025 ([PMC12603147](https://pmc.ncbi.nlm.nih.gov/articles/PMC12603147)) | Lab abnormalities within ±60 min of the ECG; troponin not among them | ±60 min | n/a | [AI4HealthUOL/CardioLab](https://github.com/AI4HealthUOL/CardioLab) |
| Cavarra et al. 2026 ([arXiv 2605.13568](https://arxiv.org/abs/2605.13568)) | MI cohort by I21/410, then mortality and HF outcomes | "ECG recorded after MI diagnosis" | 8,499 MI patients | not found |

Reported AUROCs for Strodthoff's S4 model on ED ECGs ([results CSV](https://github.com/AI4HealthUOL/ECG-MIMIC/blob/main/reports/Results_MIMIC_IV_ECG_ICD.csv)) are I21 0.870, I21.0 0.986, I21.1 0.950 and I21.4 0.847. The authors warn that discharge diagnoses "may include events unrelated to the patient's condition captured by the ED ECG".

OMI and culprit work outside MIMIC, for comparison:

- [Al-Zaiti et al., *Nat Med* 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10353937): Pittsburgh EMS cohorts. OMI is a culprit with TIMI 0–1, or TIMI 2 with >70% stenosis and a high troponin.
- [Herman et al., *EHJ-DH* 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC10944682): the Queen of Hearts model, on Belgian and international cohorts.
- [Gustafsson et al., *Nat Commun* 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13171952): 540,372 Swedish ED ECGs, with OMI and culprit (LM/LAD, LCx, RCA) set at the cath lab, externally tested on PTB-XL and others but not MIMIC.

**Has anyone derived OMI or culprit-vessel labels from MIMIC-IV?** No, as far as Europe PMC full-text, arXiv and web searches show. The closest are the ICD-coded STEMI-wall and NSTEMI labels above, at stay level, with tens of STEMI positives per subcode in a test fold.

## 10. Open questions for #30 (need credentialed access)

These need numbers that only the credentialed data can give:

1. How many ED ECGs have an index stay with PCI (027/02C, or 00.66/36.0x, or 9292x/C96xx), and how many of those have C9606/92941?
2. How often are the artery-named I21 subcodes used, compared with I21.09/.19/.29/.3?
3. How often discharge summaries of PCI stays name a culprit artery, a segment and TIMI flow (a regex or LLM pass over a sample).
4. How many troponins there are per ED stay, the timing of the first troponin against the ECG, and the share of values hidden in `comments`.
5. The ECG clock offset: the distribution of ECG time minus ED `intime` for ECGs that Ext-ICD marks as taken in the ED.

## Unverified

- The CPT 92941 descriptor and its use at BIDMC.
- Whether troponin changed to a high-sensitivity assay after 2019.
- Whether cath text appears in discharge summaries.
- The size of the ECG clock drift.
- The exact number of rows in `waveform_note_links.csv`.
- Whether the machine statements come from more than one vendor's algorithm.
