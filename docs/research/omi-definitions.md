# How OMI studies define OMI and apply STEMI criteria

Research for [the-dr-lazy/delmir#12](https://github.com/the-dr-lazy/delmir/issues/12), carried out 2026-10-21. It feeds [What is DELMIR's operational definition of OMI?](https://github.com/the-dr-lazy/delmir/issues/20), and through it [How is DELMIR evaluated?](https://github.com/the-dr-lazy/delmir/issues/24) and [What does a case in the case registry hold?](https://github.com/the-dr-lazy/delmir/issues/28).

Sources are the papers' full texts (PMC / Europe PMC JATS XML and supplements), the guideline PDFs, vendor validation documents and the PhysioNet data files. Every claim links to its source. Sources read only as an abstract are marked **[abstract only]**, and numbers that the source itself contradicts or that could not be reconciled are marked **[UNCERTAIN]**. The sections headed "synthesis" or "recommendation" are this note's own reasoning, not a source claim. The definitions of Meyers 2021, Al-Zaiti 2023 and Herman 2024 were re-checked word for word against the Europe PMC full text after drafting.

Terms follow [GLOSSARY.md](../../GLOSSARY.md): OMI, NOMI, Not-OMI, STEMI criteria, STEMI-negative OMI.

## Answer

**1. Only one rule is universal: an acute culprit with TIMI 0–1 flow is an OMI.** Every study counts it. Beyond that the studies split along four axes: TIMI 2, TIMI 3 (reperfused), patients without angiography, and how STEMI criteria are read.

**2. The Smith/Meyers lineage, which DELMIR's paradigm (ADR 0001) comes from, uses one rule:**

- an acute culprit with **TIMI 0–2**, or
- an acute culprit with **TIMI 3 (or unknown flow)** and a **very high peak troponin**, or failing that a new or presumed-new **regional wall-motion abnormality**, or
- **no angiography**: a very high peak troponin **plus** a new regional wall-motion abnormality, or a STEMI(+) ECG with **death before angiography**.

| Assay | "Very high" peak troponin | First stated in |
|---|---|---|
| Contemporary / 4th-gen cTnT | ≥ 1.0 ng/mL | Meyers 2021 |
| Contemporary / 4th-gen cTnI | ≥ 10.0 ng/mL | Meyers 2021 |
| hs-cTnT | ≥ 1000 ng/L | later lineage papers (Karim 2025, Cooper 2026, Carvalho 2026, Lindow 2026) |
| hs-cTnI | > 5000 ng/L | later lineage papers (Karim 2025, Cooper 2026, Carvalho 2026) |

The hs thresholds are a convention of the lineage, not independently validated cut-offs, and the papers mix ≥ and >. A review by the same group restates "very high" as roughly **70–300 × the assay's 99th-percentile URL** (McLaren 2022).

**3. The other studies differ in ways that matter for a label:**

| Question | Answers in the literature |
|---|---|
| TIMI 2 | OMI (Meyers lineage); OMI only with > 70 % stenosis and troponin "5–10 ng/mL" (Al-Zaiti 2023); OMI only with urgent PCI (Herman 2024 primary) |
| TIMI 3 / reperfused | OMI via very high troponin or WMA (Meyers lineage); OMI via urgent PCI (Herman 2024 primary); never OMI (Al-Zaiti 2023, Gustafsson 2026); its own ECG class (DIFOCCULT type 1d) |
| No angiography | troponin + WMA, or STEMI + death (Meyers 2021, Nyström 2026); troponin alone (DIFOCCULT: cTnI > 5.0 ng/mL; Lindow 2026: hs-cTnT ≥ 1000 ng/L); excluded (Herman 2024 Aalst, Gustafsson 2026); in effect negative (Al-Zaiti 2023) |
| Negatives | NOMI pooled with no MI. Mostly **not** angiography-verified: troponin-negative rule-outs make up most negatives in Herman, Lindow and Gustafsson. Al-Zaiti labels type 2 MI and subacute occlusion negative. |
| Time windows | Mostly none in the definition. Herman discards ECGs > 24 h before angiography or after it; Gustafsson needs angiography ≤ 7 days after an MI; Lindow and Al-Zaiti look 30 days ahead. |

Herman 2024's primary label ("TIMI 2–3 with emergent or urgent PCI") depends on a treatment decision, and treatment depends partly on the ECG. That is a label-leakage risk for an ECG model. The same paper reports troponin-based variants (hs-cTnT ≥ 500 or ≥ 1000 ng/L), and its supplement and Sharkey 2026 say the Queen of Hearts *training* label was the Meyers rule. So the PMcardio model's training label and its evaluation label may differ.

**4. Headline performance (OMI reference standard, STEMI criteria as comparator):**

| Study | Method | Sens | Spec | Share of OMI that was STEMI-negative |
|---|---|---|---|---|
| Meyers 2021 (n = 808) | OMI ECG findings (expert) vs STEMI criteria | 86 % vs 41 % | 91 % vs 94 % | 59 % |
| DIFOCCULT 2020 (n = 3000) | OMI ("ACOMI") reading vs STEMI, weighted AUC | 0.823 vs 0.736 (AUC) | | 28 % of non-STEMI MIs reclassified as occlusion-predicting |
| Al-Zaiti 2023 (prehospital STEMI excluded) | Random forest vs clinicians vs Philips software, external AUROC | 0.87 vs 0.80 vs 0.75 | | (cohort is STEMI-negative by design) |
| Herman 2024 (3254 ECGs) | Queen of Hearts vs STEMI criteria vs experts | 80.6 % vs 32.5 % vs 73.0 % | 93.7 % vs 97.7 % vs 95.7 % | 67.5 % |
| Lindow 2026 (24,511 consecutive ED patients) | Queen of Hearts vs automated STEMI criteria | 52 % vs 23 % | 99 % vs 98 % | — |

STEMI-criteria sensitivity for OMI ranges from **23 % to 70 %** across studies. Much of that spread comes from the comparator's design (who reads, which ECG, which cohort) as well as case mix.

**5. How studies apply STEMI criteria as the comparator.** Three designs:

- **Human reading of the Fourth UDMI thresholds**, blinded except to age and sex, J-point measured from QRS onset. STEMI(+) if **any pre-angiography ECG** meets criteria (Meyers 2021) or on the per-patient maximum (Herman 2024). DIFOCCULT used the admission ECG only.
- **Automated criteria** computed from Glasgow (Uni-G) per-lead J-point measurements on the **first ECG**, with no human over-read (Lindow 2026, Nyström 2026). The Glasgow program's own statements were a separate, second comparator.
- **Cath-lab activation cohorts** (Cooper 2026, Sharkey 2026), which measure the activation decision, not the criteria.

**6. Applying STEMI criteria automatically to a 12-lead signal:**

- **The rule (4th UDMI, Table 2):** new ST elevation at the **J-point**, in **two contiguous leads**, ≥ 1 mm in every lead except V2–V3. In V2–V3 the cut-points are ≥ 2 mm in men ≥ 40, ≥ 2.5 mm in men < 40, and ≥ 1.5 mm in women. It applies only in the absence of LVH and **bundle branch block** (the EHJ text says BBB; ESC 2023 says LBBB). UDMI recommends **QRS onset** as the amplitude reference. Cabrera ordering (aVL, I, −aVR, II, aVF, III) comes from AHA 2009 Part VI, not UDMI. Neither UDMI nor ESC 2023 says whether −aVR counts as a contiguous lead.
- **No open, validated implementation exists.** NeuroKit2 (MIT) and ECGdeli (GPL-3.0) delineate waves only. One GitHub hobby implementation applies 2 mm to V1 and V4–V6, which is wrong, and defaults sex to male.
- **PTB-XL+ (CC BY 4.0) has what the comparator needs:** per-lead J-point ST amplitudes from GE 12SL v243 (`STJ_X`) and Uni-G (`ILM_ST_Amp_X`), plus 12SL statements. Statement 821 "ACUTE MI / STEMI" is on 178 of 21,799 records. Uni-G is the University of Glasgow program.
- **MIMIC-IV-ECG has no per-lead ST amplitudes**, only machine report text from mixed, unlabelled vendors (Burdick/Spacelabs, Philips, GE). Some reports say they were made "without knowing patient's sex or age".
- **Machine statements are not the guideline criteria.** 12SL is specificity-tuned, uses reciprocal depression as its main discriminator and has age- and sex-specific logic. Computer STEMI statements reach 32 % to 93 % sensitivity, depending on the algorithm and the reference standard. Exact 12SL, Philips, Mortara and Glasgow thresholds could not be verified: the physician's guides were not obtainable.
- **Computer and human ST measurements are not interchangeable.** They differ systematically (Eskola 2005, Pelter 1997), and in Hillinger 2019 30 % of missed STEMIs came from wrong measurement points. Physicians agree poorly on STEMI (κ 0.33 in McCabe 2013).

### What this means for #20 (synthesis)

- **Adopt the Meyers-lineage rule as the base.** It is the definition ADR 0001's paradigm comes from, it is the training label of the best-validated model (Queen of Hearts), and its parts map one-to-one onto the follow-up #4 already records: culprit finding, per-lesion pre-PCI TIMI, peak troponin.
- **Record the troponin assay, not just a value.** The threshold depends on the assay class (contemporary vs high-sensitivity) and the analyte (I vs T). Without the assay, a value can only be judged against the highest threshold for its unit (ng/L → 5000, ng/mL → 10), or as a multiple of a known 99th-percentile URL. #28's follow-up needs the assay class, the analyte and, ideally, the URL, plus a regional wall-motion abnormality field as the fallback.
- **Make the label a sum with an Unknown case and an evidence tier, never a boolean** (angiography with TIMI / angiography without TIMI / no angiography). Missing facts become Unknown, not Not-OMI. Every published convention (Meyers, Herman-primary, Al-Zaiti, Gustafsson) is then a filter over tiers and flags, which lets DELMIR report against each.
- **Do not use urgent PCI as a criterion** for DELMIR's own label: it leaks the clinician's ECG reading into the label. Keep it as a recorded fact so a Herman-compatible label can be derived.
- **Flag "TIMI 3 with sub-threshold troponin".** Meyers shows it contains true reperfused OMIs that the rule misses. Flag "STEMI(+) with death before angiography" too, because there the ECG feeds its own label.
- **Use only ECGs before angiography**, and store the ECG-to-angiography interval. Herman's ≤ 24 h window is a reasonable default.
- **For #24's comparator:** the primary comparator is the 4th UDMI thresholds recomputed from J-point amplitudes (QRS-onset reference, age/sex V2–V3 cut-points, Cabrera adjacency). Report it on all ECGs (LVH/BBB/paced counted criteria-negative) and on the guideline-eligible subset. On PTB-XL+ use the vendor STJ values; elsewhere use DELMIR's own delineation, validated against them first. The 12SL statement is a secondary "commercial algorithm" comparator. A blinded two-reader read of a subset audits it. DELMIR's own ECGs are digitized images, so the comparator there runs on the digitized signal and inherits the digitizer's error near the 1 mm thresholds.

The detail follows: [Part 1](#part-1-how-omi-studies-turn-omi-into-a-label) covers each OMI study, [Part 2](#part-2-stemi-criteria-definitions-and-automatic-application-to-a-12-lead-ecg) covers STEMI criteria and their automation.


## Part 1: How OMI studies turn OMI into a label

Compiled 2026-10-21 from primary sources: full-text JATS XML pulled from Europe PMC (mirrors PMC), plus supplements where retrievable.
Quotes are kept under 15 words. Everything else is a faithful paraphrase. **[UNCERTAIN]** marks numbers or wording I could not reconcile, or where the source contradicts itself.

Access summary

| # | Paper | Full text read? | Supplement read? |
|---|---|---|---|
| 1a | Meyers 2021, IJC Heart & Vasc | Yes (PMC8065286) | Yes (mmc1.docx: Tables 2, 4–6, Appendix A) |
| 1b | Meyers 2021, J Emerg Med | **No.** Paywalled (Elsevier 403; Europe PMC "subscription required"). **Abstract only.** | No |
| 2 | Aslanger 2020, DIFOCCULT | Yes (PMC7399112) | Yes (Elsevier mmc2.docx: Table S1 ECG types, S2, S3). Table 3 read from the Elsevier table image |
| 3 | Al-Zaiti 2023, Nature Medicine | Yes (PMC10353937) | Figures yes. Supplementary PDF **not read** (no PDF text tool in my environment) |
| 4 | Herman 2024, EHJ-Digital Health | Yes (PMC10944682) | Yes (ztad074 supplementary .docx) |
| 5+ | Karim 2025, Cooper 2026, Hellerman 2026, Lindow 2026, Nyström 2026, Carvalho 2026, Sharkey 2026, Gustafsson 2026, McLaren 2022 review, Hung 2018 meta-analysis, AI-ECG TIMI design paper | Yes (PMC full texts) | Not read |
| — | Khan 2017 EHJ meta-analysis | **No.** Paywalled. **Abstract only** (PubMed 29020244) | No |
| — | Portuguese PMcardio external validation (EHJ-DH 2026 suppl. abstract) | Abstract only (that is all that exists) | — |

Correction to the brief: DIFOCCULT was published in **2020** (IJC Heart & Vasculature vol 30, 100603), not 2021. I found no published "DIFOCCULT-2". **DIFOCCULT-3** (NCT06570759) is a cluster-randomised paradigm trial, and I did not find a results paper for it ([registry](https://clinicaltrials.gov/study/NCT06570759)).

---

### 1a. Meyers HP, Bracey A, Lee D, et al. Accuracy of OMI ECG findings versus STEMI criteria for diagnosis of acute coronary occlusion myocardial infarction. *IJC Heart & Vasculature* 2021;33:100767.

- DOI: [10.1016/j.ijcha.2021.100767](https://doi.org/10.1016/j.ijcha.2021.100767). Full text: <https://pmc.ncbi.nlm.nih.gov/articles/PMC8065286/>
- Database: DOMI ARIGATO (NCT03863327). This database later became the **US external test set of Herman 2024**.

**Population, design, N, prevalence**
- Retrospective **case-control** study at 2 US academic EDs: Stony Brook (SBUH) and Hennepin County (HCMC).
- Patients came from four sources. Each site's cath-lab activation database (1 year) supplied cases and controls. SBUH added a prospective 6-month cohort of 467 suspected-ACS admissions. HCMC added extra controls with abnormal ECGs (STE, STD or TWI) from the UTROPIA database.
- 814 collected, 6 excluded for insufficient data to label, **N = 808**.
- 396 AMI (49%), **265 OMI (33%)**, 131 NOMI. Angiography was done in 79% (635).
- Source: §2.2 and §3.1, [PMC8065286](https://pmc.ncbi.nlm.nih.gov/articles/PMC8065286/).

**OMI definition** (§2.4, "Outcomes")

OMI is either:
1. **"Confirmed OMI"**: an acute culprit lesion with **TIMI 0–2** flow, or
2. **"Presumed OMI with significant cardiac outcome"**, any one of:
   - (a) acute but non-occlusive culprit **plus highly elevated cTn**: contemporary **cTnT ≥ 1.0 ng/mL** (Roche Elecsys, reference ≤ 0.01) or contemporary **cTnI ≥ 10.0 ng/mL** (assay given as "Abbott Architect 4th generation", reference ≤ 0.030);
   - (b) **no angiography**: highly elevated cTn **plus** a new or presumed-new **regional wall-motion abnormality (WMA)** on echo;
   - (c) a **STEMI(+) ECG with death before angiography**.

Other details:
- **TIMI 3 culprit** counts only through (a), the troponin threshold. Table 3's caption confirms that cTn-based OMI applies to "any culprit lesion".
- **Inequality sign [UNCERTAIN, minor]:** the main text and abstract use ≥. Supplement Table 2 writes ">1.0 / >10.0 ng/mL".
- **Why troponin is used:** the authors argue that TIMI flow alone is insufficient because flow at the ECG can differ from flow at angiography. They cite 16–19% TIMI-3 flow in proven STEMI.
- **Source of the thresholds:** chosen previously as the best cutoffs for separating STEMI from NSTEMI, and since "internally and externally validated" (refs 25, 34, 40, 42–47 in the paper).
- **Sensitivity analyses** (Table 3):
  - TIMI cutoff changed to 0–1.
  - cTn cutoffs lowered to 50/30/20/10% of the primary values. The caption shows an example cTnI/cTnT pair for "cTn-2" of 1.0 / 0.10 ng/mL **[UNCERTAIN: the caption's labelling of these lowered thresholds is internally confusing]**.

**Who labelled the outcome**
- Structured chart review by four EM physicians using a coding manual.
- When TIMI flow was not reported, an experienced cardiologist reviewed the cineangiogram.
- The outcome adjudicators were **not described as blinded to the ECG**. HPM was a data collector and adjudicator for SBUH and was therefore not used as a blinded ECG reader for SBUH.
- How the 265 OMIs were labelled (supplement Table 2):

| Path | n | % of OMI |
|---|---|---|
| (A) TIMI 0–2 culprit | 217 | 82% |
| (B) TIMI 3 culprit plus troponin | 44 | 17% |
| (C) no cath, WMA plus troponin | 2 | 0.8% |
| (D) STEMI/OMI ECG and death before cath | 2 | 0.8% |

**Time windows**
- No angiography time window is part of the definition.
- STEMI(+) means **any ECG before angiography** met criteria.
- The "time-to-diagnosis" analysis excluded 20 OMIs whose ECG diagnosis came more than 24 h before cath.

**Transient or reperfused OMI**
- No separate class. A reperfused culprit (TIMI 3) is OMI only if peak cTn crosses the high threshold.
- 20 of 51 "false positives" of the expert readers had acute culprits with TIMI 3 and sub-threshold troponin. The authors present two such cases as probable misses of the reference standard (§4.5).

**Patients without angiography**
- Labelled OMI only via rule (b) WMA plus troponin, or rule (c) death.
- Otherwise, "Diagnosis of any AMI in absence of angiography was based on final diagnosis in the patient's record", which means AMI without angiography is NOMI unless (b) or (c) applies.
- Patients with insufficient data to decide were **excluded** (n = 6).

**Negatives**
- NOMI: "AMI without angiographic, laboratory, or clinical evidence of OMI".
- MIRO: MI ruled out. May include mild troponin elevation adjudicated as non-AMI injury.
- Source: Table 1 definitions.

**STEMI comparator**
- Human-measured 4th Universal Definition (4UDMI) STEMI criteria, in mm at the J-point relative to the PQ junction.
- Readers: SWS (all 808) and HPM (250 HCMC cases), blinded except to age and sex.
- Serial ECGs were read sequentially. The patient counts as STEMI(+) if **any pre-angiography ECG** met criteria.
- This is ECG-criteria based, not cath-lab-activation based.
- A blinded cardiologist re-read 108 consecutive OMIs and called fewer STEMI(+) than the study reader (59 vs 67).

**Performance** (no CIs reported; McNemar p-values)

| Reader | Cohort | Method | Sens | Spec | Accuracy |
|---|---|---|---|---|---|
| Interpreter 1 | n = 808 | OMI findings | 86% | 91% | 89% |
| Interpreter 1 | n = 808 | STEMI criteria | 41% | 94% | 77% |
| Interpreter 2 | n = 250 | OMI findings | 80% | 92% | 89% |
| Interpreter 2 | n = 250 | STEMI criteria | 36% | 91% | 76% |

- Interpreter 1 differences: sensitivity p < 0.0001, specificity p = 0.008.
- Inter-rater κ: 0.849 for the OMI call, 0.893 for STEMI criteria.
- **STEMI-negative share of OMI:** 108 of 265 OMI met STEMI criteria, so **59% of OMIs were STEMI(−)**.
- Source: abstract, §4.1, §4.2, Table 3.

### 1b. Meyers HP, Bracey A, Lee D, et al. Comparison of the STEMI vs NSTEMI and OMI vs NOMI paradigms of acute MI. *J Emerg Med* 2021;60(3):273–284.

- DOI: [10.1016/j.jemermed.2020.10.026](https://doi.org/10.1016/j.jemermed.2020.10.026). PubMed: <https://pubmed.ncbi.nlm.nih.gov/33308915/>
- **Full text not accessible** (paywall). Everything below comes from the abstract.

**Population**
- Retrospective review of a **prospectively collected** ACS population: 467 patients. This appears to be the same SBUH 467-patient cohort embedded in 1a (my inference from matching N).
- 108 OMI (23%). Only 67 of 108 (60%) met STEMI criteria, so 40% of OMIs were STEMI(−).

**OMI definition (abstract)**
- An acute culprit **and** either TIMI 0–2 flow, or TIMI 3 flow plus **peak troponin T > 1.0 ng/mL**.
- The SBUH site used cTnT, which is why only a TnT threshold is given.
- No-angiography handling, the definition of negatives, and the STEMI-reading method: **not verifiable** from the abstract.
- Negatives are called "no occlusion" in the abstract.

**Results (abstract)**

| Group | Median peak TnT (ng/mL) | Median arrival-to-cath |
|---|---|---|
| STEMI(+) OMI | 3.78 | 41 min |
| STEMI(−) OMI | 1.87 | 437 min |
| No occlusion | 0.00 | — |

- Cath within 90 min: 76% for STEMI(+) OMI vs 28% for STEMI(−) OMI.

---

### 2. Aslanger EK, Yıldırımtürk Ö, Şimşek B, et al. DIagnostic accuracy oF electrocardiogram for acute coronary OCCLUsion resuLTing in myocardial infarction (DIFOCCULT Study). *IJC Heart & Vasculature* 2020;30:100603.

- DOI: [10.1016/j.ijcha.2020.100603](https://doi.org/10.1016/j.ijcha.2020.100603). Full text: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7399112/>
- Supplement: <https://ars.els-cdn.com/content/image/1-s2.0-S2352906720303018-mmc2.docx>
- Registry: NCT04022668. Terminology: "ACO" / "ACOMI" (acute coronary occlusion MI), not "OMI".

**Population and design**
- Single tertiary primary-PCI centre in Istanbul, May 2017 to Dec 2018.
- Three groups, all enrolled by admission ECG:

| Group | N | How selected |
|---|---|---|
| STEMI | 1000 | Consecutive MI patients (4UDMI) whose admission ECG met STEMI criteria |
| non-STEMI | 1000 | Consecutive MI patients whose admission ECG did not |
| Control | 1000 | Random-date sample of chest-pain patients ruled out by serial negative troponins and unchanged ECGs for at least 12 h from symptom onset |

- The authors call the study "retrospective" in their limitations.
- Admission totals for weighting: 1152 STEMI, 2353 non-STEMI, 15,510 ruled out.
- **Composite-ACO prevalence:** STEMI 85% (833/977), non-STEMI 25% in subgroup B and 61% in subgroup A, control 0%.
- Source: §2.1, Table 2, [PMC7399112](https://pmc.ncbi.nlm.nih.gov/articles/PMC7399112/).

**Troponin assay**
- One assay, given as "Troponin I Abbott c4100i" **[the name as printed; probably the Architect ci4100 contemporary cTnI, my inference]**, in ng/mL.

**ACO definition** (§2.3, a "composite ACO"). Any one of:
1. **Total occlusion or a culprit lesion** on angiography **plus** peak **cTnI ≥ 1.0 ng/mL** **plus** at least a **20% rise within 24 h**;
2. a highly elevated peak troponin, **cTnI > 5.0 ng/mL**, **regardless of angiography**;
3. **cardiac arrest before any troponin rise**, with supporting clinical evidence of possible ACO.

Notes on the definition:
- It is explicitly built to catch arteries that "spontaneously open by the time of the angiogram". Reperfused culprits therefore count via (1) or (2).
- The authors call the definition **"our own arbitrary definition"** because no universally agreed ACO definition exists (limitations).
- A troponin table header says "ng/dl" where the text says ng/mL **[UNCERTAIN: probably a typo in Table 2]**.

**Culprit and angiographic adjudication**
- Two interventional cardiologists **blinded to the ECG**, with a third to break ties.
- Culprit features considered: appearance, thrombus, or critical stenosis with less than TIMI 3 flow.
- For total occlusions, acute vs chronic was judged by absence of collaterals and ease of wire crossing.

**Time windows**
- Admission ECG only.
- Troponin rise within 24 h. A 24–48 h troponin level was also collected.
- No angiography time limit.

**Transient OMI**
- Captured by the composite.
- The ECG classification has a separate type **1d**: STE that meets criteria **plus** T-wave inversion indicating spontaneous reperfusion, or subacute MI. Type 1d counts as "STEMI" but **not** as "ACO-predicting".
- 72.8% of type-1d ECGs met the composite ACO endpoint (supplement Table S3).

**No angiography**
- Can still be ACO through (2) or (3). Otherwise not ACO. Patients were not excluded for lacking angiography.

**Negatives**
- Non-ACO: no composite endpoint.
- Controls: rule-out patients, all 0/1000 composite-negative.

**ECG classification and comparator**
- All ECGs randomly sorted and read by **two cardiologists** blinded to outcomes, with a third to resolve disagreement.
- ECG types (supplement Table S1):
  - 1a: meets STEMI criteria and is clearly due to acute occlusion.
  - **1b: does not meet STEMI criteria but has OMI signs.**
  - 1c: meets STEMI criteria with an uncertain cause (mimic).
  - 1d: meets STEMI criteria with reperfusion or subacute features.
  - 2: ischemic STD/TWI. 3: nonspecific. 4: normal.
- The ACOMI approach is positive for types 1a + 1b. The STEMI approach is positive for types 1a + 1c + 1d.
- STEMI criteria are the 4UDMI J-point thresholds, judged by humans on the **admission** ECG.

**Performance** (Table 3, read from the [Elsevier table image](https://ars.els-cdn.com/content/image/1-s2.0-S2352906720303018-fx1_lrg.jpg))

For acute coronary occlusion:

| Approach | Weighting | Sens | Spec | AUC (95% CI) |
|---|---|---|---|---|
| STEMI | Unweighted | 70.5% | 88.0% | 0.792 (0.775–0.810) |
| ACOMI | Unweighted | 73.6% | 90.1% | 0.819 (0.802–0.836) |
| STEMI | Weighted by admission rates | 54.4% | 99.0% | 0.736 (0.731–0.741) |
| ACOMI | Weighted by admission rates | 67.9% | 96.7% | 0.823 (0.819–0.828) |

- Unweighted AUC difference p = 0.026. Weighted difference p < 0.001.
- **28.2% (282/1000) of non-STEMIs** were reclassified as type 1b (ACO-predicting).
- **STEMI-negative OMI share:** not reported as a single figure. The paper says the new paradigm "still misses 17.9% ACOs in the non-STEMI group" (Discussion).

---

### 3. Al-Zaiti SS, Martin-Gill C, Zègre-Hemsey JK, et al. Machine learning for ECG diagnosis and risk stratification of occlusion myocardial infarction. *Nature Medicine* 2023;29(7):1804–1813.

- DOI: [10.1038/s41591-023-02396-3](https://doi.org/10.1038/s41591-023-02396-3). Full text: <https://pmc.ncbi.nlm.nih.gov/articles/PMC10353937/>
- Study name: ECG-SMART, NCT04237688.

**Population, design, N, prevalence**
- Prospective observational cohorts: consecutive EMS patients with non-traumatic chest pain or an anginal equivalent, transported by ambulance with at least one **prehospital 12-lead ECG**.

| Cohort | Source | N | OMI |
|---|---|---|---|
| Derivation | Pittsburgh EMS + 3 UPMC hospitals | 4,026 | 5.2% |
| External validation | Orange County EMS (176) + Mecklenburg County EMS / Atrium (3,111), combined | 3,287 | 6.4% (209) |

- **Exclusions:** duplicate ECGs, cardiac arrest, VT/VF, and **confirmed prehospital STEMI** (machine "ACUTE MI" warning, EMS STEMI documentation, or a consult for cath-lab activation). The model therefore targets **STEMI-negative** OMI by design.
- Source: Results, Fig. 1, Methods "Study design", [PMC10353937](https://pmc.ncbi.nlm.nih.gov/articles/PMC10353937/).

**OMI definition** (Methods, "Clinical outcomes")
- Angiographic evidence of an acute culprit lesion in LAD, LCX, RCA or their primary branches with **TIMI 0–1**.
- **TIMI 2** with severe narrowing (> 70%) **and** peak troponin of "5–10.0 ng/mL" is also OMI. The Results section specifies peak "fourth-generation (not high sensitivity)" troponin.
  - **[UNCERTAIN]** The phrase is a range (5–10 ng/mL), not a single cutoff, and no assay or TnI/TnT split is given. It probably means "≥ 5 to 10 ng/mL depending on assay", but the paper does not say so.
- **TIMI 3 culprits are never OMI.** There is no troponin route for them.

**Adjudication**
- Two independent reviewers at each site, blinded to all ECG analyses and model output.
- They reviewed all medical records **within 30 days** of the encounter. κ = 0.771, with a third reviewer for disagreements.

**Time windows**
- The ECG is the first prehospital ECG.
- Outcome follow-up is 30 days. There is no explicit angiography time window.

**Transient OMI**
- A reperfused culprit (TIMI 2 without the troponin criterion, or TIMI 3) is **not** OMI.

**No angiography**
- OMI requires angiographic evidence, so non-catheterized patients are **effectively OMI-negative**. The paper has no troponin-only or echo route. (The negative class is "all other" patients.)

**Negatives**
- The negative class is the absence of OMI: all non-ACS causes plus "non-coronary occlusive ACS subtypes" (NOMI and unstable angina).
- **Type 2 MI and pre-existing subacute coronary occlusion** were labelled negative for both ACS and OMI. So were chronic troponin leak and non-coronary troponin leak such as pericarditis.

**Comparators** (the paper has no formal "STEMI criteria" arm)
- **Commercial software:** Philips DXL "Acute MI" / "Acute Ischemia" statements.
- **Clinician overread:** independent physicians annotated each ECG per 4UDMI. They were also asked to use judgement for suspicious changes such as hyperacute T waves. κ = 0.568 (EM physicians) and 0.690 (cardiologists).
- **HEART/HEAR score.**

**Performance**

Hold-out internal test:

| Method | AUROC (95% CI) |
|---|---|
| Random-forest model | 0.91 (0.87–0.96) |
| Clinicians | 0.79 (0.73–0.76) **[UNCERTAIN: this CI as printed does not contain the point estimate; a typo in the paper]** |
| Commercial system | 0.78 (0.70–0.85) |

External validation:

| Method | AUROC (95% CI) | Sens | Spec | PPV | NPV |
|---|---|---|---|---|---|
| Model | 0.87 (0.85–0.90) | 0.86 (0.81–0.91) | 0.98 (0.97–0.99) | 0.54 | 0.99 |
| Clinicians | 0.80 (0.77–0.83) | 0.58 | 0.93 | — | — |
| Commercial system | 0.75 (0.71–0.79) | 0.79 | 0.80 | — | — |

- The model's sensitivity and specificity come from its combined rule-in/rule-out score.

---

### 4. Herman R, Meyers HP, Smith SW, et al. International evaluation of an artificial intelligence–powered electrocardiogram model detecting acute coronary occlusion myocardial infarction. *Eur Heart J – Digital Health* 2024;5(2):123–133.

- DOI: [10.1093/ehjdh/ztad074](https://doi.org/10.1093/ehjdh/ztad074) (online Nov 2023). Full text: <https://pmc.ncbi.nlm.nih.gov/articles/PMC10944682/>
- Model: PMcardio OMI AI, "Queen of Hearts" (QoH).

**Population, design, N, prevalence**
- Retrospective study.
- **Development:** Aalst, Belgium (2011–2021, 9,764 suspected-ACS patients) plus an international ECG-image database of 2,368 ACS patients. The supplement says the image database consists of publicly available cases collected by Smith and Meyers.
  - Development set: 18,616 ECGs from 10,543 patients, 22.9% OMI.
- **Test sets:** 3,254 ECGs from 2,222 patients (2,263 contacts), **21.6% OMI**:
  - EU internal test (Aalst): 1,630 contacts, 16.0% OMI.
  - US external test: the DOMI ARIGATO database (= Meyers 2021 cohort), 633 contacts, 36.2% OMI.
- Source: Methods, Table 1, Fig. 1, [PMC10944682](https://pmc.ncbi.nlm.nih.gov/articles/PMC10944682/).

**OMI definition: primary (main text)**
- Clinical symptoms **and** a troponin elevation consistent with 4UDMI, **and** an angiographic acute culprit stenosis with either
  - (i) **TIMI 0–1**, or
  - (ii) **TIMI 2–3 with emergent or urgent PCI**.
- The **primary rule has no troponin threshold**. TIMI 2–3 counts only via urgent PCI.
- Patients "without any dynamic changes" on serial biomarkers were ruled out for OMI **regardless of angiography**.
- **[UNCERTAIN, internal contradiction]** Supplement Table S2's footnote labels the primary outcome as "Culprit TIMI 0-2 OR TIMI 3 with Trop T ≥1000 ng/L". In main-text Table 3, that is one of the *secondary* definitions (with "and PCI performed"). Sharkey 2026 (below) states the QoH **training** label was TIMI 0–2, or TIMI 3 with 4th-gen TnT ≥ 1.0 or TnI ≥ 10 ng/mL. So the training label and the evaluation label may differ.

**Secondary definitions tested** (Table 3, Troponin T in ng/L):

| Definition | Sens | Spec | AUC |
|---|---|---|---|
| TIMI 0–1 only | 87.5% | 86.9% | 0.929 |
| TIMI 0–1, or TIMI 2–3 with TnT ≥ 500 | 83.6% | 92.4% | 0.942 |
| TIMI 0–1, or TIMI 2–3 with TnT ≥ 1000 | 84.5% | 91.6% | 0.942 |
| TIMI 0–2, or TIMI 3 with TnT ≥ 1000 and PCI | 82.4% | 92.6% | 0.939 |

- The Aalst cohort used hs-cTnT. The admission/peak TnT columns are in ng/L (Table 2).

**Angiographic adjudication**
- EU: independent clinical reviewers assessed culprit, stenosis, TIMI flow, collaterals and treatment, "blinded" (the text says blinded identification of culprit vessels).
- US: DOMI ARIGATO angiograms (see 1a).
- Limitation stated: visual TIMI grading, with no core lab.

**Time windows**
- ECGs recorded **more than 24 h before coronary angiography, or after it, were discarded**.
- With multiple pre-angiography ECGs, the benchmarking used the **maximum interpretation per patient**.

**Transient OMI**
- Included in the primary outcome via TIMI 2–3 with urgent PCI.
- The authors' rationale is that up to one-fourth of STEMIs are reperfused at angiography.

**No angiography** (Figure 1 flow chart)
- The Aalst cohort contributed (a) acute-MI patients **who underwent coronary angiography** and (b) **MI ruled out without angiography (negative serial troponin)**.
- AMI **without** angiography therefore does not appear and was effectively **excluded**.
- Only 62% of test contacts underwent angiography. The rest are troponin-negative rule-outs labelled not-OMI.

**Negatives**
- "Not OMI" means no acute MI, or NOMI: no angiographic culprit, or a culprit that "does not require immediate revascularization".

**STEMI comparator**
- Blinded physician annotation of 4UDMI STEMI criteria (≥ 1 mm in two contiguous leads, with V2–V3 sex/age cut-points).
- "ECG experts" (SWS and HPM) gave a separate OMI annotation.
- Per patient, the maximum interpretation across pre-angiography ECGs was used. This is ECG-criteria based.

**Performance** (overall test set; Table 4, bootstrap 95% CI)

| Method | Sens | Spec | Accuracy | AUC |
|---|---|---|---|---|
| AI, optimal threshold 0.1106 | 80.6% (76.8–84.0) | 93.7% (92.6–94.8) | 90.9% | 0.938 (0.924–0.951) |
| STEMI criteria | 32.5% (28.4–36.6) | 97.7% (97.0–98.3) | 83.6% | — |
| ECG experts | 73.0% (68.7–77.0) | 95.7% (94.7–96.6) | 90.8% | — |
| AI at STEMI-matched specificity (threshold 0.5995) | 65.8% (61.3–70.0) | 97.5% | — | — |

- AUC by test set: EU 0.946, US 0.903.
- **STEMI-negative share:** 330 of 489 OMIs (**67.5%**) were missed by STEMI criteria (main text and Table 4).
- **[UNCERTAIN]** Count inconsistencies within the paper:
  - The text says 240 EU OMI and 213 US OMI. Table 1 and the supplement say 260 and 229 (= 489).
  - The US AUC CI as printed, 0.903 (0.893–0.939), is asymmetric around the point estimate.

#### 4b. Related PMcardio / QoH studies (verified from full text unless stated)

**Karim SR, Helseth HC, Baker PO, et al. *J Pers Med* 2025;15(4):130.** DOI [10.3390/jpm15040130](https://doi.org/10.3390/jpm15040130). [PMC12028524](https://pmc.ncbi.nlm.nih.gov/articles/PMC12028524/)
- **Design:** case-only series (no negatives), 2014–2024: 42 OMIs whose ECGs a conventional algorithm read as "normal", mostly from Dr. Smith's blog. Not a diagnostic-accuracy cohort.
- **Value here:** gives the most explicit per-assay version of the Smith/Meyers definition.
- **OMI definition**, requiring all of:
  1. acute type 1 MI with troponin rise and/or fall;
  2. an angiographic culprit **with intervention**;
  3. either TIMI 0–2, or TIMI 3 / **unknown flow** with large infarct, shown by any one of:
     - peak **hs-cTnI > 5000 ng/L**;
     - peak **4th-gen cTnI > 10 ng/mL**;
     - peak **hs-cTnT > 1000 ng/L**;
     - peak **4th-gen cTnT > 1.0 ng/mL**;
     - a **new regional WMA** "if peak troponin levels were not available or were below" threshold.
- Five candidate cases with TIMI 3 and sub-threshold troponin were **excluded** from the series.

**Cooper BL, Genova EA, et al. *EHJ – Digital Health* 2026 (ztaf138).** DOI [10.1093/ehjdh/ztaf138](https://doi.org/10.1093/ehjdh/ztaf138). [PMC12853124](https://pmc.ncbi.nlm.nih.gov/articles/PMC12853124/)
- **Population:** retrospective, single centre (Houston), consecutive STEMI-alert cath-lab activations 2022–2023, N = 304 (454 activations, 150 excluded).
- **Exclusions:** included death before cath, activations for electrical instability, and ECG not available.
- **True positive:** acute culprit with **TIMI 0–2 and any positive troponin**, or **TIMI 3 with very high peak troponin**: hs-cTnT ≥ 1000 ng/L, hs-cTnI ≥ 5000 ng/L, cTnI > 10.0 ng/mL, or cTnT > 1.0 ng/mL.
- **Adjudication:** chronic vs acute judged by intravascular imaging, response to wiring and collaterals. An interventional cardiologist blinded to AI output (but not the ECG) adjudicated equivocal cases.
- **No angiography:** 4 cancelled activations ruled out by troponin were counted as false-positive activations.
- **Prevalence:** 61.2% true positives (186).
- **STEMI comparator:** "traditional STEMI millimetre criteria". The text I read did not say who applied them.
- **Results:** QoH (threshold ≥ 0.50) sensitivity 89.2% (84.0–92.9) vs 68.3% (61.3–74.5); specificity 72.9% (64.2–80.1) vs 51.7% (42.8–60.5).

**Hellerman MB, Wang C, Zhang DT, et al. *J Pers Med* 2026;16(4):174.** DOI [10.3390/jpm16040174](https://doi.org/10.3390/jpm16040174). [PMC13117242](https://pmc.ncbi.nlm.nih.gov/articles/PMC13117242/)
- **Population:** retrospective, Stony Brook, Jul 2022 to Jul 2023, patients flagged as "suspected OMI".
- **OMI definition:** copied from Herman 2024's main text: TIMI 0–1, or TIMI 2–3 with emergent or urgent PCI, plus troponin per 4UDMI. "Not OMI" is worded the same way.
- **Exclusions:** patients who died before sufficient data were excluded (22–23).
- **Results:** 142 OMIs, of which 74 (52%) were STEMI(−). At high confidence, sensitivity 90.0% and specificity 93.2% overall; 66.2% and 93.4% in STEMI(−).
- **[UNCERTAIN]** Internal inconsistencies:
  - N is 474 in the abstract vs 451 in Methods (363 + 88).
  - A "missed 34% (25/74)" sentence is repeated under the broadest threshold, where sensitivity is 90.5%.

**Lindow T, Nyström A, Forberg JL, et al. *JACEP Open* 2026 (100473).** DOI [10.1016/j.acepjo.2026.100473](https://doi.org/10.1016/j.acepjo.2026.100473). [PMC13482599](https://pmc.ncbi.nlm.nih.gov/articles/PMC13482599/)
- **Population:** **consecutive** ED chest-pain patients at 5 Swedish EDs (ESC-TROP, 2017–2018), N = 24,511.
  - **OMI 467 (1.9%)**, which is 31% of the 1,589 AMIs.
  - Prehospital-identified STEMIs bypass the ED and are absent.
- **OMI labelling.** Among AMI patients **with** angiography, any one of:
  1. a registry-coded acute complete occlusion (SCAAR; N = 252);
  2. significant stenosis **revascularized** plus **hs-TnT ≥ 1000 ng/L** (N = 170). **No TIMI requirement on this path;**
  3. manual review of reports or films for an acute culprit with **TIMI 0–1** (N = 170). Reviewers were an EM physician plus a cardiologist, blinded to ECG results.
- **No angiography:** AMI without angiography follows "the criteria established by Meyers et al" (TnT ≥ 1000 ng/L, highly suspected ACS). This added 25 OMIs.
- **Time window:** AMI or revascularization **within 30 days**. First ECG only.
- **Negatives:** NOMI or no AMI.
- **STEMI comparator:** **fully automated** 4UDMI criteria from Glasgow program measurements, with no human over-read. Extended-lead and Sgarbossa/LVH variants were also tested.

| Method | Sens | Spec | PPV |
|---|---|---|---|
| QoH | 52% (47–57) | 99% | 51% |
| STEMI criteria | 23% (19–27) | 98% | 17% |
| Glasgow statements | 32% | 98% | — |
| Extended criteria | 41% | 95% | — |

**Nyström A, Björkelund A, et al. *JACEP Open* 2026;7(1):100299.** DOI [10.1016/j.acepjo.2025.100299](https://doi.org/10.1016/j.acepjo.2025.100299). [PMC12818230](https://pmc.ncbi.nlm.nih.gov/articles/PMC12818230/)
- This is not a PMcardio study. It uses the same ESC-TROP cohort and the same 467 OMIs as Lindow, with an in-house deep-learning model.
- **Labelling text:**
  - AMI plus SCAAR-coded acute occlusion.
  - Or hs-cTnT > 1000 ng/L **plus urgent PCI or CABG**.
  - Or a reviewed acute culprit with TIMI 0–1.
  - **No angiography:** hs-cTnT > 1000 ng/L **plus new or presumed-new regional WMA, or a STEMI ECG with arrest before angiography**.
  - Patients with an unclear outcome due to missing data were **excluded**.
- **[UNCERTAIN]** Lindow's description of the no-angiography rule (troponin alone, ≥ 1000) and Nyström's (> 1000 plus WMA or STEMI-arrest) differ for the same 467 cases. One of the two descriptions is simplified.
- **STEMI comparator:** automated (Uni-G/Glasgow measurements), evaluated after excluding LBBB, LVH and paced rhythms.
- **Results:** AI AUC 95.3% (93.8–97.3). Sensitivity 62% vs 27% for STEMI criteria at a matched specificity of 97.4%.

**Carvalho PEP, Belzer W, Pollmann DL, et al. *JACC: Advances* 2026 (102663).** DOI [10.1016/j.jacadv.2026.102663](https://doi.org/10.1016/j.jacadv.2026.102663). [PMC13053991](https://pmc.ncbi.nlm.nih.gov/articles/PMC13053991/)
- **Population:** Minneapolis Heart Institute, high-risk NSTE-ACS "level 2" emergent angiography activations 2022–2024, N = 224, **OMI 58%**. STEMI excluded.
- **OMI definition:** culprit with TIMI 0–2, **or TIMI 3/unknown** with peak troponin hs-cTnT ≥ 1000 ng/L, hs-cTnI > 5000 ng/L, cTnI > 10.0 ng/mL or cTnT > 1.0 ng/mL **before revascularization**, **or an assumed-new regional WMA** if troponin was unavailable or below threshold.
  - Of 13 TIMI-3 OMIs, 11 qualified by troponin and 2 by WMA.
- **Results:** QoH (any of the aOMI or mACS outputs > 0.5) sensitivity 58% (49–66), specificity 78% (68–86).
- **Comparator:** the standard-of-care activation itself. QoH would have reduced false positives from 42% to 22%.

**Sharkey SW, Herman R, Witt DR, et al. *JACC: Advances* 2026;5(4):102671.** DOI [10.1016/j.jacadv.2026.102671](https://doi.org/10.1016/j.jacadv.2026.102671). [PMC13019798](https://pmc.ncbi.nlm.nih.gov/articles/PMC13019798/)
- **Population:** Midwest STEMI Consortium cath-lab activations 2018–2022, N = 2,523.
- **Labels are not OMI labels.** There are three cohorts:
  - "AMI with culprit" (troponin > 99th percentile plus angiographic culprit, **any TIMI**), used as positives;
  - "AMI without culprit";
  - "no AMI", used as negatives.
- **Training label, as stated here:** the paper gives the QoH training-set definition as culprit TIMI 0/1/2, or TIMI 3 with peak 4th-gen TnT ≥ 1.0 ng/mL or TnI ≥ 10 ng/mL.
- **Results:** sensitivity 93.8% overall and 86.9% for TIMI-3 culprits. Specificity for no-AMI 79.7%. AUC 0.952.

**Portuguese external validation (EHJ-DH 2026, vol 7 suppl 1, ztaf143.130), abstract only.** [PMC12794886](https://pmc.ncbi.nlm.nih.gov/articles/PMC12794886)
- N = 812 AMI patients.
- The reference OMI was set by "central adjudication" using presentation, angiography and serial troponin. **No thresholds are given.** Excluded from the comparison table for that reason.
- Performance figures came from a search snippet and were **not verified** by me.

**AI-ECG TIMI design paper (Herman R, et al. *JSCAI* 2025;4(3 Pt B):102494).** DOI [10.1016/j.jscai.2024.102494](https://doi.org/10.1016/j.jscai.2024.102494). [PMC11993865](https://pmc.ncbi.nlm.nih.gov/articles/PMC11993865/)
- Protocol only, no results.
- Prospective registry of more than 700 ACS patients with an ECG recorded **at the time of angiography**.
- Primary endpoint is an **actively occluded (TIMI 0–1)** culprit. A new model will separate "actively occluded (TIMI 0–1)" from "open/reperfused (TIMI 2–3)".
- The authors explicitly acknowledge that Herman 2024 could not confirm active occlusion at the time of the ECG.

---

### 5. Other label-relevant primary sources

**Gustafsson S, Ribeiro AH, Gedon D, et al. A deep learning ECG model for identification and localization of OMI. *Nat Commun* 2026;17:4336.** DOI [10.1038/s41467-026-73023-1](https://doi.org/10.1038/s41467-026-73023-1). [PMC13171952](https://pmc.ncbi.nlm.nih.gov/articles/PMC13171952/)
- **Population:** Stockholm ED ECGs 2005–2016 (SwED): 540,372 ECGs. Labels: 1,583 OMI, 4,279 nOMI, 534,510 controls.
- **OMI definition:** **angiography only, no troponin.** OMI is the SWEDEHEART/SCAAR "OCKL" variable, a newly formed occlusion set by the angiographer at the procedure. The Results describe it as "TIMI blood flow 0", with acute vs chronic distinguished by guidewire behaviour.
- **Time windows:** MI cases had to undergo **angiography within 7 days**. The ECG had to be within 24 h of the visit.
- **Negatives:** "control" means no MI (ICD I21–I23 absent). Non-catheterized non-MI visits are controls.
- **Stated rationale for excluding troponin:** STEMIs bypass troponin testing, troponin is low early, and the acuity of non-total occlusions is unknown (Discussion).
- **InCor (Brazil) external set:** uses a different label (culprit ≥ 95% obstruction during the ED admission). Controls were ED patients **never catheterized**.

**McLaren JTT, Meyers HP, Smith SW, Chartier LB. From STEMI to occlusion MI: paradigm shift and ED quality improvement. *CJEM* 24(3):250.** DOI [10.1007/s43678-021-00255-z](https://doi.org/10.1007/s43678-021-00255-z). [PMC9001399](https://pmc.ncbi.nlm.nih.gov/articles/PMC9001399/)
- A review, not a study. It restates the Meyers definition for QI use.
- It expresses "highly elevated troponin" generically as **70–300 times the 99th-percentile URL, depending on assay**. This is a useful assay-agnostic framing.

**Khan AR, Golwala H, et al. *Eur Heart J* 2017;38(41):3082–3089.** DOI [10.1093/eurheartj/ehx418](https://doi.org/10.1093/eurheartj/ehx418). [PubMed abstract](https://pubmed.ncbi.nlm.nih.gov/29020244/)
- **Abstract only.**
- 7 studies, 40,777 NSTEMI patients. 25.5% had a totally occluded culprit, with higher mortality (short-term RR 1.67).
- The TIMI definition of "total occlusion" is **not stated in the abstract**, so I cannot verify it.

**Hung CS, Chen YH, et al. *Crit Care* 2018;22:34.** DOI [10.1186/s13054-018-1944-x](https://doi.org/10.1186/s13054-018-1944-x). [PMC5806289](https://pmc.ncbi.nlm.nih.gov/articles/PMC5806289/)
- 25 studies. Pooled occluded-culprit prevalence in NSTEMI **34% (95% CI 30–37%)**.
- The occluded-culprit definition varied by study (TIMI 0–1, TIMI 0 only, TIMI 1 only, or TIMI 0–2). TIMI 0–1 was the most common.
- Demonstrates that "occlusion" itself is not standardised.

**Polish ORPKI national registry, "Impact of acute total occlusion of the culprit artery on outcome in NSTEMI" (BMC Cardiovasc Disord 2021; authors not recorded here).** DOI [10.1186/s12872-021-02099-y](https://doi.org/10.1186/s12872-021-02099-y). [PMC8204478](https://pmc.ncbi.nlm.nih.gov/articles/PMC8204478/)
- Defines acute total occlusion as **TIMI 0 only**. 19.9% of single-vessel-PCI NSTEMIs.

---

### Comparison table

Key: TnT/TnI = contemporary or 4th-generation; hs = high-sensitivity. "WMA" = new or presumed-new regional wall-motion abnormality.

| Study | TIMI rule | Troponin threshold per assay | Time window | Transient / reperfused OMI | No-angio handling | Negatives | STEMI comparator | Key performance |
|---|---|---|---|---|---|---|---|---|
| Meyers 2021 IJCHV ([PMC8065286](https://pmc.ncbi.nlm.nih.gov/articles/PMC8065286/)) | Culprit TIMI 0–2 = OMI. TIMI 3 culprit = OMI only with troponin | TnT ≥ 1.0 ng/mL (Roche); TnI ≥ 10.0 ng/mL (Abbott). Supplement says ">" | None. STEMI(+) if any pre-angio ECG met criteria | Via the troponin threshold only | OMI if troponin above threshold + WMA, or STEMI(+) ECG with death before angio. Else per chart AMI dx (NOMI). Undecidable excluded (6) | NOMI (AMI without OMI evidence); MIRO | Human 4UDMI, J-point vs PQ, blinded, any serial ECG | Sens/spec: OMI findings 86/91 vs STEMI 41/94. 59% of OMI STEMI(−) |
| Meyers 2021 JEM ([abstract](https://pubmed.ncbi.nlm.nih.gov/33308915/)) | TIMI 0–2, or TIMI 3 + troponin | TnT > 1.0 ng/mL | n/a (abstract) | Via troponin | Not verifiable | "No occlusion" | Not verifiable | 40% of OMI STEMI(−); cath delay 437 vs 41 min |
| DIFOCCULT 2020 ([PMC7399112](https://pmc.ncbi.nlm.nih.gov/articles/PMC7399112/)) | Any total occlusion or culprit (TIMI not specified) + troponin rule | TnI ≥ 1.0 ng/mL + ≥ 20% rise in 24 h with culprit; **or TnI > 5.0 ng/mL alone**. One cTnI assay | Admission ECG; rise within 24 h | Captured by composite; ECG type 1d = reperfused STE | ACO possible via troponin > 5.0 or arrest before troponin rise | Composite-negative; rule-out controls | Two blinded cardiologists, 4UDMI, admission ECG; STEMI = types 1a/1c/1d | AUC ACOMI 0.819 vs STEMI 0.792 (weighted 0.823 vs 0.736); 28% of NSTEMI reclassified |
| Al-Zaiti 2023 ([PMC10353937](https://pmc.ncbi.nlm.nih.gov/articles/PMC10353937/)) | TIMI 0–1; TIMI 2 only with > 70% stenosis + troponin; TIMI 3 never | Peak 4th-gen troponin "5–10 ng/mL" (range, assay unspecified) **[UNCERTAIN]** | Prehospital ECG; records ≤ 30 d | TIMI 3 = negative | Effectively negative (angio required) | All non-OMI incl. NOMI, UA; type 2 MI and subacute occlusion negative | No STEMI arm (prehospital STEMI excluded); clinicians' 4UDMI-plus-judgement read; Philips software | External AUROC 0.87 vs clinicians 0.80 vs software 0.75 |
| Herman 2024 ([PMC10944682](https://pmc.ncbi.nlm.nih.gov/articles/PMC10944682/)) | TIMI 0–1, or TIMI 2–3 **with urgent PCI** (primary); troponin variants secondary | None in primary. Secondary hs-TnT ≥ 500 / ≥ 1000 ng/L. Supplement footnote contradicts (TIMI 0–2 or TIMI 3 + TnT ≥ 1000) **[UNCERTAIN]** | ECGs > 24 h before or after angio discarded | Included via urgent PCI | AMI without angio absent from Aalst data; troponin-negative rule-outs = not-OMI | No MI, or NOMI (no culprit or not needing immediate revascularization) | Blinded human 4UDMI; max per patient over pre-angio ECGs | AI 80.6/93.7, AUC 0.938; STEMI 32.5/97.7; experts 73.0/95.7; 67.5% of OMI STEMI(−) |
| Karim 2025 ([PMC12028524](https://pmc.ncbi.nlm.nih.gov/articles/PMC12028524/)) | TIMI 0–2, or TIMI 3/unknown + troponin or WMA; culprit **with intervention** required | hs-TnI > 5000 ng/L; TnI > 10 ng/mL; hs-TnT > 1000 ng/L; TnT > 1.0 ng/mL | Pre-PCI ECGs | Via troponin/WMA | Not included (angio + intervention required) | None (case series) | Not a comparator study | 81% of first ECGs called OMI by AI |
| Cooper 2026 ([PMC12853124](https://pmc.ncbi.nlm.nih.gov/articles/PMC12853124/)) | TIMI 0–2 + any positive troponin; TIMI 3 + very high troponin | hs-TnT ≥ 1000 ng/L; hs-TnI ≥ 5000 ng/L; TnI > 10.0 ng/mL; TnT > 1.0 ng/mL | ECG that drove activation | Via troponin | Death before cath excluded; troponin rule-out = false positive | False-positive activations | "Millimetre criteria" (applier not stated) | AI 89.2/72.9 vs STEMI 68.3/51.7 |
| Lindow 2026 ([PMC13482599](https://pmc.ncbi.nlm.nih.gov/articles/PMC13482599/)) / Nyström 2026 ([PMC12818230](https://pmc.ncbi.nlm.nih.gov/articles/PMC12818230/)) | Registry acute occlusion; or revascularized stenosis + hs-TnT ≥ 1000 (no TIMI); or reviewed TIMI 0–1 | hs-TnT ≥ (or >) 1000 ng/L | AMI/revascularization within 30 d; first ECG | Via revascularization + troponin | Lindow: hs-TnT ≥ 1000 alone. Nyström: plus WMA or STEMI-arrest **[UNCERTAIN]** | NOMI + no AMI | **Automated** Glasgow/Uni-G 4UDMI measurements | QoH 52/99 vs STEMI 23/98 (Lindow); in-house AI 62 vs 27 at spec 97.4 (Nyström) |
| Carvalho 2026 ([PMC13053991](https://pmc.ncbi.nlm.nih.gov/articles/PMC13053991/)) | TIMI 0–2, or TIMI 3/unknown + troponin or WMA | hs-TnT ≥ 1000 ng/L; hs-TnI > 5000 ng/L; TnI > 10.0 ng/mL; TnT > 1.0 ng/mL (before revascularization) | Initial ECG; emergent angio | Via troponin/WMA | All had angio | Non-OMI on angio | STEMI excluded; comparator = SOC activation | AI sens 58%, spec 78% |
| Sharkey 2026 ([PMC13019798](https://pmc.ncbi.nlm.nih.gov/articles/PMC13019798/)) | Positive = any culprit + troponin > 99th (any TIMI) | 99th percentile | Activating ECG | Counted positive | All activated | No-AMI (troponin < 99th, no culprit) | None | Sens 93.8, spec 79.7, AUC 0.952 |
| Gustafsson 2026 ([PMC13171952](https://pmc.ncbi.nlm.nih.gov/articles/PMC13171952/)) | Angiographer-coded new occlusion (≈ TIMI 0) | **None** | MI cases angio ≤ 7 d; ECG ≤ 24 h | Not OMI (nOMI) | MI without angio excluded; non-MI = control | nOMI and no-MI controls | 12SL statements (supplement) | C-statistic ≥ 0.95 OMI vs rest |

---

### Implications for an operational OMI label (MY SYNTHESIS, not a source claim)

#### Where the studies agree
- **Anchor class.** An **acute culprit with TIMI 0–1** is OMI in every study, whichever definition it uses. Only Gustafsson (≈ TIMI 0 only) and the Polish registry are stricter.
- **TIMI 2.** Usually OMI: Meyers, Karim, Cooper, Carvalho, and the QoH training label as reported by Sharkey. It is conditional in Al-Zaiti (> 70% stenosis plus troponin) and in Herman's primary definition (urgent PCI).
- **TIMI 3 counts only with an infarct-size surrogate.** The Smith/Meyers lineage converges on one set of "very high peak troponin" numbers:

| Assay | Threshold |
|---|---|
| Contemporary / 4th-gen cTnT | 1.0 ng/mL |
| Contemporary / 4th-gen cTnI | 10 ng/mL |
| hs-cTnT | 1000 ng/L |
| hs-cTnI | 5000 ng/L |

  Sources: Karim, Cooper, Carvalho, Lindow (hs-TnT). The hs thresholds do **not** appear in Meyers 2021 itself. They appear in later papers in the same lineage, so treat the hs-cTnI 5000 ng/L figure as a lineage convention, not an independently validated cutoff.
- **Fallback when there is no troponin peak.** The usual fallback is a **new or presumed-new regional WMA**.
- **No angiography.** Most Meyers-lineage studies call these OMI only with very high troponin **plus** WMA, or a STEMI(+) ECG with death before angiography.
- **Negatives.** Negatives pool NOMI with no-MI, and they are generally **not angiographically verified**. Troponin-negative rule-outs make up the bulk of negatives in Herman, Lindow and Gustafsson.

#### Where they differ (and why it matters for a label)
1. **Inequality signs.** Meyers uses ≥, Karim uses >, Cooper mixes the two. This is harmless in practice, but pick one and document it.
2. **Troponin threshold scale.**
   - DIFOCCULT uses **cTnI > 5.0 ng/mL standalone, with no angiography needed**, and 1.0 ng/mL with a culprit.
   - Al-Zaiti uses "5–10 ng/mL" only for TIMI 2.
   - Meyers uses 10 ng/mL for TnI.
   - That is a 2× spread for contemporary cTnI between studies.
3. **Urgent PCI vs troponin.** Herman's primary label uses **urgent PCI** for TIMI 2–3 instead of troponin. That ties the label to clinicians' decisions, and through them partly to the ECG, which is a label-leakage risk for an ECG model. Lindow's "revascularized + hs-TnT ≥ 1000" path has no TIMI condition at all.
4. **No-angiography AMI.** The handling varies widely:
   - excluded (Herman Aalst, Gustafsson);
   - negative (Al-Zaiti);
   - troponin plus WMA (Meyers, Nyström);
   - troponin alone (Lindow's wording, DIFOCCULT).
5. **TIMI 3 / transient.** Positive via troponin (Meyers lineage), positive via PCI (Herman), always negative (Al-Zaiti, Gustafsson), or split into its own class (AI-ECG TIMI design, DIFOCCULT type 1d).
6. **STEMI comparator.** The comparator varies along three axes:
   - **reader:** human 4UDMI reading (Meyers, Herman, DIFOCCULT) vs automated measurement (Lindow, Nyström);
   - **ECGs used:** any serial ECG (Meyers, Herman max-per-patient) vs the first ECG only (Lindow, DIFOCCULT);
   - **population:** activation-based (Cooper, Sharkey: STEMI-alert cohorts, not criteria).

   Reported STEMI-criteria sensitivity ranges from 23% to 70%, largely because of these choices and the case mix.

#### A label that degrades gracefully (proposal)
Represent the label as a sum type with provenance rather than a boolean, so that training and evaluation can filter by evidence tier:

```
OmiLabel =
  | OMI      { tier, evidence }
  | NotOMI   { tier, evidence }
  | Unknown  { reason }

tier (strongest → weakest):
  A  angiography with documented TIMI flow
  B  angiography with culprit but TIMI unknown
  C  no angiography
```

Suggested rules, applied in order:

1. **A-positive.** An acute culprit with TIMI 0–1 → OMI.
   - TIMI 2 → OMI. This is the Meyers convention; keep a flag so a stricter TIMI 0–1 analysis can be rerun.
2. **A-positive via infarct size.** An acute culprit with TIMI 3, or flow unknown (tier B), is OMI if peak troponin is at or above the assay-specific threshold: cTnT 1.0 ng/mL, cTnI 10 ng/mL, hs-cTnT 1000 ng/L, hs-cTnI 5000 ng/L.
   - **If the troponin is known but its assay is not**, do not guess a threshold. Either:
     - (a) require the value to clear the **highest plausible** threshold for its unit family (ng/L → 5000, ng/mL → 10), which gives a conservative positive; or
     - (b) use a multiple of the assay's 99th-percentile URL if the URL is known. McLaren cites 70–300 × URL; pick a fixed multiple and record it.
   - Otherwise, use a new regional WMA if echo is available.
   - Otherwise → Unknown. Do not call it negative.
3. **A-negative.** An angiogram with no acute culprit, or a culprit with TIMI 3 and troponin below threshold with no WMA → NotOMI.
   - Flag the "TIMI 3 + sub-threshold" subgroup. Meyers shows these include true reperfused OMIs.
4. **C (no angiography).**
   - Troponin ≥ threshold **plus** WMA → OMI (tier C).
   - STEMI(+) ECG with death before angiography → OMI (tier C). Flag it, because the ECG feeds the label (circular for an ECG model).
   - Troponin ≥ threshold **without** WMA → Unknown, or OMI-probable if you follow Lindow and DIFOCCULT. Keep it separate.
   - Serial troponin negative, with no rise or fall → NotOMI (tier C). This is the Herman rule.
   - Otherwise (an AMI with neither) → Unknown, not NotOMI. Al-Zaiti and Meyers implicitly treat it as negative. That choice inflates specificity and should be an explicit switch.
5. **Only troponin known, no imaging or clinical data.** Assign at most "OMI-probable (troponin-only)" or "NotOMI (troponin-negative)", and record the tier.
6. **Timing.** Store the ECG-to-angiography interval. Use only pre-angiography ECGs. A ≤ 24 h pre-angiography window (Herman) is a reasonable default. Keep the interval so that a TIMI 0–1 result far after the ECG can be down-weighted.
7. **Exclusions to make explicit:** type 2 MI, chronic total occlusion, myopericarditis, and chronic troponin leak → NotOMI (Al-Zaiti), not Unknown.

This keeps every published convention reproducible as a filter over tiers and flags. For example:
- **Meyers-2021-compatible** = tiers A, B and C with the TIMI 0–2 / troponin / WMA / death rules.
- **Herman-primary-compatible** needs an urgent-PCI flag.
- **Al-Zaiti-compatible** = tier A with TIMI 0–1 or TIMI 2 + troponin; everything else negative.
- **Gustafsson-compatible** = registry acute occlusion only.

It also avoids silently converting missing facts into negatives.

## Part 2: STEMI criteria: definitions, and automatic application to a 12-lead ECG

**How the sources were accessed** (so you can judge each claim):

| Source | What I read |
|---|---|
| Fourth UDMI (Thygesen 2018, EHJ version) | Full text: the publisher PDF (CC BY) in the Amsterdam UMC repository |
| AHA/ACCF/HRS 2009 Part VI (Wagner et al.) | Full text: the JACC version, from a third-party mirror. The publisher and HRS sites blocked automated access. |
| 2023 ESC ACS guideline | Full text: the publisher PDF in the ORBi (Liège) repository |
| 2025 ACC/AHA/ACEP/NAEMSP/SCAI ACS guideline | Full text: the JACC PDF, from a third-party mirror. The publisher site blocked access. |
| GE 12SL | Full text of the "Statement of Validation and Accuracy" (416791-003 Rev B, 2007) and of GE patent US6507753B1. I could **not** get the 12SL *Physician's Guide* (2056246-002C). |
| PTB-XL+ / MIMIC-IV-ECG | The PhysioNet project pages, the data files themselves, and the PTB-XL+ paper (full text, PMC) |
| Accuracy studies | Marked one by one as **[full text]** or **[abstract only]** |

Nothing below is invented. Wherever I could not verify something, the text says so.

---

### 1. Guideline definitions

#### 1.1 Fourth Universal Definition of MI (Thygesen et al., 2018)

Source: the EHJ version, *Eur Heart J* 2019;40:237–269, doi:10.1093/eurheartj/ehy462. The full text I read is the publisher PDF at https://pure.amsterdamumc.nl/ws/files/156952229/Fourth-universal-definition-of-myocardial-infarction-2018.pdf. The same document was co-published in *Circulation* (doi:10.1161/CIR.0000000000000617), *JACC* (doi:10.1016/j.jacc.2018.08.1038) and *Global Heart* (doi:10.1016/j.gheart.2018.08.004). I compared only the EHJ text.

**Table 2, verbatim from the EHJ PDF.** Title: "Electrocardiographic manifestations suggestive of acute myocardial ischaemia (in the absence of left ventricular hypertrophy and bundle branch block)".

> **ST-elevation**
> New ST-elevation at the J-point in two contiguous leads with the cut-point: ≥ 1 mm in all leads other than leads V2–V3 where the following cut-points apply: ≥ 2 mm in men ≥ 40 years; ≥ 2.5 mm in men < 40 years, or ≥ 1.5 mm in women regardless of age.^a
>
> **ST-depression and T wave changes**
> New horizontal or downsloping ST-depression ≥ 0.5 mm in two contiguous leads and/or T inversion > 1 mm in two contiguous leads with prominent R wave or R/S ratio > 1.
>
> ^a When the magnitudes of J-point elevation in leads V2 and V3 are registered from a prior electrocardiogram, new J-point elevation ≥ 1 mm (as compared with the earlier electrocardiogram) should be considered an ischaemic response. For bundle branch block, see section below.

- **Wording of the exclusion.** In the EHJ PDF, the Table 2 title excludes "bundle branch block", not just LBBB. Many secondary sources, and the task brief, say "LVH and LBBB". The 2023 ESC guideline (§1.3) phrases the exclusion as LV hypertrophy or LBBB. The 2009 AHA Part VI (§1.2) says RBBB does **not** affect the ST criteria. For RBBB, UDMI §32 says: "new or presumed new ST-segment elevation ≥ 1 mm, or ST-segment or T wave abnormalities (excluding leads V1–V4) (Table 2), may indicate acute myocardial ischaemia". The sentence is ambiguous about whether "excluding V1–V4" also applies to the STE part.

**Measurement point (UDMI §27), quoted from the PDF:**

> "The J-point (junction between QRS termination and ST-segment onset) is used to determine the magnitude of the ST-segment shift with the onset of the QRS serving as the reference point. In patients with a stable baseline, the TP segment (isoelectric interval) is a more accurate method to assess the magnitude of ST-segment shift, and in distinguishing pericarditis (PTa depression) from acute myocardial ischaemia. Tachycardia and baseline shift are common in the acute setting and can make this determination difficult. Therefore, QRS onset is recommended as the reference point for J-point determination (Figure 8)."

- Figure 8 caption: "The initial onset of the Q wave shown by arrow 1 serves as the reference point and arrow 2 shows the onset of the ST-segment or J-point … Measurements of both arrows should be made from the top of the electrocardiogram line tracing."
- "New, or presumed new, J-point elevation ≥ 1 mm (1 mm = 0.1 mV) is required in all leads other than V2 and V3 as an ischaemic response."

**Contiguity**

- "The criteria in Table 2 require that the ST shift be present in two or more contiguous leads. For example, ≥ 2 mm of ST-elevation in lead V2 and ≥ 1 mm in lead V1 would meet the criteria of two abnormal contiguous leads in a man ≥40 years old." Note that the leads in a pair can carry different lead-specific thresholds.
- "≥ 1 mm and < 2 mm of ST-elevation, seen only in leads V2–V3 in men (or < 1.5 mm in women), may represent a normal finding."
- The UDMI text has **no** Cabrera definition. The only explicit lead grouping in the document is in Table 3 (prior-MI Q waves): "contiguous lead grouping (I, aVL; V1–V6; II, III, aVF)". The Cabrera / −aVR ordering comes from the 2009 AHA statement (§1.2).

**aVR, posterior and right-sided leads (UDMI §27–28)**

- "ST-elevation in lead aVR > 1 mm may accompany anterior or inferior STEMI, and is associated with increased 30 day mortality."
- The "What's new" box lists "ST-segment elevation in lead aVR with specific repolarization patterns, as a STEMI equivalent."
- ST-segment depression ≥1 mm in six leads, with ST-elevation in aVR or V1, suggests multivessel or left main disease.
- **V7–V9:** "A cut-off point of 0.5 mm ST-elevation is recommended in leads V7–V9; specificity is increased at a cut-off point ≥ 1 mm ST-elevation and this cut-off point should be used in men < 40 years old."
- Isolated ST-depression ≥0.5 mm in V1–V3 may indicate left circumflex occlusion. ST-depression in V1–V3, "especially when the terminal T wave is positive (ST-elevation equivalent)", is "non-specific" per UDMI.
- **V3R/V4R:** "ST-elevation ≥ 0.5 mm (≥ 1 mm in men < 30 years old) provides supportive criteria for the diagnosis" of RV infarction.
- **LBBB:** "ST-segment elevation ≥ 1 mm concordant with the QRS complex in any lead may be an indicator of acute myocardial ischaemia." The same applies to RV-paced rhythm.
- **Reciprocity:** "Prolonged new convex ST-segment elevation, particularly when associated with reciprocal ST-segment depression, usually reflects acute coronary occlusion … Reciprocal changes can help to differentiate STEMI from pericarditis or early repolarization changes."
- "A prior ECG is often helpful in distinguishing a new from a chronic finding, but should not delay the decision for treatment." Confounders listed: pericarditis, LVH, LBBB, Brugada, TTS (takotsubo syndrome), early repolarization.

**STEMI vs NSTEMI (UDMI §7):** STEMI is a clinical label for treatment triage, not an MI "type":

> "… it is usual practice to designate MI in patients with chest discomfort or other ischaemic symptoms, who develop new ST-segment elevations in two contiguous leads or new bundle branch blocks with ischaemic repolarization patterns as an ST-elevation MI (STEMI) … In contrast, patients without ST-segment elevation at presentation are usually designated non-ST-elevation MI (NSTEMI)."

It is "essential to integrate the ECG findings with the aim of classifying type 1 MI into STEMI or NSTEMI".

**Troponin parts and MI types (UDMI §2 summary box; EHJ PDF)**

- **Myocardial injury:** "elevated cardiac troponin values (cTn) with at least one value above the 99th percentile upper reference limit (URL). The myocardial injury is considered acute if there is a rise and/or fall of cTn values."
- **Acute MI (types 1, 2, 3):** acute myocardial injury with clinical evidence of acute myocardial ischaemia, plus a rise and/or fall of cTn with ≥1 value >99th percentile URL, plus at least one of the following:
  - ischaemic symptoms
  - new ischaemic ECG changes
  - pathological Q waves
  - imaging evidence of new loss of viable myocardium or a new regional wall-motion abnormality
  - coronary thrombus on angiography or autopsy (not for type 2 or 3)
- **Type 1:** atherothrombotic, usually plaque rupture or erosion. Its criteria box repeats the list above, including "Identification of a coronary thrombus by angiography including intracoronary imaging or by autopsy".
- **Type 2:** the same cTn criterion, plus "evidence of an imbalance between myocardial oxygen supply and demand unrelated to acute coronary athero-thrombosis", plus ≥1 of the clinical items above (no thrombus item).
- **Why this matters for labels:** "STEMI" is a property of the **ECG at presentation**. MI type 1 or 2 is a **final diagnosis** that needs troponin and clinical adjudication. A STEMI-criteria-positive ECG can end up as type 1 MI, type 2 MI, myocardial injury without MI, or no MI. UDMI §31 lists the mimics.

#### 1.2 AHA/ACCF/HRS 2009, Part VI: Acute Ischemia/Infarction (Wagner et al.)

Source: *Circulation* 2009;119:e262–e270, doi:10.1161/CIRCULATIONAHA.108.191098; *JACC* 2009;53:1003–11, doi:10.1016/j.jacc.2008.12.016. It is endorsed by the International Society for Computerized Electrocardiology. I read the full JACC text from the mirror https://fd.org.ua/wp-content/uploads/2019/03/AHAA-CCF-HRS-Recommendations-for-the-Standardization-and-Interpretation-of-the-Electrocardiogram-Part-VI.pdf (the publisher and HRS pages returned HTTP 403 to automated access).

**Threshold recommendations, verbatim:**

> 1. For men 40 years of age and older, the threshold value for abnormal J-point elevation should be 0.2 mV (2 mm) in leads V2 and V3 and 0.1 mV (1 mm) in all other leads.
> 2. For men less than 40 years of age, the threshold values for abnormal J-point elevation in leads V2 and V3 should be 0.25 mV (2.5 mm).
> 3. For women, the threshold value for abnormal J-point elevation should be 0.15 mV (1.5 mm) in leads V2 and V3 and greater than 0.1 mV (1 mm) in all other leads.
> 4. For men and women, the threshold for abnormal J-point elevation in V3R and V4R should be 0.05 mV (0.5 mm), except for males less than 30 years of age, for whom 0.1 mV (1 mm) is more appropriate.
> 5. For men and women, the threshold value for abnormal J-point elevation in V7 through V9 should be 0.05 mV (0.5 mm).
> 6. For men and women of all ages, the threshold value for abnormal J-point depression should be −0.05 mV (−0.5 mm) in leads V2 and V3 and −0.1 mV (−1 mm) in all other leads.

Notes on these recommendations:

- They mix "should be X" with "greater than 0.1 mV" (rec. 3). The ≥ versus > boundary is therefore not uniform across documents. UDMI 2018 uses ≥ throughout.
- The statement's background text, citing its reference 4 (the 2000 ESC/ACC document), describes the *older* standard as "greater than 0.2 mV (2 mm with standard calibration) in leads V1, V2, and V3 and greater than 0.1 mV in all other leads". Implementations that copy that text will use 2 mm in V1, which is wrong under the current definition.

**Contiguity and the Cabrera format, verbatim:**

> "For these leads to be displayed in their anatomically contiguous manner, that is, from left superior-basal to right inferior, the display should be aVL, I, −aVR (i.e., lead aVR with reversed polarity), II, aVF, and III. With this configuration, −aVR exists at 30° in the hexaxial frontal plane, that is, midway between limb lead I (at 0°) and limb lead II (at 60°). This display, known as the Cabrera format …"

- The chest leads are contiguous in V1→V6 order.
- Recommendation: "ECG machines should be equipped with switching systems that will allow the limb leads to be displayed and labeled appropriately in their anatomically contiguous sequence."

**Other content relevant to automation:**

- The statement contains explicit recommendations to automated algorithms:
  - name the occluded vessel or site
  - suggest V3R/V4R recording when ST elevation >0.1 mV in II, III, aVF
  - flag possible multivessel or left-main disease for ST-depression >0.1 mV in ≥8 leads with ST-elevation in aVR and/or V1
  - flag LBBB cases that meet the GUSTO-I (Sgarbossa) concordance criteria
- It does **not** specify the isoelectric reference (PR/TP/QRS onset) or J+x ms. It only says ST elevation is "measured at the J point".
- "ST-segment criteria for the diagnosis of acute ischemia/infarction are not affected by the presence of fascicular blocks or by right bundle-branch block. They are affected by the presence of left bundle-branch block …"

#### 1.3 2023 ESC Guidelines for the management of ACS (Byrne et al.)

Source: *Eur Heart J* 2023;44:3720–3826, doi:10.1093/eurheartj/ehad191. I read the full text from https://orbi.uliege.be/bitstream/2268/329460/1/ehad191.pdf.

**§3.2.1, verbatim:**

> "In the appropriate clinical context, ST-segment elevation (measured at the J-point) is considered suggestive of ongoing coronary artery acute occlusion in the following cases: New ST elevation at the J-point in at least two contiguous leads: • ≥2.5 mm in men <40 years, ≥2 mm in men ≥40 years, or ≥1.5 mm in women regardless of age in leads V2–V3 • and/or ≥1 mm in the other leads (in the absence of left ventricular [LV] hypertrophy or left bundle branch block [LBBB])."

**Occlusion without ST elevation:**

> "The diagnosis of ongoing acute coronary artery occlusion on ECG can sometimes be challenging, and some cases may warrant prompt management and triage for immediate reperfusion therapy despite the absence of ST-segment elevation. It is also important to recognize that while the most sensitive sign for ongoing acute coronary artery occlusion is ST-segment elevation, there are other ECG findings that can be suggestive of ongoing coronary artery occlusion (or severe ischaemia). If these findings are present, prompt triage for immediate reperfusion therapy is indicated (see Supplementary data online, Figure S2)."

The patterns it names are:

- ST-depression in V1–V3, especially with a positive terminal T wave, and/or STE in V7–V9 (posterior occlusion)
- STE in V3R/V4R (RV ischaemia)
- ST-depression ≥1 mm in ≥6 leads with STE in aVR and/or V1 (multivessel or left main disease)
- LBBB, RBBB or paced rhythm with high clinical suspicion: "should be managed similarly to those with clear ST-segment elevation, regardless of whether the BBB is previously known"

**Where the guideline stands on STEMI vs occlusion:**

- The working diagnosis is defined as "persistent ST-segment elevation (or ST-segment elevation equivalents)".
- The guideline frames STE as a marker of "ongoing coronary artery acute occlusion".
- It does **not** use the term "OMI" or "occlusion MI": a whole-word search of the full text for "OMI" returns nothing.
- Supplementary Figure S2, which lists the occlusion patterns, is in the online supplement. **I did not read it.**
- It recommends additional leads (V3R, V4R, V7–V9) "in cases of inferior STEMI or if total vessel occlusion is suspected and standard leads are inconclusive". This is in Recommendation Table 1. The PDF text extraction scrambles the class/level column, so I do not report the class.

#### 1.4 2025 ACC/AHA/ACEP/NAEMSP/SCAI ACS guideline (Rao et al.)

Source: *JACC* 2025;85:2135–2237, doi:10.1016/j.jacc.2024.11.009, and *Circulation*, doi:10.1161/CIR.0000000000001309. I read the full JACC PDF from a third-party copy (https://nendkvqenyirntfzhefa.supabase.co/storage/v1/object/public/stat-docs/_pda/2025/12/2025-ACCAHAACEP-ACS-Guideline.pdf). The publisher sites returned 403. Please verify against the DOI.

**Table 3, "Electrocardiographic Interpretation for Patients With Suspected ACS". It is adapted from Thygesen 2018 and from Kontos 2022 (the ACC chest-pain Expert Consensus Decision Pathway).**

- STEMI: "New or presumed new ST-segment elevation of ≥1 mm in ≥2 anatomically contiguous leads (measured at the J-point) in all leads other than V2-V3 and ≥2 mm in men ≥40 y, ≥2.5 mm in men <40 y, and ≥1.5 mm in women regardless of age in leads V2-V3."
- "Posterior leads (V7-V9) should be obtained in patients with suspected left circumflex occlusion particularly in the setting of isolated ST-segment depression ≥0.5 mm in leads V1-V3."
- Footnote, verbatim: "New or presumably new LBBB at presentation occurs infrequently and should not be considered diagnostic of AMI in isolation; clinical correlation is required. A new LBBB in an asymptomatic patient does not constitute a STEMI equivalent."
- In the PDF text extraction, "≥" appears as "$". I have rendered it back as ≥.

**Text:** "When ST-segment elevation or an equivalent finding is present on the initial ECG (Table 3), initial management and triage should follow the prescribed STEMI treatment algorithm."

- A whole-word search for "OMI" returns nothing, and "de Winter", "hyperacute" and "Sgarbossa" do not appear in the body text (Sgarbossa appears only in a reference title).
- So the 2025 US guideline keeps the STEMI paradigm, with an undefined "equivalent". It points readers to Kontos 2022 for the equivalents, which I did not read.

---

### 2. Computing STEMI criteria from a signal

#### 2.1 Measurement point and baseline

| Source | Amplitude reference | ST measurement point(s) |
|---|---|---|
| 4th UDMI (EHJ PDF) | **QRS onset** recommended; TP segment "more accurate" when the baseline is stable | J-point (end of QRS) |
| ESC 2023 / ACC-AHA 2025 | not restated | "measured at the J-point" |
| AHA 2009 Part VI | not specified | J-point |
| GE 12SL (Statement of Validation 416791-003 Rev B, 2007, p.18) | "All amplitudes measured with respect to QRS onset" | **STJ** = QRS offset; **STM** = STJ + 1/16 of average RR; **STE** = STJ + 1/8 of average RR |
| Glasgow / Uni-G (Macfarlane, Devine, Clark, *Computers in Cardiology* 2005:451–4) | "All QRST amplitudes are referred to QRS onset". Lindow 2026 calls this "relative to the PQ junction". | ST at J, plus ST at J+80 ms, 2/8 and 3/8 of ST-T, and ST slope (PTB-XL+ feature list) |
| Meyers et al. 2021 (manual reads) | "measured in millimeters using the QRS onset (PQ junction) and the J-point" | J-point |
| Pelter et al. 1997 (ST monitoring research) | "isoelectric line" | J + 80 ms |

Sources for the table:

- GE: https://www.numed.co.uk/documents/download/216
- Uni-G: https://www.cinc.org/archives/2005/pdf/0451.pdf
- Lindow 2026: https://pmc.ncbi.nlm.nih.gov/articles/PMC13482599/
- Meyers 2021: https://pmc.ncbi.nlm.nih.gov/articles/PMC8065286/
- Pelter 1997: doi:10.1016/s0022-0736(97)80025-8 **[abstract only]**

**Practical consequences:**

- **Use J-point and QRS-onset reference.** The guideline criteria are defined **at the J-point**. J+60 or J+80 ms values are for exercise or monitoring and research, and are *not* the guideline STEMI measurement. Measuring at J+60/80 will inflate STE in hyperacute or upsloping segments. Use QRS onset (the PQ junction) as the zero reference to match UDMI and both major commercial programs.
- **Global versus per-lead fiducials.** Uni-G derives **global** QRS onset and offset: "selecting the earliest QRS onset … A similar approach is adopted for QRS termination". The J-point in each lead's median beat is therefore a common global instant, not a per-lead QRS end. Per-lead delineators such as ECGdeli or NeuroKit2 give per-lead offsets. That choice changes STJ, especially in leads where the QRS ends early. Document which you use.
- **Median beat versus per-beat.** Both commercial programs measure on a median (representative) beat. ECGdeli reports the median and IQR across beats (PTB-XL+ page).
- **Systematic measurement differences:**
  - Eskola et al. 2005 (*Am J Cardiol* 96:1584, doi:10.1016/j.amjcard.2005.07.075) **[abstract only]**: "automatically measured ST-segment deviations were smaller than those manually measured". Agreement with a cardiologist for STE ≥0.2 mV was κ=0.72 in V2 and 0.85 in V3. Bland–Altman limits for ST deviation were "clinically inadequate". The optimal computer cut-off to detect a manual ≥0.2 mV STE was 0.115 mV.
  - Pelter 1997 (J+80, isoelectric reference) found the opposite: computer *greater* than manual, which the authors attribute to humans rounding down to 50 µV.
  - So **computer and manual STEMI-criteria labels are not interchangeable.** Pelter: computer and manual ST measurements "should not be mixed when used as a variable for research".
- **Failure modes of automated guideline criteria.** Hillinger et al. 2019 (*Int J Cardiol*, doi:10.1016/j.ijcard.2019.04.041) **[abstract only]** applied guideline criteria with "automated software-based analysis" to 2,486 ED patients. Of the STEMIs missed, 30% were due to "incorrect measurement points", 36% to non- or borderline-significant STE, 25% to timing, and 9% to inferoposterior location.

#### 2.2 Operationalising "two contiguous leads"

- **Chest leads:** adjacent pairs (V1,V2), (V2,V3), (V3,V4), (V4,V5), (V5,V6). Each lead uses its own threshold: V2 and V3 use the age/sex threshold, all others 1 mm (UDMI's V1/V2 example).
- **Limb leads:** Cabrera order aVL – I – (−aVR) – II – aVF – III, with adjacent pairs (AHA 2009). "ST elevation in −aVR" equals ST depression in aVR. Whether −aVR elevation counts toward STEMI criteria is **not stated** in UDMI 2018 or ESC 2023, so treat it as an implementation choice and document it.
- **Simpler grouping:** UDMI Table 3 groups the leads as (I, aVL), (V1–V6) and (II, III, aVF), "any two leads of a contiguous lead grouping". That is the Q-wave table, but it is commonly reused for ST elevation. It differs from Cabrera adjacency: it allows II+III, which are not adjacent in Cabrera order (II–aVF–III), and it never uses −aVR, so I and II are never linked through it.
- **aVR elevation alone** is not part of the two-contiguous-lead rule. UDMI calls aVR STE "with specific repolarization patterns" a STEMI equivalent.
- **Extended pairs.** Lindow 2026 added the inverted-lead pairs −III/aVL, II/−aVR, −aVR/I, III/−aVL, −V1/−V2 and −V2/−V3 as "extended STEMI criteria". This raised sensitivity for OMI and lowered specificity (numbers in §5). Inverted V1–V3 is a surrogate for posterior leads, which do not exist on a standard 12-lead.

#### 2.3 Exclusions: LVH, LBBB and pacing

The guideline exclusion needs a classifier for LVH, BBB and pacing. Practical options in the literature:

- **Lindow 2026** (full text, PMC13482599):
  - LBBB and ventricular pacing taken from the Glasgow program's statements.
  - LVH = S(V3) + R(aVL) > 2.8 mV in men or > 2.0 mV in women, i.e. Cornell voltage.
  - STEMI criteria evaluated in the subset without LVH, LBBB or pacing (21,972 of 24,511).
  - In the excluded groups they applied modified Sgarbossa (ST/S ≥0.25) and an LVH rule (STE ≥25% of the summed R+S in V1–V3) as "extended" criteria.
- **Lindow 2021** (*Scand Cardiovasc J*, doi:10.1080/14017431.2021.1875138) **[abstract only]**: excluded QRS ≥120 ms and ECG LVH.
- **UDMI and AHA 2009** give concordance criteria for LBBB (≥1 mm concordant STE). For RBBB, UDMI's wording is ambiguous; see §1.1.

#### 2.4 "New" versus unknown baseline

- Every guideline says "new or presumed new". A single-ECG dataset cannot establish "new", so a computed comparator is effectively "**presumed new**", i.e. the criteria are met on this ECG.
- UDMI's footnote allows a delta criterion in V2–V3 (≥1 mm versus a prior ECG) when a prior is available. MIMIC-IV-ECG has repeated ECGs per patient, so this is possible in principle. I am not aware of a published automated implementation.

#### 2.5 Age and sex

The V2–V3 thresholds need age and sex. These defaults matter:

- **MIMIC-IV-ECG.** In the first ~23,000 rows of `machine_measurements.csv` I counted these report lines:
  - "\*\*\* report made without knowing patient's sex or age \*\*\*" (207 times)
  - "… without knowing patient's age …" (84)
  - "… without knowing patient's sex …" (61)
  - "\*\* INTERPRETATION MADE WITHOUT KNOWING PATIENT'S GENDER/AGE \*\*"

  So for an unknown fraction of MIMIC ECGs, the cart applied non-age/sex criteria. This is my own count on a partial download; the full 182 MB file did not download reliably.
- **PTB-XL+.** The paper does not say whether age and sex were supplied when PTB-XL was re-analysed in MUSE with 12SL v243. **Unknown.**
- **Why it matters.** GE reports that providing sex changed 12SL sensitivity for acute inferior and anterior MI in women under 60 (validation doc. p.58). Glasgow states that it "makes extensive use of age and sex".

---

### 3. Open tools

| Tool | What it does for ST/STEMI | Licence | Source |
|---|---|---|---|
| **NeuroKit2** | P/QRS/T delineation (`ecg_delineate`: onsets, offsets, R offsets). **No ST-level or STEMI logic.** A code search for "STEMI" or "J-point" in the repo found nothing. | MIT | https://github.com/neuropsychology/NeuroKit |
| **ECGdeli** (KIT-IBT) | MATLAB delineation (fiducial point tables). Its feature extraction gives amplitudes and intervals. In PTB-XL+ its ST feature is "ST elevation/depression from multiple Gaussian fits" (`STc_X`), not a J-point measurement. Needs MATLAB. | GPL-3.0 | https://github.com/KIT-IBT/ECGdeli |
| **ecg-kit** (Demski/Llamedo) | MATLAB toolbox ("A Matlab toolbox for cardiovascular signal processing"; wavedet-based delineation). **I did not verify any ST or STEMI module.** Last push 2020. | GPL-2.0 | https://github.com/marianux/ecg-kit |
| **ecgpuwave** (PhysioNet) | Onsets, peaks and ends of P, QRS and T, plus T-wave type. The page does not describe ST-level measurement. | GPL per the page's Availability section; the PhysioNet project licence field says ODC-By | https://physionet.org/content/ecgpuwave/1.3.4/ |
| **PTB-XL+** | Precomputed **12SL v243** and **Uni-G R30.4.2** features, ECGdeli features, median beats, and **12SL statements**; details below. | CC BY 4.0 | https://physionet.org/content/ptb-xl-plus/1.0.1/ ; paper https://pmc.ncbi.nlm.nih.gov/articles/PMC10183020/ |
| **Glasgow (Uni-G) program** | Commercial; not open source. Exposed only as features in PTB-XL+. Its statements are **not** in PTB-XL+. | proprietary | Macfarlane 2005 (link in §2.1) |
| GitHub "4th UDMI STEMI" implementations | GitHub repository and code searches found **no established or validated open implementation**, only small unlicensed hobby code. Details below. | — | — |

**PTB-XL+ features relevant to ST** (from `features/feature_description.csv`, which I downloaded):

- `ST_Amp_X`: "ST amplitude at the J-point in lead X". Uni-G `ILM_ST_Amp_X`, 12SL `STJ_X`.
- `ST_Amp80ms_X`: J+80 ms, Uni-G only.
- `ST_Amp116_X` and `ST_Amp18_X`: 12SL `STM_X` and `STE_X`.
- `ST_Slope_X`, `ST_AmpAdj_X`, `LVH_Strain_Global`: Uni-G.

**The GitHub hobby example.** `drshailesh88/ecg/src/core/algorithms/stemi.py` has no licence and 0 stars. It is a cautionary example of how easy the thresholds are to get wrong:

- It applies **2 mm to V1, V4, V5 and V6**, contradicting UDMI's ≥1 mm.
- It defaults sex to male.
- It treats lead pairs as {I, aVL}, {II, III, aVF} and adjacent V-pairs, ignoring −aVR.

**Bottom line:** no open, validated, signal-to-STEMI-criteria implementation exists. You would build one on top of a delineator, or use the commercial J-point measurements in PTB-XL+.

---

### 4. Machine statements by vendor

#### GE Marquette 12SL

**Statements.** The PTB-XL+ mapping file `labels/mapping/12slv23ToSNOMED.csv` lists:

- statement **821, acronym STEMI, full text "\*\* \*\* ACUTE MI / STEMI \*\* \*\*"**, mapped to SNOMED "Acute ST segment elevation myocardial infarction"
- 830 **AC** ", possibly acute" (a qualifier on infarct statements, e.g. `ASMI;AC`)
- 806 **CRVI** "Consider right ventricular involvement in acute inferior infarct"
- 963–967 "ST elevation, consider [inferior/anterior/lateral/anterolateral/inferolateral] injury or acute infarct"
- 930–962 "[region] injury pattern"
- 902/903 early repolarization and pericarditis statements, and 901 "Acute pericarditis"
- 1024 "ST depression, consider subendocardial injury"

**Counts in PTB-XL+.** These are my counts on the full `labels/12sl_statements.csv` (21,799 ECGs):

- STEMI: 178
- AC: 128
- CRVI: 74
- IIOHAI: 20
- AIOHAI: 16
- LIOHAI: 4
- SERYR1: 10
- PCARD: 2

The PTB-XL ECGs are not an acute-care cohort, so these are mostly not true STEMIs and need adjudication.

**The algorithm, per GE's validation document** (416791-003 Rev B, https://www.numed.co.uk/documents/download/216):

- 12SL "was modified to recognize earlier forms of STEMI, using reciprocal depression as the primary discriminating characteristic to discern STEMI versus early repolarization."
- GE's resting-ECG versions include "gender and age-specific criteria for the recognition of STEMI" and right-ventricular-involvement logic.
- The V4R threshold is 100 µV, reduced to 50 µV with acute inferior STEMI plus high-degree AV block plus STE III > II.
- Version 14 of 12SL runs in third-party prehospital defibrillators (Medtronic Physio-Control, Zoll).
- **The exact 12SL STEMI thresholds per lead, age and sex are in the 12SL *Physician's Guide* (2056246-002C), which I could not retrieve.** I do not report them.

**GE patent US6507753B1** (Xue, Reddy, Taha, Murray; assignee GE Marquette; https://patents.google.com/patent/US6507753B1/en) describes one embodiment:

- For females under 60, "the ST segment threshold is decreased by 20%".
- Acute inferior MI requires ST in ≥2 inferior leads above a threshold **and** reciprocal-lead ST below a second threshold.

This is a patent embodiment, not confirmed shipped logic.

#### Philips DXL

- The PageWriter TC10 datasheet (https://www.documents.philips.com/assets/20170818/d599c04944f443e6999ca7d300f3c0f7.pdf) lists "Age and gender criteria", "Based upon 2009 AHA/ACCF/HRS Recommendations, Part VI".
- It also lists "STEMI-CA (Culprit Artery): Criteria that suggest any of four probable sites of the occluded coronary artery".
- **I did not obtain the DXL physician's guide**, so the exact statement strings and thresholds are unverified.

#### Glasgow / Uni-G

- Uni-G is the **University of Glasgow ECG Analysis Program**, not "University General" (PTB-XL+ page; Macfarlane 2005).
- Its STEMI criteria were modified from the ACC/ESC criteria to be age- and sex-dependent. Macfarlane et al., *J Electrocardiol* 2004;37 Suppl:98–103, doi:10.1016/j.jelectrocard.2004.08.032 **[abstract only]**. In a 1,220-ECG test set, sensitivity went from 41.5% to 46.7% and specificity from 96.0% to 98.5% versus the old ACC/ESC criteria. The reference was AMI by "conventional clinical criteria".
- The exact thresholds are not in the abstract.
- The Glasgow program is also embedded in some prehospital monitors. Lindow 2026 describes the LIFEPAK 15 software in Bosson 2017 as the Glasgow program; I did not verify this against Physio-Control documents.

#### Mortara VERITAS

- Its physician's guide was not retrieved. Product literature mentions sex-specific criteria. **Nothing verified.**

#### Which vendors appear in which dataset

- **PTB-XL+** contains **12SL statements, 12SL measurements (STJ, STM, STE per lead) and Uni-G measurements (ST at J and J+80 per lead)**. It does not contain Uni-G, Philips or Mortara statements.
- **MIMIC-IV-ECG v1.0** (https://physionet.org/content/mimic-iv-ecg/1.0/; ODbL; open access):
  - `machine_measurements.csv` has free-text machine report lines `report_0..report_17`, plus `bandwidth` and `filtering`. Its only measurements are **global** ones: `rr_interval`, `p_onset`, `p_end`, `qrs_onset`, `qrs_end`, `t_end` and the P, QRS and T axes.
  - **There are no per-lead ST amplitudes.** The page says "Machine measurements for individual leads may be released in a future version".
  - The carts were "Burdick/Spacelabs, Philips, and General Electric". `cart_id` is de-identified and **no vendor column is given**, so statement wording is mixed.
  - Cardiologist reports are linkable via `waveform_note_links.csv` to MIMIC-IV-Note (credentialed).
  - In my ~23,000-row sample, acute-MI-type statements included "\*\*\* CONSIDER ACUTE ST ELEVATION MI \*\*\*" (277), "[Inferior/Lateral/Anteroseptal/Anterolateral] ST elevation, CONSIDER ACUTE INFARCT", "\*\*\* [region] INFARCT - POSSIBLY ACUTE \*\*\*", "Extensive ST-T changes suggest myocardial injury/ischemia" and "ST elevation suggests acute pericarditis".
  - The GE-style "ACUTE MI / STEMI" string did not appear in that sample. I did not attribute strings to vendors.

---

### 5. Accuracy of computerized STEMI interpretation, and of STEMI criteria

Sens = sensitivity, spec = specificity, PPV = positive predictive value.

| Study | Setting / algorithm | Reference standard | Result | Access |
|---|---|---|---|---|
| Kudenchuk 1991, *JACC* 17:1486 (MITI), doi:10.1016/0735-1097(91)90636-n | Prehospital, n=1,189; computer-interpreted ECG (12SL per GE doc) | AMI (enzymes) | Computer flagged 52% of 391 AMIs vs 66% by electrocardiographer; excluded 98% of non-MI vs 95%; PPV 94% vs 86%; NPV 81% vs 85% | abstract only |
| GE 12SL validation doc (re-analysis of MITI) | same | Enzymes **and** ST elevation | STEMI sens 71%, spec 98.5%, PPV 94% | vendor doc, full text |
| Massel 2000, *Am Heart J*, doi:10.1067/mhj.2000.108240 | 75 CCU-selected ECGs, 3 cardiologists × 2 reads vs 12SL | Cardiologist consensus | 12SL sens 61.5%, spec 100%; inter-rater κ 0.89 (interpretive) vs 0.78 (measured ≥1 mm criteria); strict measured criteria → ~15% overuse of thrombolysis | abstract only |
| Clark 2010, *Am J Cardiol*, doi:10.1016/j.amjcard.2010.07.047 | 1,000 prehospital ECGs, Denmark; LIFEPAK 12 algorithm vs Glasgow vs attending cardiologists | Hospital discharge diagnosis | Sens/spec/PPV for a STEMI report: LP12 78/91/81%; Glasgow 78/94/87%; cardiologists 85/90/81% | abstract only |
| Bhalla 2013, *Prehosp Emerg Care*, doi:10.3109/10903127.2012.722176 | LIFEPAK 12 "acute MI suspected"; 100 STEMI activations vs 100 controls | ED STEMI diagnosis plus cath-lab activation | Sens 58%, spec 100% | abstract only |
| Garvey 2016, *J Electrocardiol*, PMC5613667 | 500 prehospital ECGs; 3 blinded proprietary algorithms run by an industry partner (a co-author is from Philips' Advanced Algorithm Research Center) | **Culprit artery at catheterization** | Sens 0.69 / 0.68 / 0.62; spec 0.89 / 0.91 / 0.95; AUC 0.78–0.79 | full text |
| Bosson 2017, *Prehosp Emerg Care*, doi:10.1080/10903127.2016.1247200 | 44,611 LA Fire Dept ECGs, LIFEPAK 15 software | Regional registry; 3 blinded cardiologists where needed | Sens 92.8%, spec 98.7%; 482 TP vs 711 FP, so PPV ≈ 40% by my arithmetic (not stated in the abstract). FP causes: artifact 20%, early repolarization 16%, peri/myocarditis 13%, LVH 8%, RBBB 5%. FN causes: borderline STE under threshold 40%, tall T reducing ST/T ratio 15%. | abstract only |
| Hillinger 2019, *Int J Cardiol*, doi:10.1016/j.ijcard.2019.04.041 | 2,486 ED patients; **automated application of guideline STEMI criteria** | Adjudicated final STEMI diagnosis | Sens 35%, PPV 54%, NPV 97.8% | abstract only |
| Lindow 2021, *Scand Cardiovasc J*, doi:10.1080/14017431.2021.1875138 | 19,932 ED chest-pain patients; conventional vs extended criteria | AMI with occluded/near-occluded artery | Conventional sens 17%, spec 98%, PPV 12%; extended 30/94/8%; adding reciprocal ST depression raised PPV to 24% / 23% | abstract only |
| Lindow 2026, *JACEP Open*, PMC13482599 | 24,511 ED chest pain (ESC-TROP); STEMI criteria computed from **Glasgow v30.4.3 automated measurements** (no manual reads) | OMI (angiographic TIMI 0–1, or culprit + hs-TnT ≥1000 ng/L, etc.) | STEMI criteria sens 23%, spec 98%, PPV 17%; Glasgow statements sens 32%, spec 98%, PPV 26%; extended criteria 41/95/14%; QoH AI 52/99/51%. In the subset without LVH/LBBB/pacing: STEMI criteria sens 26%, spec 98%. | full text |
| Meyers 2021, *IJC Heart Vasc*, PMC8065286 | 808 patients, case-control; **manual** STEMI criteria (UDMI, QRS onset → J) by 2 interpreters | OMI (TIMI 0–2 culprit, or TIMI 3 + high troponin) | STEMI criteria sens 41%, spec 94% (interpreter 1); 36% / 91% (interpreter 2, n=250) | full text |
| Herman 2024, *EHJ Digit Health*, PMC10944682 | 3,254 ECGs, international test set | OMI ("acutely occluded or flow-limiting culprit artery requiring emergent revascularization") | STEMI criteria sens 32.5%, spec 97.7%; AI 80.6% / 93.7%; experts 73.0% / 95.7% | abstract plus partial full text |
| de Alencar 2024 meta-analysis, *Int J Cardiol*, doi:10.1016/j.ijcard.2024.131889 | 3 studies, 23,704 participants | Acute coronary occlusion | Pooled STE sens 43.6%, spec 96.5% | abstract only |
| Meyers 2025, *EHJ ACVC*, doi:10.1093/ehjacc/zuaf037 | 53 TIMI-0 LAD occlusions | Angiography | 38% never met STEMI criteria on any pre-angiography ECG | abstract only |

**Reviews (no new data)**

- Schläpfer & Wellens 2017, *JACC*, doi:10.1016/j.jacc.2017.07.723 **[abstract only]**: limitations of computer interpretation persist; over-reading by an experienced reader is essential.
- McLaren et al. 2024, *Acad Emerg Med*, doi:10.1111/acem.14795, on Code-STEMI patients whose first ECG the computer labelled "normal". **No abstract was available; I could not see its results.**
- I did not find a 2019 *Ann Emerg Med* paper by Smith matching the brief's description. The closest relevant works are McLaren 2024 above and Karim 2025, *J Pers Med*, PMC12028524 **[abstract only]**: 42 OMI patients whose ECGs the conventional algorithm read as "normal"; the AI flagged 81% as OMI.

#### Inter-observer agreement on STEMI

- **McCabe 2013**, *JAHA*, PMC3835230 **[abstract only]**: 124 physicians read 36 putative-STEMI ECGs, judged against emergent angiography. κ = 0.33 ("poor"); sensitivity 65%, specificity 79%. No difference by specialty after adjusting for experience.
- **Jayroe 2009**, *Am J Cardiol*, doi:10.1016/j.amjcard.2008.09.082 **[abstract only]**: 15 experienced cardiologists read 116 STE ECGs, of which 8 were STEMI. They recommended PPCI in 7.8%–33% of ECGs. Per-reader sensitivity was 50–100% (mean 75%) and specificity 73–97% (mean 85%).
- **Massel 2000** (above): κ 0.78 for measured ≥1 mm criteria among 3 cardiologists. **Massel 2003**, *J Thromb Thrombolysis* **[abstract only]**: overall κ 70.4% across 9 clinicians; showing a computer interpretation biased trainees.
- **Eskola 2005**: cardiologist inter-observer κ 0.94 / 0.93 for ST deviation ≥0.2 mV in V2 / V3, which is high for a pure *measurement* task.
- **Meyers 2021**: 94% absolute agreement between its two interpreters. The paper cites the STEMI criteria's "notoriously poor interrater reliability".

---

### 6. Recommended way to compute a STEMI-criteria comparator (synthesis — my recommendation, not a guideline)

**The goal:** a reproducible, documented "STEMI(+) on this ECG" flag to set beside an OMI model. Here are three options, then a recommendation.

#### (a) Re-implement 4th-UDMI thresholds on delineated J-points

**Inputs per ECG:**

- per-lead ST amplitude at J relative to QRS onset
- age and sex
- LVH, BBB and paced flags
- QRS duration

**Rule:**

- Lead-specific threshold: V2 and V3 use the age/sex rule (≥2.0 mm men ≥40, ≥2.5 mm men <40, ≥1.5 mm women); every other lead ≥1.0 mm.
- Positive if ≥2 *adjacent* leads exceed their thresholds.
- Adjacency: chest V1…V6, and limb leads in Cabrera order aVL–I–(−aVR)–II–aVF–III. State whether −aVR counts.
- Report a variant using the UDMI Table 3 grouping as a sensitivity analysis.

**Practical source of measurements:**

- **PTB-XL+**: use the 12SL `STJ_X` and/or Uni-G `ILM_ST_Amp_X` (both J-point relative to QRS onset, from median beats). This is close to Lindow 2026's design, which used Glasgow measurements.
- **Other data, including MIMIC**, where no per-lead ST is released: run a delineator (NeuroKit2 or ECGdeli) on a median beat, take the global QRS onset and offset, and measure per-lead amplitude at the offset minus the amplitude at onset.
- **Validate your measurements against the 12SL or Uni-G STJ values in PTB-XL+** before trusting them.

**Pros:**

- Transparent, versionable and deterministic.
- Applies identically to every dataset.
- Matches the guideline text.
- Lets you report STEMI(+) with and without the LVH/BBB exclusions.

**Cons and tradeoffs:**

- **Age and sex are required** for V2–V3. PTB-XL and MIMIC both carry age and sex in metadata. Without them the label is undefined: defaulting to "male ≥40" is the most conservative in V2–V3 for women (1.5 → 2.0 mm), so it understates sensitivity for women.
- **The LVH/BBB exclusion needs its own classifier.** Use machine statements (12SL in PTB-XL+, the report text in MIMIC) or explicit criteria such as QRS ≥120 ms and Cornell voltage (Lindow 2026). Report results both on the eligible subset and on all ECGs (excluded = STEMI-negative), since both conventions exist.
- **"New" is unknowable** from one ECG. Label it "criteria met (presumed new)". Optionally implement the V2–V3 delta when a prior ECG from the same patient exists.
- **Posterior and right-sided leads are not on a standard 12-lead.** V7–V9 and V3R/V4R criteria cannot be applied. ST depression in V1–V3 or inverted-lead pairs (Lindow's −V1/−V2, −V2/−V3) are only surrogates; put them in an "extended" variant, not the main comparator.
- **Reciprocal depression** is not part of the UDMI STEMI threshold rule. Requiring it raises PPV (Lindow 2021; 12SL uses it as its primary discriminator) but changes the comparator. Keep it as a secondary variant.
- **Measurement noise near the threshold.** Automated and manual ST amplitudes differ systematically (Eskola 2005; Pelter 1997), and Hillinger attributes 30% of misses to measurement points. Report how many ECGs fall within ±0.05 mV of any threshold, and consider a sensitivity analysis that shifts thresholds by ±0.05 mV.
- **J-point placement drives everything.** Use the J-point, not J+60/J+80, for the guideline comparator.

#### (b) Use 12SL or other machine statements

- **PTB-XL+:** STEMI = statement 821 "ACUTE MI / STEMI". Optionally widen it to AC-qualified infarct statements and the "ST elevation, consider … injury or acute infarct" family.
- **MIMIC:** use a string-matched set such as "CONSIDER ACUTE ST ELEVATION MI" and "… ST elevation, CONSIDER ACUTE INFARCT". Build and publish an explicit regex list, because the vendors are mixed.

**Pros:**

- Zero implementation.
- It is literally what clinicians and paramedics see.
- It has the most published accuracy data (table in §5).
- It already includes vendor exclusions and logic: reciprocity, age/sex, early-repolarization and pericarditis handling.

**Cons:**

- It is *not* the guideline STEMI criteria. 12SL is deliberately specificity-tuned: sensitivities in §5 range from 32% to 71% depending on the reference standard.
- The logic is proprietary, version-dependent (PTB-XL+ used 12SL v243) and not fully documented publicly; I could not obtain the Physician's Guide.
- In MIMIC, vendor and version are unknown per ECG, and some reports were made **without age or sex**.
- No per-lead measurements exist in MIMIC to audit a statement.

Use it as a **second comparator** ("commercial algorithm"), as Lindow 2026 did with its "Computer statement", not as *the* STEMI-criteria comparator.

#### (c) Cardiologist read

**Pros:**

- Closest to clinical practice.
- Can use clinical judgment: reciprocity, morphology, mimics.

**Cons:**

- Poor and variable agreement (κ 0.33 in McCabe; PPCI recommendation rates of 8–33% in Jayroe).
- Expensive.
- A "measured criteria" read and an "interpretive" read give different answers (Massel 2000).
- Readers must be blinded to outcome and given age and sex (Meyers 2021 protocol).
- Manual and computer amplitudes should not be mixed.

It is feasible only for a test subset. It is useful to adjudicate threshold-borderline cases, or to estimate the comparator's own reliability (two readers, κ).

#### Recommendation

- **Primary comparator:** option (a), computed from J-point amplitudes relative to QRS onset, with age/sex-specific V2–V3 thresholds and Cabrera adjacency. Report it two ways:
  - (i) on all ECGs, with LVH/BBB/paced ECGs counted as criteria-negative
  - (ii) on the guideline-eligible subset only

  On PTB-XL+, use the vendor STJ measurements. Elsewhere, use your own delineation, validated against them.
- **Secondary comparator:** option (b), the machine statement (12SL "ACUTE MI / STEMI" in PTB-XL+; a published regex list in MIMIC).
- **Optional extended variant:** inverted-lead pairs, Sgarbossa for LBBB/pacing, and an LVH rule (Lindow 2026).
- **Audit:** a blinded two-reader manual read on a stratified subset (option c), to quantify measurement disagreement near thresholds.
- **Labels:** keep the OMI reference standard (angiography/troponin) separate from all of the above. STEMI criteria are an ECG test, not an outcome.

---

### 7. Open uncertainties and things I could not verify

- **Exact 12SL STEMI thresholds** (Physician's Guide 2056246-002C) and Philips DXL, Mortara VERITAS and Glasgow STEMI rule details. Only abstracts and vendor summaries were seen.
- **ESC 2023 Supplementary Figure S2** (occlusion ECG patterns) and the **2022 ACC chest-pain ECDP (Kontos)** list of "STEMI equivalents": not read.
- **Whether −aVR elevation counts toward "two contiguous leads"**: not stated in UDMI 2018 or ESC 2023.
- **Whether PTB-XL+ 12SL processing received age and sex**: not stated.
- **Full MIMIC-IV-ECG statement frequencies**: my counts come from the first ~23k of ~800k rows, because the download was unstable.
- Several accuracy studies (Kudenchuk, Massel, Clark, Bhalla, Bosson, Hillinger, McCabe, Jayroe, Eskola, Pelter, Macfarlane 2004, Lindow 2021, de Alencar 2024) were **abstract-only** for me. Their reference standards and numbers are as stated in the abstracts.
- Third-party mirrors were used for AHA 2009 Part VI (JACC version) and the 2025 ACC/AHA guideline. The content matched the citation metadata but should be checked against the publisher versions.
