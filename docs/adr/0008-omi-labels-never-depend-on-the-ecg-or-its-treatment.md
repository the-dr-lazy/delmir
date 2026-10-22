# OMI labels never depend on the ECG or the treatment it prompted

An OMI label is decided only by what angiography found (the culprit lesion and its pre-PCI TIMI flow), the troponin course, regional wall motion and the final diagnosis, never by the ECG being labelled or by a decision a clinician took from it. So urgent or emergent PCI, cath-lab activation, a STEMI diagnosis and Meyers' "STEMI-positive ECG with death before angiography" are not routes to OMI, even though Herman 2024's primary label uses urgent PCI and Meyers 2021 uses death before angiography. A label that follows the clinician's reading of the ECG teaches the model to copy that reading, STEMI criteria above all, which is the rule ADR 0001 exists to improve on.

## Consequences

- A case that only those routes could decide is Undetermined, not OMI.
- Urgent PCI may still be recorded as a fact, so a Herman-compatible label can be derived to compare against published results; it never trains a model.
- MIMIC-IV proxy labels built on PCI billing (C9606) count only as evidence of what angiography found, never of the decision to treat.
