# Bare React Native on Android, with both stages running on the phone

DELMIR ships as a bare React Native app (no Expo), Android first, and runs the digitizer and the classifier on the phone through native ONNX Runtime. This replaces the original brief's web app on onnxruntime-web: the case registry needs a real on-device database, capture needs native camera and file access, and native ONNX Runtime runs faster on a phone than its browser build. Running the model locally keeps a reading working offline and keeps patient data off servers, even though DELMIR now saves cases and reports telemetry. Expo was declined by preference.

## Consequences

- iOS stays buildable but untested; building it from NixOS needs a Mac or a cloud build service.
- Every native module (ONNX Runtime, camera, SQLite) is wired by hand rather than through Expo config plugins.
