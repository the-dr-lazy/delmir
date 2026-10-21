# Labels follow the OMI paradigm, not STEMI criteria

DELMIR's first output is the probability of an OMI, and every label, model output and evaluation metric is defined in OMI terms (Smith and Meyers). STEMI criteria survive only as a comparator, above all to mark out the STEMI-negative OMIs where DELMIR has to beat them. STEMI labels would have been far easier to get, since they can be computed from the ECG alone, but STEMI criteria miss a large share of occlusions, and training on them would teach the model the very rule it exists to improve on.

## Consequences

An OMI label needs follow-up (angiography and troponin), not just the ECG, so every public dataset yields only proxy labels until the case registry supplies angiography-confirmed ones.
