# Case exports carry the patient's identifiers, not a de-identified copy

A case export carries everything the case registry holds: each patient's record number, real dates and times, free-text notes and the ECG image as captured, with the printed header that names the patient. The admin needs the record number to find and correct follow-up on the training side, and the phone's own copy of a case is no less identifiable. A pseudonymous export (random IDs only, times shifted per patient, images cropped below the printed header) was considered and declined by the owner: it would have made exports safe to share, but it costs the link back to the hospital record and the original images that a better digitizer may read later.

## Consequences

- Every case export is identifiable patient data. It is protected in transit and at rest like the case registry itself, and never enters the repo, Cachix, telemetry, MLflow artifacts or a research branch.
- The record number is never a model input or a split key: splits use the case registry's own random patient IDs.
- The record number is part of the case contract in `contracts/`, so the generated Python models carry it too.
