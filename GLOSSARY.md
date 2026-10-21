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

### Anatomy

**Culprit vessel**:
The coronary artery system (LAD, LCx or RCA) containing the lesion that caused an OMI, with each branch counted as the system that supplies it in that patient. Exists only for an OMI.
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
A label inferred by rule from a different concept than the one it stands for, such as a culprit vessel inferred from an infarct territory. Always marked as a proxy, and superseded by an angiography-confirmed label when one exists.
_Avoid_: weak label, silver label

**Angiography-confirmed label**:
A label taken from the patient's coronary angiography and troponin course: the reference standard that proxy labels stand in for.
_Avoid_: real label, ground truth

**Prior ECG**:
An earlier ECG of the same patient, available for comparison with the current one.

**Blog test set**:
Cases from Dr. Smith's ECG Blog, hand-labelled from the follow-up each post reports, used only to test DELMIR and never to train it.
_Avoid_: blog dataset, validation set

### Cases

**Case**:
One ECG of one patient saved in DELMIR, together with the model's outputs for it and its follow-up.
_Avoid_: record, study, encounter

**Follow-up**:
The angiography and troponin findings added to a case after its ECG, such as the culprit vessel, TIMI flow, lesion location and peak troponin.
_Avoid_: outcome, result

**Case registry**:
The saved cases on the phone, and the source of DELMIR's own angiography-confirmed labels.
_Avoid_: database, dataset

**Case export**:
A file of cases deliberately saved out of the case registry; the only way cases leave the phone.
_Avoid_: backup, sync, dump

**Admin**:
A DELMIR user allowed to save cases, add follow-up and make case exports. For now, the only user.
_Avoid_: owner, superuser
