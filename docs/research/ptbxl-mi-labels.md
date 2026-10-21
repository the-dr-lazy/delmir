# What PTB-XL's labels say about acute MI and infarct territory

Research for [#10](https://github.com/the-dr-lazy/delmir/issues/10), feeding the proxy-label decision in [#21](https://github.com/the-dr-lazy/delmir/issues/21). Researched 2026-10-21.

## Answer in brief

- **PTB-XL's MI labels describe infarcts of every age, and nearly all of them are not acute.**
  - 5,469 records (4,670 patients) carry an MI-superclass statement.
  - Only **150 records (128 patients)** are staged as acute (Stadium I or I–II).
  - 949 are staged old (III), 998 subacute-to-old (II or II–III), and 3,372 (62%) have no age stated ("unknown").
- **"Stadium I" means the reporting cardiologist called the infarct acute or early, often only "possibly acute".**
  - It is not angiography, troponin or OMI.
  - Only 26 of the 171 Stadium I/I–II reports mention ST elevation in words.
- **The INJ\* statements ("subendocardial injury") sit in the MI superclass, but they describe ST depression, not an infarct.**
  - There are 323 records, and 287 of them have no stage.
  - 181 MI-superclass records carry INJ\* and no infarct statement at all.
- **PTB-XL+ adds GE 12SL automatic statements, including `STEMI` ("ACUTE MI / STEMI"), on 178 records (155 patients).**
  - This flag agrees poorly with PTB-XL's acute stage: only 49 records carry both, and the paper reports MCC 0.29.
  - PTB-XL+ also adds per-lead ST amplitudes (J-point, J+80 ms, J+RR/16, J+RR/8), median beats and fiducial points. With these, STEMI criteria can be *computed* as a comparator.
- **Infarct territory gives a defensible proxy culprit vessel only for anterior/anteroseptal statements (→ LAD).**
  - Anterolateral is "probably LAD".
  - Inferior, inferolateral, lateral and posterior are ambiguous between RCA and LCx (or a diagonal).
  - Multi-territory records (997) are ambiguous by construction.
  - The 12SL and cardiologist localisations hardly agree with each other (MCC near 0 to 0.6 by territory).

## Sources and data

| Key | Source |
|---|---|
| [PXL-page] | PhysioNet, PTB-XL v1.0.3 project page: https://physionet.org/content/ptb-xl/1.0.3/ |
| [PXL-paper] | Wagner et al., "PTB-XL, a large publicly available electrocardiography dataset", *Sci Data* 7, 154 (2020): https://www.nature.com/articles/s41597-020-0495-6 |
| [PXL-T4] | Its Table 4, likelihood keywords: https://www.nature.com/articles/s41597-020-0495-6/tables/5 (the site's table URLs are off by one) |
| [PXL-T11] | Its Table 11, infarction stadium: https://www.nature.com/articles/s41597-020-0495-6/tables/12 |
| [PXP-page] | PhysioNet, PTB-XL+ v1.0.1 (latest) project page: https://physionet.org/content/ptb-xl-plus/1.0.1/ |
| [PXP-paper] | Strodthoff et al., "PTB-XL+, a comprehensive electrocardiographic feature dataset", *Sci Data* 10, 279 (2023): https://www.nature.com/articles/s41597-023-02153-8 |
| [PXP-T3/T4] | Its Tables 3 and 4 (12SL vs. cardiologist agreement): https://www.nature.com/articles/s41597-023-02153-8/tables/3, …/tables/4 |
| [ISE-2020] | Birnbaum et al., "A counterpoint paper: Comments on the electrocardiographic part of the 2018 Fourth Universal Definition of Myocardial Infarction", endorsed by ISE and ISHNE, *Ann Noninvasive Electrocardiol* 2020 (PMC7507065) |

**Files counted.** Every count below is computed from these files. Each file was checked against the dataset's `SHA256SUMS.txt`.

- PTB-XL v1.0.3: `ptbxl_database.csv` (sha256 `7600de9c…216b`) and `scp_statements.csv` (`ad05b0b1…ac8f`).
- PTB-XL+ v1.0.1: `labels/12sl_statements.csv` (`1199e5cf…0199`), `labels/mapping/12slv23ToSNOMED.csv`, `labels/mapping/apply_snomed_mapping.py` and `features/feature_description.csv`.
- The large PTB-XL+ CSV came from PhysioNet's official S3 mirror (`physionet-open`), because physionet.org was very slow.

**Not reached.** Two primary sources sit behind bot checks that were not bypassed:
- The AHA/ACCF/HRS 2009 ECG standard Part VI (acute ischemia/infarction; Wagner GS et al., *Circulation* 119:e262).
- Bayés de Luna et al.'s 2006 ISHNE statement on wall terminology (*Circulation* 114:1755).

The territory section therefore leans on [ISE-2020], written by an overlapping author group, and on the data itself.

**Counting conventions.**
- "Records" are ECGs and "patients" are distinct `patient_id`s.
- A statement counts as present at any likelihood unless stated otherwise. All MI statements have a likelihood above 0.

## 1. The MI superclass: statements and counts

**How the superclass is built.**
- `scp_statements.csv` puts 14 statements in the diagnostic class `MI`, with four subclasses: AMI, IMI, LMI and PMI.
- The five INJ\* statements are filed under AMI or IMI. Their SCP category is "ischemic ST-T changes compatible with subendocardial injury", not "Myocardial Infarction".
- The superclass totals 5,469 records and 4,670 patients, which matches the PhysioNet page's 5,469 [PXL-page].
- 593 MI patients have more than one MI record.

**What the stage columns mean** (stage = `infarction_stadium1`/`2`, see §2):
- "I" is Stadium I or I–II.
- "II" is Stadium II or II–III.
- "III" is Stadium III only.
- "unk" is "unknown".
- "≥50" counts records with a likelihood of at least 50 (see §3).
- "vbh" is `validated_by_human` = True.

| SCP code | Description | Subclass | Records | Patients | lik 100 | lik ≥ 50 | vbh | I | II | III | unk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IMI | inferior MI | IMI | 2,676 | 2,355 | 1,022 | 1,714 | 1,600 | 54 | 629 | 443 | 1,550 |
| ASMI | anteroseptal MI | AMI | 2,357 | 2,033 | 1,522 | 2,007 | 1,614 | 102 | 398 | 514 | 1,343 |
| ILMI | inferolateral MI | IMI | 478 | 416 | 331 | 416 | 247 | 23 | 91 | 87 | 277 |
| AMI | anterior MI | AMI | 353 | 348 | 116 | 213 | 271 | 7 | 57 | 41 | 248 |
| ALMI | anterolateral MI | AMI | 288 | 243 | 200 | 246 | 160 | 23 | 43 | 41 | 181 |
| LMI | lateral MI | LMI | 201 | 185 | 57 | 122 | 153 | 5 | 17 | 30 | 149 |
| IPLMI | inferoposterolateral MI | IMI | 51 | 50 | 31 | 46 | 34 | 1 | 9 | 5 | 36 |
| IPMI | inferoposterior MI | IMI | 33 | 28 | 28 | 33 | 25 | 2 | 8 | 6 | 17 |
| PMI | posterior MI | PMI | 17 | 17 | 4 | 13 | 14 | 3 | 1 | 3 | 10 |
| INJAS | subendocardial injury, anteroseptal leads | AMI | 214 | 196 | 196 | 212 | 153 | 4 | 8 | 5 | 197 |
| INJAL | subendocardial injury, anterolateral leads | AMI | 145 | 136 | 133 | 143 | 102 | 1 | 11 | 6 | 127 |
| INJIN | subendocardial injury, inferior leads | IMI | 18 | 17 | 17 | 18 | 12 | 0 | 0 | 0 | 18 |
| INJLA | subendocardial injury, lateral leads | AMI | 17 | 17 | 14 | 16 | 13 | 0 | 1 | 2 | 14 |
| INJIL | subendocardial injury, inferolateral leads | IMI | 15 | 14 | 15 | 15 | 14 | 1 | 0 | 0 | 14 |

**Statements co-occur.** 1,156 MI records carry two or more infarct-territory statements. The commonest combinations are:

| Combination | Records |
|---|---|
| IMI alone | 1,971 |
| ASMI alone | 1,342 |
| ASMI + IMI | 578 |
| ILMI alone | 286 |
| AMI alone | 240 |
| ASMI + ILMI | 182 |
| INJ\* only (no infarct statement) | 181 |
| ALMI + ASMI | 159 |
| LMI alone | 108 |
| ALMI alone | 99 |
| AMI + IMI | 94 |

**INJ\* is not an infarct label.**
- 323 records (293 patients) carry any INJ\* statement.
- 142 of them also carry an infarct statement, and 181 carry none.
- 287 of the 323 are unstaged.
- These records sit in the MI superclass only because of how `scp_statements.csv` groups them.
- Related ischaemia statements live in the STTC superclass, for example ISCAL (659 records), ISC\_ (1,272), STD\_ (1,009) and STE\_ ("non-specific ST elevation", only 28 records).

**Overlaps that matter for ADR 0006.**
- 38 MI records also carry CLBBB, and 4 carry PACE.
- 2 MI records are from patients under 18.

## 2. `infarction_stadium1` / `infarction_stadium2`: how acute?

**Where the stage comes from.**
- The stage was pulled out of the free-text report by keyword [PXL-paper, "ECG Statements"; PXL-page].
- The paper defines each stage only by the keywords mapped to it, with "see [Bousseljot et al.] for further details" [PXL-T11].
- It adds the intermediate stages I–II and II–III to "the conventionally used infarction stages I, II, and III" [PXL-paper].

| Value | Keywords mapped to it [PXL-T11] | Reading |
|---|---|---|
| Stadium I | "acut, early" | acute |
| Stadium I–II | "acut/subacut, ablaufend" | acute to subacute ("ablaufend" means evolving) |
| Stadium II | "recent, subacut, bereits abgelaufen" | recent or subacute |
| Stadium II–III | "subacut/chronisch" | subacute to chronic |
| Stadium III | "old, abgelaufen, chronisch" | old |
| unknown | "uncertain, unknown, unbekannt" | age not stated |

**Counts in v1.0.3.**

| Column | Empty | unknown | I | I–II | II | II–III | III |
|---|---|---|---|---|---|---|---|
| `infarction_stadium1`, all records | 16,187 | 3,430 | 166 | 5 | 88 | 943 | 980 |
| `infarction_stadium1`, MI records | 0 | 3,372 | 146 | 4 | 88 | 910 | 949 |

- `infarction_stadium2` is set on only 103 records: I 19, II 19, III 65.
  - It holds a second stage for a second infarct, for example I + III on 8 records.
  - Its Stadium I never occurs without Stadium I in `infarction_stadium1`.
- Every MI record has `infarction_stadium1` set.
- 143 non-MI records also carry a stage. Their commonest codes are ABQRS, NORM, LVH, ISC\_ and WPW. 21 of them are Stadium I/I–II.

**Acute-staged MI: 150 records, 128 patients** (Stadium I or I–II in either column).

| Aspect | Breakdown |
|---|---|
| By statement | ASMI 102, IMI 54, ILMI 23, ALMI 23, AMI 7, LMI 5, INJAS 4, PMI 3, IPMI 2, IPLMI 1, INJIL 1, INJAL 1 (one record can carry several) |
| MI likelihood | 148 have an MI statement at likelihood ≥ 50, 137 at 100 |
| `validated_by_human` | 98 |
| Folds 1–8 | 124 records, 10–23 per fold |
| Fold 9 | 12 |
| Fold 10 | 14 |
| Patient course | Of the 140 patients with any Stadium I/I–II record, 48 have a later ECG, and 18 of those are later staged II or III |

**What the report text shows.** The stage reflects how the infarct was worded, and the extraction is noisy:

| Report wording | Records | Stage assigned |
|---|---|---|
| "akut" | 133 | 120 Stadium I. Many say "mögl. akut", which means possibly acute. |
| "subakut" | 22 | 16 Stadium I. Table 11 maps "subacut" to II, so this looks like a substring match on "akut". |
| "recent" | 63 | 26 Stadium II, 12 Stadium I |
| "alt" (old) | 1,065 | 941 Stadium II–III. These are mostly "wahrscheinlich alt" ("probably old"), so in practice **II–III mostly means "probably old"**. |
| "alter unbest." (age undetermined) | 988 | 923 "unknown" |
| ST elevation in words ("ST-Hebung", "ST elevation", "ST segments are elevated") | 318 | Only 26 of the 171 Stadium I/I–II reports say this |

**PTB-XL+ relabels the stages** [`apply_snomed_mapping.py`, PXP v1.0.1]:
- `map_infarction_stadium()` and `map_mi_labels()` add `_AC` (acute) for Stadium I/I–II.
- They add **`_OLD` for Stadium II**, which is the "recent/subacute" stage.
- They add nothing for Stadium II–III and III.
- So in PTB-XL+'s `ptbxl_statements.csv`, "Acute myocardial infarction" covers 150 records and "Old myocardial infarction" only 84 [PXP-T4]. Those 84 are Stadium II, not the 949 Stadium III records.
- Do not reuse PTB-XL+'s SNOMED view of PTB-XL stages without correcting this.

**What this means for acuteness.**
- Read generously, the pool of "acute MI" is about 150 records. Many are worded "possibly acute".
- It averages about 15 records per fold. That is enough to look at, but too few for a test fold to give a tight confidence interval.
- None of these labels says whether an artery was occluded (ADR 0001).

## 3. Likelihoods, `validated_by_human` and `strat_fold`

**Likelihood.**
- `scp_codes` is a dictionary from statement to likelihood, with "likelihood … set to 0 if unknown" [PXL-page].
- Diagnostic statements get a likelihood from keywords in the report. Form and rhythm statements get 0 [PXL-paper, "ECG Statements"].
- The keyword map is [PXL-T4]:

| Report keywords | Likelihood |
|---|---|
| "nicht auszuschliessen, cannot rule out, cannot be excluded" | 15 |
| "möglicherweise, consider, suggest, likely" | 35 |
| "wahrscheinlich, possible, maybe, probably, ablaufend, Verdacht auf" | 50 |
| "Sonst, Bild" | 80 |
| "Consistent with, Diagnose, Zustand nach…" | 100 |

- A second cardiologist could edit likelihoods directly [PXL-paper, Methods].
- Over all MI statement occurrences: 100 × 3,686, 15 × 1,492, 50 × 1,295, 80 × 233, 35 × 156, and one stray 14.
- **By each record's highest MI likelihood:**
  - 2,975 records are at 100.
  - 1,207 are at 15 ("cannot be excluded").
  - 127 are at 35.
  - So 1,335 MI records (24%) are MI only in the sense of "cannot rule out" or "consider".
  - MI at ≥ 50 covers 4,134 records (3,541 patients).

**Annotation provenance** [PXL-paper, "ECG Statements" and "Quality Assessment for Annotation Data"].
- `initial_autogenerated_report` is true when the report ended with "unbestätigter Bericht", meaning the device wrote it. This applies to 6,813 records.
- `second_opinion` is true when a second cardiologist's report is appended after "Edit:". This applies to 555 records, 139 of them MI.
- `validated_by_human` is a conservative estimate. It is false only for auto-generated reports that have neither a `validated_by` nor a second opinion.
  - Overall: 16,056 True and 5,743 False.
  - MI records: 3,477 True and 1,992 False.
  - Acute-staged MI: 98 True and 52 False.

**`strat_fold`** [PXL-paper, "Cross-validation Folds"; PXL-page item 5].
- There are 10 folds, assigned **per patient**: in v1.0.3, no patient spans two folds.
- The split is multilabel-stratified on all statements plus sex and five age bins.
- Patients with any record not validated by a human are kept out of folds 9 and 10. In v1.0.3, all 2,183 fold-9 and 2,198 fold-10 records are `validated_by_human`.
- Recommended use: folds 1–8 to train, fold 9 to validate, fold 10 to test.
- MI is spread evenly, at 528–563 records per fold.
- The stratification did not target the acute stage, so acute-staged MI varies from 10 to 23 per fold.

## 4. What PTB-XL+ adds

PTB-XL+ v1.0.1 is the latest version [PXP-page, PXP-paper]. It adds the following for all 21,799 PTB-XL records:

- **Features** from three sources, in `features/{12sl,unig,ecgdeli}_features.csv` with a harmonised `feature_description.csv`:
  - GE Marquette 12SL v.243, re-analysed in MUSE.
  - Glasgow Uni-G R30.4.2.
  - Open-source ECGDeli.
- **Median beats** from 12SL and Uni-G, in WFDB format at 500 Hz, 600 samples each.
- **Fiducial points** from ECGDeli, as WFDB annotations, per lead and global. The per-beat labels include an "L point (for STEMI)" next to QRS offset and T onset.
- **Automatic diagnostic statements from 12SL only.**
  - Uni-G statements are withheld "due to usage restrictions" [PXP-paper].
  - The file is `labels/12sl_statements.csv`, with columns `statements`, `statements_cat` (qualifiers bound with ";"), `statements_ext` (statement plus certainty) and `statements_ext_snomed`.
  - Mappings to SNOMED (actually OMOP concept ids) are provided for both 12SL and PTB-XL labels.

### 12SL statements bearing on acute MI and STEMI

The statement text comes from `12slv23ToSNOMED.csv`, and the counts are records out of 21,799.

| 12SL code (no.) | Text | Records |
|---|---|---|
| STEMI (821) | "\*\* \*\* ACUTE MI / STEMI \*\* \*\*" | **178** (155 patients) |
| `<site>MI;AC` (qualifier 830 ", possibly acute") | acute-qualified infarct: IMI 49, ASMI 39, ALMI 17, IPMI 13, AMI 11, POSTMI 4, LMI 2 | 128 |
| CRVI (806) | "Consider right ventricular involvement in acute inferior infarct" | 74 |
| IIOHAI/AIOHAI/LIOHAI/ALIHAI/ILIHAI (963–967) | "ST elevation, consider \<site\> injury or acute infarct" | 42 (20/16/4/1/1) |
| AINJ/LINJ/IINJ/ALINJ/ILINJ (930–962) | "\<site\> injury pattern" | 21 (1/12/6/1/1) |
| SERYR1 (902) / SERYR2 (903) | "ST elevation, consider early repolarization, pericarditis, or injury" / "…probably due to early repolarization" | 10 / 21 |
| PCARD (901) | "Acute pericarditis" | 2 |
| STDEP2 + 7 "marked ST abnormality, possible \<site\> subendocardial injury" codes (1024–1081) | ST depression | 267 |
| `<site>MI;AU` (qualifier 831 ", age undetermined") | infarct of undetermined age, mapped to *old* MI | 3,999 |

**STEMI is the umbrella statement.**
- Every `;AC`, 963–967 and injury-pattern record also carries STEMI, so their union is exactly the 178 STEMI records.
- How the STEMI records compare with PTB-XL:

| PTB-XL view of the 178 STEMI records | Breakdown |
|---|---|
| MI superclass | 157 carry it. 4 are labelled NORM. |
| PTB-XL MI statements | ASMI 89, IMI 56, ALMI 36, ILMI 20, IPMI 8, INJAS 7, IPLMI 6, AMI 5 |
| PTB-XL stage | Stadium I 48, I–II 1, II 24, II–III 6, III 9, unknown 71, no stage 19 |
| `validated_by_human` | 142 |
| Folds | fold 9: 23, fold 10: 15, folds 1–8: 10–25 each |

- In the other direction, **only 49 of the 171 Stadium I/I–II records get a 12SL STEMI.**
- PTB-XL+ itself reports agreement between the two sources as MCC [PXP-T3/T4]:

| Concept | MCC | PTB-XL count | 12SL count |
|---|---|---|---|
| Myocardial infarction | 0.63 | 5,469 | 4,174 |
| Inferior MI | 0.61 | 3,238 | 2,304 |
| Anteroseptal MI | 0.45 | 2,357 | 566 |
| Anterolateral MI | 0.32 | 288 | 146 |
| Acute myocardial infarction | 0.29 | 150 | 178 |
| Acute MI of inferior wall | 0.20 | 55 | 89 |
| Lateral MI | 0.19 | 679 | 190 |
| Old MI (distorted by the Stadium II mapping above) | 0.08 | 84 | 3,999 |
| Anterior MI | −0.02 | 353 | 618 |

- The paper notes "essentially no agreement" for "myocardial infarctions with specific localization" [PXP-paper, "Descriptive analysis"].
- 12SL's STEMI is an algorithm applying millimetre STEMI criteria. Under ADR 0001 it can serve as a **STEMI-criteria comparator**, never as an OMI label. Its decision rules are in GE's Physician's Guide, which is not public and was not consulted.

### ST measurements, for computing STEMI criteria ourselves

Taken from `feature_description.csv`, where X is any of the 12 leads:

| Source | Columns | Meaning |
|---|---|---|
| Uni-G | `ST_Amp_X` | J-point amplitude, mV |
| Uni-G | **`ST_Amp80ms_X`** | J+80 ms amplitude, mV |
| Uni-G | `ST_Amp28_X`, `ST_Amp38_X` | 2/8 and 3/8 of the ST-T segment |
| Uni-G | `ST_AmpAdj_X`, `ST_Slope_X`, `ST_Dur_X` | adjusted amplitude, slope, duration |
| 12SL | `ST_Amp_X` (STJ) | J-point amplitude |
| 12SL | `ST_Amp116_X` (STM), `ST_Amp18_X` (STE) | ST level at QRS offset + RR/16 and + RR/8 |
| 12SL | `ST_AmpMax_X`, `ST_AmpMin_X` | maximum and minimum of STJ, STM and STE |
| ECGDeli | `ST_Elev_X` | ST deviation from Gaussian fits, with IQR and beat count |

- No source has a J+60 ms column.
- **Units need checking.** In the first rows, 12SL STM and STE look like µV while STJ is in mV, so Max/Min may mix units.
- The median-beat headers (12SL in WFDB format 32 with non-integer gains, Uni-G in format 212) don't match the project page's "16 bit … 1 μV/LSB". Read them with each file's own header gains.

## 5. Infarct territory → culprit vessel as a proxy label

**Why territory is weak as a vessel label.**
- PTB-XL's territory is the *reading cardiologist's ECG localisation*.
- For most records it describes an old Q-wave scar, not an acute occlusion.
- The 12SL algorithm and the cardiologists localise inconsistently, as the MCC table above shows.
- The culprit-vessel rule of [#4](https://github.com/the-dr-lazy/delmir/issues/4) says the lesion decides, never the territory. So any territory-derived vessel is a proxy label by definition (GLOSSARY).

**What the anatomy allows** [ISE-2020, §5]:
- The RCA can give the posterior descending artery and/or a posterolateral branch supplying the inferolateral segments.
- The LCx supplies the lateral free wall through the obtuse marginals and may give a left PDA.
- So "the majority of inferior infarcts [are] due to RCA or LCX occlusion".
- The same authors argue that ST depression in V1–V3 is not inferobasal ("posterior") ischaemia, which undercuts the classic "posterior MI" label.

Groups are by the set of infarct statements on a record (any likelihood; INJ\* left out because it does not localise an infarct):

| Group | Statements | Plausible proxy vessel | Records | Patients | Stage I/I–II records | Fold 10 records |
|---|---|---|---|---|---|---|
| A | ASMI and/or AMI only | **LAD**: the one unambiguous mapping | 1,582 | 1,420 | 43 | 163 |
| B | ALMI, alone or with ASMI/AMI | probably LAD (diagonal); LCx possible | 258 | 216 | 21 | 26 |
| C | IMI and/or IPMI only | RCA or LCx (dominance-dependent): **ambiguous** | 1,998 | 1,777 | 26 | 204 |
| D | ILMI/IPLMI, with or without IMI/IPMI | RCA or LCx: **ambiguous** | 334 | 302 | 8 | 31 |
| E | LMI only | LCx or LAD diagonal: **ambiguous** | 108 | 101 | 1 | 12 |
| F | PMI only | LCx or RCA: **ambiguous**, and the term itself is disputed | 11 | 11 | 2 | 1 |
| G | statements from two or more groups (e.g. ASMI + IMI: 578) | wraparound LAD, multivessel, or two infarcts of different age: **ambiguous** | 997 | 866 | 48 | 95 |
| — | INJ\* only | no territory | 181 | 168 | 1 | 18 |

- With only statements at likelihood ≥ 50 counted, A has 1,367 records (48 acute-staged) and B has 222 (22).
- **Only group A, and arguably B, yields a single proxy vessel.** Everything inferior or lateral needs angiography to tell RCA from LCx. So PTB-XL alone cannot train a three-way LAD/LCx/RCA head.
- Restricting to acute-staged records leaves 43–48 LAD-proxy records. That is far too few for phase 2 on acute MI alone.

## Open points for #21

These are left for the grilling, not decided here:
- Whether phase 1 uses all-age MI, MI at likelihood ≥ 50, or the ~150 acute-staged records.
- Whether INJ\* records count as MI.
- Whether the 12SL STEMI flag serves as a STEMI-criteria comparator, or criteria are computed from the Uni-G J/J+80 features.
- Whether phase 2 trains only LAD vs. not-LAD from PTB-XL.
- How to correct PTB-XL+'s Stadium II → "old MI" mapping if `ptbxl_statements.csv` is used.

## Method

- The counts come from short Python scripts over the files above, using the `csv` and `ast` modules.
- `scp_codes` and the 12SL list columns are parsed with `ast.literal_eval`.
- The MI codes are those whose `diagnostic_class` is `MI` in `scp_statements.csv`.
- "Acute-staged" means Stadium I or I–II in `infarction_stadium1` or `infarction_stadium2`.
- Report-text matches are case-insensitive regular expressions over `report`.
