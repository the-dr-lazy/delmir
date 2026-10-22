# DELMIR

DELMIR reads one 12-lead ECG from an adult with suspected ACS and reports whether it shows an OMI and, if it does, the culprit vessel.

## Language

### Diagnoses

**OMI**:
An acute myocardial infarction caused by an acute coronary occlusion or near-occlusion with insufficient collateral flow, whether or not the ECG meets STEMI criteria.
_Avoid_: STEMI, ACO-MI

**NOMI**:
An acute myocardial infarction without an acute coronary occlusion. One kind of Not-OMI, never the name of the whole negative class.
_Avoid_: NSTEMI

**Not-OMI**:
Any ECG without an OMI: a NOMI, no infarction at all, or an OMI mimic.
_Avoid_: NOMI, negative, normal

**STEMI criteria**:
The millimetre ST-elevation thresholds of the Fourth Universal Definition of Myocardial Infarction. A comparator for DELMIR, never a label it learns.
_Avoid_: STEMI (as a label)

**STEMI-negative OMI**:
An OMI whose ECG does not meet STEMI criteria.
_Avoid_: occult OMI, NSTEMI-OMI

**Reperfused OMI**:
An OMI whose culprit lesion had reopened to TIMI 2 or 3 flow by angiography, recognised by a very high troponin or a new regional wall-motion abnormality.
_Avoid_: transient OMI, open-artery OMI

**OMI mimic**:
A Not-OMI ECG whose findings resemble an OMI, such as LVH with strain, early repolarization, pericarditis or hyperkalaemia. Read like any other ECG, never declined.
_Avoid_: false positive, pseudo-STEMI

### Readings

**Intended use**:
One 12-lead ECG, recorded with standard lead placement, from an adult with suspected ACS: the population DELMIR's readings are meant for and validated on.
_Avoid_: indication, scope

**Reading**:
What DELMIR reports for one ECG: its P(OMI), culprit vessel and caveats when it reads the ECG, or only the decline reasons for a declined ECG.
_Avoid_: result, prediction, output

**Caveat**:
A named reason a reading is less reliable, shown alongside its P(OMI).
_Avoid_: warning, flag

**Declined ECG**:
An ECG outside DELMIR's intended use, whose reading gives decline reasons and never a P(OMI) or culprit vessel.
_Avoid_: rejected, invalid, unreadable ECG

**Intended-use screen**:
The check before the classifier that finds what a tracing shows outside DELMIR's intended use and returns its decline reasons and caveats.
_Avoid_: gate, filter, quality check

### Anatomy

**Culprit lesion**:
The lesion angiography identifies as the cause of an OMI, whatever its mechanism (plaque rupture, dissection, embolus), including one already reperfused.
_Avoid_: culprit, target lesion

**Culprit vessel**:
The coronary artery system (LAD, LCx or RCA) that a single culprit lesion lies in, with each branch counted as the system it arises from in that patient: diagonals in the LAD, the ramus and obtuse marginals in the LCx, RV branches in the RCA, and the PDA and posterolateral branches in whichever artery gives rise to them. Exists only for an OMI whose culprit lesions all lie in one native system beyond the left main; a left main or graft culprit, culprits in more than one system, or an unnamed culprit has none.
_Avoid_: culprit artery, infarct territory

**Infarct territory**:
The region of myocardium an ECG localises an infarct to, such as anterior, inferior, lateral or posterior. Says where, not which artery.
_Avoid_: culprit, vessel

### Inputs

**ECG image**:
A picture of an ECG, such as a phone photo, a scan, a PDF or a screenshot, whose signal has to be recovered by digitizing it.
_Avoid_: printout, ECG photo (for any picture)

**ECG file**:
A file that stores an ECG's sample values in machine-readable form, such as WFDB, DICOM-ECG or a vendor XML. A PDF is never an ECG file, even when its traces are vector paths.
_Avoid_: digital ECG, ECG export

### Labels and data

**Proxy label**:
A label inferred by rule from a different concept than the one it stands for, such as a culprit vessel inferred from an infarct territory. Always marked as a proxy, and superseded by an angiography-confirmed or clinical label when one exists.
_Avoid_: weak label, silver label

