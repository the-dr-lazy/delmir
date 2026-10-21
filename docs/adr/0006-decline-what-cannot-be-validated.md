# DELMIR declines ECGs it cannot validate a reading on, instead of reading them with a caveat

Every ECG gets one of three readings: read, caveated read, or declined. A declined ECG shows only its decline reasons, never a P(OMI) or culprit vessel, and the phone has no override. A category is declined when it changes how OMI shows on the ECG or when too few labelled examples exist to validate a reading on it. Complete LBBB, ventricular pacing, sustained ventricular rhythms, WPW, a detected lead reversal, non-standard lead placement and a missing or unreadable lead all decline. Queen of Hearts and Al-Zaiti et al. read LBBB and paced ECGs, and DELMIR could have done the same with a caveat. That was declined: neither model validates well there (Queen of Hearts reaches about 57% sensitivity in LBBB), and a number shown on an ECG the model was never validated on still anchors the reader.

## Consequences

- The reading population is the training and evaluation population. Declined categories leave the OMI classifier's training, validation and test sets and train the intended-use screen instead; caveated categories stay in and get subgroup metrics. Under-18s are excluded from the data even though the app does not check age.
- A declined ECG can still be saved as a case, so DELMIR's own LBBB and paced cases accumulate as evidence. A category moves from declined to caveated read only through a recorded decision backed by its own test-set metrics with confidence intervals.
- LBBB and paced decline reasons point to Smith-modified Sgarbossa applied by hand.
