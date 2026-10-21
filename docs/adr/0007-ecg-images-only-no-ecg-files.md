# DELMIR reads ECG images only, never ECG files

DELMIR takes an ECG as an image (a photo taken in the app, or a JPEG, PNG or PDF page shared to it or picked from the phone) and recovers its signal with the digitizer; it imports no ECG files (WFDB, DICOM-ECG, HL7 aECG, SCP-ECG, GE MUSE XML, Philips XML, MFER, CSV). The only ECGs the owner meets are paper printouts, and no maintained ECG-file parser runs in React Native, so each format would be a parser written and tested with no real input to test it against. Every PDF, even one whose traces are vector paths that could be read geometrically, is an image and goes through the digitizer.

## Consequences

- The digitizer is the only producer of the 12-lead signal on the phone, and golden fixtures reach the phone in the signal contract's own form, converted from WFDB at build time rather than parsed in the app.
- Nothing about the patient is read from the ECG: age and sex are entered by hand.
- If ECG files are ever imported, the rules are already settled in [Which digital ECG file formats does DELMIR import?](https://github.com/the-dr-lazy/delmir/issues/7): the 10 s rhythm data only, never the cart's interpretation, measurements or median beats; no demographics; leads mapped by name, missing limb leads derived, extra leads ignored; one ECG per import.