**Angiography-confirmed label**:
A label decided by the culprit finding of the patient's coronary angiography, with the troponin course where the culprit's flow alone does not decide: the reference standard that proxy labels stand in for.
_Avoid_: real label, ground truth

**Clinical label**:
A label decided without an angiographic culprit finding, from the troponin course, regional wall motion and the final diagnosis, such as a Not-OMI from a troponin rule-out.
_Avoid_: troponin label, soft label

**Undetermined**:
What a case's label is when its follow-up cannot decide between OMI and Not-OMI; such a case is left out of training and evaluation, never counted as Not-OMI.
_Avoid_: unknown, Indeterminate (a call, not a label), excluded

**Very high troponin**:
A peak troponin at or above the level that marks an infarct large enough to be an OMI for its assay: 1.0 ng/mL for conventional cTnT, 10 ng/mL for conventional cTnI, 1000 ng/L for hs-cTnT and 5000 ng/L for hs-cTnI. A qualitative troponin test never shows one.
_Avoid_: high troponin, large troponin leak

**Prior ECG**:
An earlier ECG of the same patient, available for comparison with the current one.

**Blog test set**:
The blog cases of Dr. Smith's ECG Blog, used only to test DELMIR and never to train, tune or calibrate it.
_Avoid_: blog dataset, validation set

**Blog case**:
One ECG image from a post on Dr. Smith's ECG Blog, labelled from the follow-up facts the post reports, never from the authors' reading of the ECG. Not a case: it is never saved in the case registry.
_Avoid_: blog post (a post can hold several patients and many ECGs), blog record

**Index ECG**:
The earliest ECG of an episode that carries the episode's label: the one ECG counted when each episode is counted once.
_Avoid_: presenting ECG, first ECG, quiz ECG

### Cases

**Case**:
One ECG image of one patient saved in DELMIR, with the reading it got when it was saved; it belongs to an episode and shares that episode's follow-up.
_Avoid_: record, study, encounter

**Episode**:
One presentation of a patient with suspected ACS, from symptom onset to discharge. Its follow-up gives the label of the episode's ECGs recorded before angiography, never of those recorded after it.
_Avoid_: encounter, admission, event

**Follow-up**:
The angiography, troponin and imaging findings of the episode a case's ECG belongs to, such as the culprit lesions, their TIMI flow, peak troponin, regional wall motion and the final diagnosis.
_Avoid_: outcome, result

**Case registry**:
The saved cases on the phone, and the source of DELMIR's own angiography-confirmed labels.
_Avoid_: database, dataset

**Case export**:
A file of cases deliberately saved out of the case registry, carrying everything the registry holds about them, record numbers and ECG images included; the only way cases leave the phone.
_Avoid_: backup, sync, dump

**Record number**:
The hospital's identifier for a patient, typed in by the admin so the follow-up can be found later; the only identifier DELMIR stores apart from what an ECG image shows.
_Avoid_: MRN, patient ID, file number

**Cardiac history**:
Whether a patient had a prior MI, a prior PCI or a prior CABG, as known at an episode.
_Avoid_: risk factors, comorbidities

**Admin**:
A DELMIR user allowed to save cases, add follow-up and make case exports. For now, the only user.
_Avoid_: owner, superuser

### Presenting a reading

**P(OMI)**:
The model's calibrated probability that an ECG shows an OMI.
_Avoid_: score, risk, OMI likelihood

**Call**:
The verdict DELMIR gives for an ECG it reads, set by where its P(OMI) falls against a rule-out and a rule-in threshold: OMI, Indeterminate or Not-OMI.
_Avoid_: diagnosis, prediction, classification

**Indeterminate**:
The call for a P(OMI) between the rule-out and rule-in thresholds, where DELMIR claims neither OMI nor Not-OMI.
_Avoid_: borderline, equivocal, grey zone

**Confidence**:
How far to trust one ECG's P(OMI), given as High, Moderate or Low from the model's own uncertainty and the signal quality.
_Avoid_: certainty, confidence interval

**Signal quality**:
How cleanly each lead, and the ECG as a whole, was recorded and digitized.
_Avoid_: image quality, noise level

**Lead attribution**:
How much each lead drove an ECG's P(OMI).
_Avoid_: saliency, heatmap, explanation
