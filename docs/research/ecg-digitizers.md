# Open-source ECG digitizers, and whether they can run on a phone

Research for [the-dr-lazy/delmir#14](https://github.com/the-dr-lazy/delmir/issues/14), carried out 2026-10-21. ADR 0007 makes the digitizer the only producer of DELMIR's 12-lead signal: it reads phone photos, scans and PDF pages, vector PDFs included. Nothing here was exported, built or run. Every claim links to its source. **UNVERIFIED** marks what no primary source confirmed. **[calc]** marks numbers derived by arithmetic from primary data.

## Answer

**There is no open digitizer that already runs on a phone. One open digitizer, Ahus-AIM's Open-ECG-Digitizer, works on real phone photos and is small enough to port.**

- **Open-ECG-Digitizer** ([repo](https://github.com/Ahus-AIM/Open-ECG-Digitizer); Stenhede et al., *npj Digit Med* 2026, [arXiv 2510.19590](https://arxiv.org/abs/2510.19590)) is the strongest open candidate.
  - It is a 22.6 M-parameter U-Net (90 MB fp32) with a classical pipeline: perspective correction, grid finding and layout template matching. It handles several layouts: 3×4, 6×2, 12×1 and Cabrera.
  - On real prints from Akershus hospital it reports SNR 19.65 dB from a scanner, 12.19 dB from a OnePlus phone and 10.47 dB from an iPhone.
  - On the Challenge's hidden set it was scored by the organisers zero-shot. It is the only open method with a positive SNR on every real variant there, but phone photos only reach 1–2 dB.
  - Licence: CC BY-SA 4.0 for code and weights.
- **ECG-Digitiser** ([repo](https://github.com/felixkrones/ECG-Digitiser), team SignalSavants, Oxford) won the PhysioNet Challenge 2024 digitization task with 12.15 dB on real scans.
  - It is BSD-2, a 59 M-parameter nnU-Net, and assumes one fixed 3×4 layout at 25 mm/s and 10 mm/mV. It does no grid detection and does not read the calibration pulse.
  - Its SNR is **negative on every phone-photo variant** of the hidden set.
- **The Kaggle rerun** ("PhysioNet – Digitization of ECG Images", 2025-10 to 2026-01) produced much higher scores, about 23 dB (UNVERIFIED leaderboard snippet).
  - The winners are GPU ensembles at 2–5k px, fitted to one fixed ECG-Image-Kit template. They are not phone candidates.
  - The 5th place ([dangnh0611](https://github.com/dangnh0611/kaggle_ecg_digitization)) and the hengck23 baseline are MIT. They are useful as an accuracy ceiling and as design evidence.
- **Everything else is weaker for DELMIR:**
  - [ECGtizer](https://github.com/UMMISCO/ecgtizer) (Unlicense) is tested on clean renders only and has no photo handling.
  - [Paper-ECG](https://github.com/Tereshchenkolab/paper-ecg) is a manual desktop GUI.
  - PMcardio is closed.
  - The other top-5 Challenge teams published no code.
- **pdf2ECG** ([repo](https://github.com/BIVectors/pdf2ECG), GPL-3.0) is not an image digitizer. It recovers **bit-exact** signals from GE MUSE vector PDFs.
  - Under ADR 0007 it has no place in the app.
  - It is valuable as a **ground-truth generator** for the bake-off: take an exact signal from a MUSE PDF, then print and photograph that PDF.

**On the phone.** The U-Nets export to ONNX in principle. They use standard Conv, InstanceNorm, LeakyReLU, bilinear Resize and Concat, but no export was tried. Two things stand in the way.

1. **Compute.** Open-ECG-Digitizer's U-Net costs about 0.7 TMAC at 1500×2100 px [calc], which is seconds to tens of seconds on a phone CPU at fp32. It needs a smaller input, tiling, int8 or an NPU.
2. **The classical steps.** They are written in torch, numpy, SciPy and scikit-image: a custom Hough accumulator, Hungarian matching and connected-component graph merging. They have to be ported to native code. `react-native-fast-opencv` covers some of them, but not `remap` or a raw Hough accumulator.

**Every digitizer recovers only what is printed.** A 3×4 printout gives 2.5 s per lead (plus a 10 s rhythm strip) at the lead's own time offset. Open-ECG-Digitizer returns a 12 × 5000 canvas with NaN outside each lead's window. Only ECGtizer fills to 10 s, with a generative model (ECGrecover). The classifier's input contract has to accept this ([Output length](#output-length-10-s-or-25-s)).

**Bake-off candidates:**

1. Open-ECG-Digitizer (lead candidate).
2. ECG-Digitiser (SignalSavants), as the Challenge-winning baseline.
3. The Kaggle 5th-place solution, as a desktop-only accuracy ceiling.

**Bake-off data:** the real phone-photo subsets of [ECG-Image-Database](https://www.kaggle.com/datasets/physionet/ecg-image-database), plus your own phone photos of printouts with known signals ([Bake-off](#for-the-digitizer-bake-off)).

## The PhysioNet Challenge 2024

### Setup

The George B. Moody PhysioNet Challenge 2024 was "Digitization and Classification of ECG Images" ([challenge page](https://moody-challenge.physionet.org/2024/); [Reyna et al., CinC 2024](https://moody-challenge.physionet.org/2024/papers/cinc_paper.pdf)).

- **Training data.** 21,799 PTB-XL records. Teams rendered images themselves with ECG-Image-Kit and could add PhysioNet 2021 and CODE-15% signals.
- **Hidden data were real paper.** 35,595 images of 1,977 records (PTB-XL and Emory) were "printed, photographed, and/or scanned". The variants are:
  - colour and black-and-white scans;
  - phone photos of clean, stained and deteriorated paper;
  - scans of deteriorated paper;
  - phone photos of a monitor.
- **The official ranking scores only the colour and B&W scans of the PTB-XL prints.** Photos appear only in the per-variant "extended" columns ([results](https://moody-challenge.physionet.org/2024/results/)).
- **Metric.** The authoritative version is the code in [`evaluation-2024`](https://github.com/physionetchallenges/evaluation-2024) (`helper_code.compute_snr`, `evaluate_model.py`).
  - Per-lead SNR is `10·log10(mean(x²) / mean((x − x̂)²))`, averaged over leads and records.
  - Before scoring, the estimate is shifted to the best 2-D cross-correlation match within ±0.5 s and ±1 mV.
  - NaN samples are excluded, and the SNR is multiplied by the fraction of reference samples that were digitized.
  - An all-zeros output scores exactly 0 dB, so many teams cluster near 0.
- **What gets scored.** The organisers' recipe renders with `--mask_unplotted_samples`, which sets the unprinted part of each lead to NaN ([ECG-Image-Kit README](https://github.com/alphanumericslab/ecg-image-kit/blob/main/codes/ecg-image-generator/README.md)).
  - So only each lead's printed 2.5 s window is scored, and it must sit at its correct time offset.
  - UNVERIFIED: whether the real hidden files were masked the same way.

### Official digitization ranking (hidden set, SNR in dB)

From [`official_scores_digitization.tsv`](https://moody-challenge.physionet.org/2024/results/official_scores_digitization.tsv). "Ranked" is the leaderboard score on PTB-XL scans. A dash means the team was not scored on that variant.

| Rank | Team | Ranked (scans) | Colour scan, clean | Phone, clean | Phone, stained | Phone, deteriorated | Phone photo of monitor | Public code |
|---|---|---|---|---|---|---|---|---|
| 1 | SignalSavants (Oxford) | **12.151** | 4.930 | −1.071 | −0.723 | −1.304 | −1.759 | [ECG-Digitiser](https://github.com/felixkrones/ECG-Digitiser), BSD-2 |
| 2 | BAPORLab (Asan / Ulsan) | 5.493 | 6.220 | −0.261 | −1.116 | 0.807 | 0.123 | none found |
| 3 | wavie_ABI (Auckland) | 5.469 | – | – | – | – | – | none found |
| 4 | Ahus AI Lab (Akershus) | 3.047 | 3.318 | 0.138 | −0.345 | 0.792 | −0.512 | 2024 code not public; successor Open-ECG-Digitizer |
| 5 | USST_Med (Shanghai) | 2.202 | −0.058 | −0.375 | −0.375 | −0.375 | −0.375 | none found |
| 6 | mins-eth (ETH Zürich) | 0.893 | – | – | – | – | – | [repo](https://github.com/MINSMoody/ECG_Paper_Digitization_via_Faster_R-CNN_and_U-Net), BSD-2 |
| 7 | Inventec AIC | 0.397 | 4.101 | −4.574 | −5.106 | −3.782 | −2.450 | none found |
| 13 | Revenger | −0.733 | | | | | | [wenh06/cinc2024](https://github.com/wenh06/cinc2024), MIT |

- **The win is on scans only.** Over the 8 extended columns SignalSavants averages 0.57 dB and BAPORLab 1.47 dB (Reyna et al. Table 1; the SignalSavants figure is confirmed [calc]). BAPORLab beats SignalSavants on 7 of 8 extended variants.
- **No Challenge entry did well on phone photos.** No entry exceeds 0.81 dB on any phone-photo variant. The SignalSavants paper notes that "no team received a positive score for mobile phone photos of stained papers" ([CinC2024-097](https://www.cinc.org/archives/2024/pdf/CinC2024-097.pdf)).
- **Commercial comparison.** The organisers also evaluated the commercial PMcardio, which "outperformed the Challenge algorithms". No numbers were published (Reyna et al. §4).
- USST_Med's identical values across variants look like near-constant output (my reading, UNVERIFIED).
- Inventec's own paper claims 5th place, but the official table ranks it 7th.

### The top teams' pipelines

All but SignalSavants and mins-eth come from the [CinC 2024 papers](https://www.cinc.org/archives/2024/) only.

- **SignalSavants**, [CinC2024-097](https://www.cinc.org/archives/2024/pdf/CinC2024-097.pdf), arXiv 2410.14185, repo above.
  1. Deskew: Canny, then `cv2.HoughLines`, rotating by the median near-horizontal angle.
  2. An nnU-Net v2 2D model labels every pixel as background or one of 12 leads (13 classes). The whole page is the input.
  3. Each lead's per-column mean y becomes the signal.
  - **Scale is assumed, not measured.** px/s comes from assuming every short lead spans 2.5 s, and 25 mm/s and 10 mm/mV are fixed. The baseline is a hard-coded fraction of page height per lead (`config.py`).
  - **Model.** `PlainConvUNet`, 9 stages [32…512], InstanceNorm and LeakyReLU, patch 1024×1280; ≈ 59.2 M params [calc from `plans.json`].
  - **Weights.** `checkpoint_final.pth` is 474.9 MB in Git LFS. That is likely including optimizer state; fp32 weights alone would be ≈ 237 MB [calc].
  - **Frameworks.** PyTorch, a vendored nnU-Net fork (Apache-2.0), OpenCV, and TensorFlow for ECG-Image-Kit's handwriting generator.
- **BAPORLab** ([CinC2024-227](https://www.cinc.org/archives/2024/pdf/CinC2024-227.pdf)).
  - Network: an EfficientNet-B0 U-Net with three output channels: waveform, gridline and text.
  - Post-processing is rule-based:
    - skeletonise the waveform;
    - count horizontal grid lines to get the amplitude;
    - scan columns to read the signal.
  - Its extended scores are the best of any Challenge entry. No code.
- **wavie_ABI** ([CinC2024-229](https://www.cinc.org/archives/2024/pdf/CinC2024-229.pdf)).
  - Pipeline: a rotation-regression network, then nnU-Net v2, then YOLOv5s lead boxes snapped to the 3×4 template.
  - Scale is fixed at 0.1 mV and 0.04 s per small square.
  - About 30 s per case. No code.
- **Ahus AI Lab 2024** ([CinC2024-262](https://www.cinc.org/archives/2024/pdf/CinC2024-262.pdf)).
  - Network: a small U-Net with four classes (trace, 1 mV calibration pulse, other print, background).
  - An edge-finder network locates the start and end of each lead.
  - A differentiable softmax column-expectation turns 2-D into 1-D, so the whole thing can be fine-tuned on −SNR.
  - Superseded by Open-ECG-Digitizer.
- **USST_Med** ([CinC2024-134](https://www.cinc.org/archives/2024/pdf/CinC2024-134.pdf)).
  - Network: YOLOv8-tiny finds the lead names to deskew, then a ResUNet with CBAM attention segments the trace.
  - It is the only top-5 entry that **scales amplitude from the calibration pulse**.
  - No code.

None of these entries uses Viterbi or dynamic-programming path finding.

## Open-ECG-Digitizer in detail

- **Papers.** Stenhede, Bjørnstad, Ranjbar, "Digitizing Paper ECGs at Scale: An Open-Source Algorithm for Clinical Research".
  - [arXiv 2510.19590](https://arxiv.org/abs/2510.19590), 2025-10.
  - *npj Digit Med* 2026, doi:10.1038/s41746-025-02327-1 ([PMC12891466](https://pmc.ncbi.nlm.nih.gov/articles/PMC12891466/)).
- **Repo.** [Ahus-AIM/Open-ECG-Digitizer](https://github.com/Ahus-AIM/Open-ECG-Digitizer): v1.9.3, 2026-06-04, about 110 stars.
- **Licence: CC BY-SA 4.0** for code and LFS weights ([LICENSE](https://raw.githubusercontent.com/Ahus-AIM/Open-ECG-Digitizer/main/LICENSE)).
  - It was added only in v1.9.3 ([CHANGELOG](https://github.com/Ahus-AIM/Open-ECG-Digitizer/blob/main/CHANGELOG.md)). The README also asks for a mandatory citation.
  - ShareAlike would carry over to an ONNX conversion or a fine-tune.
  - DELMIR is a personal tool that is not distributed, so the obligations, which attach to sharing, are unlikely to bite. That is my reading, not legal advice.
- **Training data.** A modified ECG-Image-Kit rendered CODE-15% signals in 3×4 + II. The [development dataset](https://huggingface.co/datasets/Ahus-AIM/Open-ECG-Digitizer-Development-Dataset) is Apache-2.0: 8,658 images, about 75 GB.
- **Pipeline** ([`src/model`](https://github.com/Ahus-AIM/Open-ECG-Digitizer/tree/main/src/model), configs in `src/config`):
  1. Resample the image to a 3000 px long side (`resample_size: 3000`).
  2. **Segmentation U-Net**, 3 → 4 classes (trace, grid, background, …).
     - Dims [32, 64, 128, 256, 320×4], depth 2, InstanceNorm2d, LeakyReLU, strided-conv downsampling, bilinear `F.interpolate` upsampling, replicate padding.
     - **22.6 M params**; `weights/unet_weights_07072025.pt` is 90,464,067 B.
  3. **Perspective detector.** A Hough transform written in torch (250 θ, `index_add_` accumulator), corrects up to about 45°.
  4. Crop with `torchvision` perspective.
  5. **Pixel-size finder.** Grid autocorrelation.
  6. **Lead identifier.** Layout templates in YAML ([`lead_layouts_all.yml`](https://github.com/Ahus-AIM/Open-ECG-Digitizer/blob/main/src/config/lead_layouts_all.yml): standard and Cabrera 12×1, 6×1 halves, 3×4 with 0–3 rhythm strips, 6×2 with 0–1, 3×1, 3×2) plus a second **lead-name U-Net** (1 → 13 classes, about 5.8 M params, 23.3 MB), matched with `scipy.optimize.linear_sum_assignment`.
  7. **Signal extractor.** `skimage.measure.label` connected components with line-graph merging.
  - An experimental dewarper exists but is off by default.
- **Output.** A canonical 12 × 5000 array in µV (10 s at 500 Hz). Each 3×4 cell is placed in its own time window, with NaN elsewhere, and a rhythm lead fills the full width ([`lead_identifier.py`](https://github.com/Ahus-AIM/Open-ECG-Digitizer/blob/main/src/model/lead_identifier.py)).
- **Reported accuracy.** The alignment shift may flatter all the numbers.

  | Data | SNR (dB) | Other |
  |---|---|---|
  | Ahus thermal prints (1,596 images, 266 ECGs, 50 mm/s Cabrera), scanner | 19.65 ± 5.20 | RMSE 19.3 µV, r 0.987 |
  | Same, OnePlus phone photo | 12.19 ± 4.65 | RMSE 42.8 µV, r 0.947 |
  | Same, iPhone photo | 10.47 ± 3.94 | RMSE 51.3 µV, r 0.935 |
  | Challenge hidden set, colour scan clean / deteriorated | 7.34 / 1.82 | zero-shot, organiser-scored |
  | Challenge hidden set, B&W scan clean / deteriorated | 7.24 / 1.73 | |
  | Challenge hidden set, phone clean / stained / deteriorated | 1.05 / 2.03 / 1.59 | |
  | Challenge hidden set, monitor photo | 2.11 | |

  Sources: [arXiv 2510.19590 HTML](https://arxiv.org/html/2510.19590v1) and the journal full text.
  - **The gap is large.** The Ahus prints (Ahus's own printers, at 50 mm/s) score about 10 dB above the hidden set's PTB-XL and Emory photos. Expect DELMIR's hospital printouts to land somewhere in that range until measured.
- **Runtime.** 5.88 s per image on an RTX 5090, 16.78 s on an i9-14900KF CPU.

## Kaggle "PhysioNet – Digitization of ECG Images" (2025–26)

- **The competition.** [Competition page](https://www.kaggle.com/competitions/physionet-ecg-image-digitization). The Kaggle pages render with JavaScript, so details come from mirrors such as [StarryBNU/PhysioNet_ECG](https://github.com/StarryBNU/PhysioNet_ECG/blob/main/README.md) (secondary).
  - It reran the 2024 task on fresh data from 2025-10-21 to 2026-01-22.
  - Notebook-only, no internet.
  - **The metric differs from the Challenge.** It allows a 0.2 s shift and sums power over the 12 leads, so its scores are not comparable to the Challenge's.
  - Training variants include an original render, colour and B&W scans, a phone photo of a print, a phone photo of a screen, stained or soaked prints, and mould scans. All use one 3×4 + II template.
- **Leaderboard.** Private top SNR about 23.3 dB (UNVERIFIED: from a search snippet of the leaderboard).
- **1st place.** Ten-model ensemble with ConvNeXtV2, EfficientNetV2 and other backbones at 5056×1280 or 2528×1280. The head is split into the fixed layout's four row groups. Read via a [mirror of the write-up](https://github.com/seshurajup/myclew/blob/main/research/gm/writeups/https-www-kaggle-com-c-physionet-ecg-image-digitization-writeups-1st-place-solution.md).
- **hengck23 baseline.** [Repo](https://github.com/hengck23/kaggle-physionet-ecg-image-digitization), MIT: homography rectification, then grid-point detection.
- **5th place.** [dangnh0611/kaggle_ecg_digitization](https://github.com/dangnh0611/kaggle_ecg_digitization), MIT, private LB 22.63.
  - Rotation net.
  - A 2048² ConvNeXt U-Net detects 2,422 template keypoints.
  - Piecewise homography crops each lead.
  - A column-wise Gaussian-heatmap U-Net reads the trace at 1024².
  - Weights are on Kaggle. Training needs ≥ 45 GB VRAM.
  - **Its [ablations](https://github.com/dangnh0611/kaggle_ecg_digitization/blob/main/docs/ABLATION_STUDY.md) are useful design evidence.** Local piecewise homography beats a global one (22.93 vs 21.55 dB), and a 1024 input beats 512 (23.57 vs 22.90).
- **Relevance.** Everything is tied to one known template and is far too big for a phone. The transferable ideas are mesh rectification from grid keypoints and per-lead column-wise heatmap regression.

## Other digitizers

- **ECGtizer** ([repo](https://github.com/UMMISCO/ecgtizer), Unlicense, active 2026-04; [arXiv 2412.12139](https://arxiv.org/html/2412.12139v1), *Biomed Signal Process Control* 2025).
  - Classical pipeline: OCR text masking, Otsu or Sauvola binarisation, strip finding, calibration pulse.
  - Optional ECGrecover completion extends 2.5 s or 5 s leads to 10 s.
  - Output is HL7 aECG at 12 × 10 s × 500 Hz.
  - Tested only on clean digital renders: PCC 0.954. No perspective or photo handling.
- **Paper-ECG** ([repo](https://github.com/Tereshchenkolab/paper-ecg), MIT). A semi-manual desktop GUI, about 137 s per ECG.
- **ECGMiner** (*Comput Methods Programs Biomed* 2024, doi:10.1016/j.cmpb.2024.108053). Rule-based; PCC 0.97–0.99 on renders. Code location UNVERIFIED.
- **PMcardio** (Powerful Medical; [medRxiv 2024.08.31.24312876](https://www.medrxiv.org/content/10.1101/2024.08.31.24312876), *J Electrocardiol* 2025). Closed.
  - Reports PCC > 0.91 and SNR > 12.5 dB on 6,000 images, with a 6.6 % failure rate.
  - The ECG-Image-Database authors cite it as the only robust option on their Ahus data.
- **On-device digitizers.** No 2023–2026 primary source shows a full 12-lead digitizer running on a phone.

## ECG-Image-Kit and ECG-Image-Database

- **ECG-Image-Kit** ([repo](https://github.com/alphanumericslab/ecg-image-kit), BSD-3, frozen since 2024; Shivashankara et al., *Physiol Meas* 2024, [arXiv 2307.01946](https://arxiv.org/abs/2307.01946)) renders WFDB records into images.
  - **Layouts.** 3×4 (time-shifted 2.5 s columns, the default), 6×2 at 5 s and 12×1 at 10 s, plus an optional 10 s rhythm strip.
  - **Distortions.** Handwritten text, creases, wrinkles, rotation, noise, crop, colour temperature, grid colour and B&W, calibration pulse, header text.
  - **Ground truth.** The WFDB signal (NaN-masked with `--mask_unplotted_samples`). A JSON with per-lead and lead-name bounding boxes, `plotted_pixels` (trace pixel coordinates) and grid spacing ([`template2.json`](https://github.com/alphanumericslab/ecg-image-kit/blob/main/codes/ecg-image-generator/template2.json)).
  - **No physical print model.** The distortions are synthetic only.
  - **A GPL-3.0 sub-folder.** The `codes/ecg-image-digitizer/roi/` YOLOv7 lead detector is GPL-3.0.
  - **Its role.** The standard training generator; every candidate above was trained on its output. For a bake-off it gives controlled ablations, not real photos.
- **ECG-Image-Database** (Reyna et al., [arXiv 2409.16612](https://arxiv.org/abs/2409.16612); journal version *Physiol Meas* 2026, doi:10.1088/1361-6579/ae85b2, [PMC13402943](https://pmc.ncbi.nlm.nih.gov/articles/PMC13402943/)) is the Challenge's hidden data, now public on [Kaggle](https://www.kaggle.com/datasets/physionet/ecg-image-database).
  - **Licence and size.** CC BY-ND 4.0, about 36.4 GB, from 2026-08.
  - **Contents.** 37,191 images of 2,243 records (PTB-XL, Emory, Ahus), all with WFDB signals.
    - Prints were scanned on two scanners and photographed with 8 phones. Some were shot off a monitor, stained, soaked, ironed or moulded.
    - **Layout gap.** PTB-XL and Emory are 3×4 + II at 2.5 s. Ahus is a two-page Cabrera layout at 50 mm/s. Real 6×2 and 12×1 photos are rare or absent.
  - **This is the bake-off's public data:** real phone photos with known signals.

## pdf2ECG

- **Repo and paper.** [BIVectors/pdf2ECG](https://github.com/BIVectors/pdf2ECG), GPL-3.0, 2026-09. The preprint is Abdelrahman, …, Waks, [medRxiv 10.64898/2026.09.23.26362281](https://www.medrxiv.org/content/10.64898/2026.09.23.26362281v1).
- **What it does.**
  - Parses the FlateDecode streams of a **GE MUSE vector PDF**.
  - Inverts the rendering's "double quantization" to recover the integer ADU samples **bit-exactly**.
  - Certifies each reconstruction and flags clipping.
  - Validation: 100 % zero-error on 1,632 PDF–XML pairs (5 layouts × 3 gains).
- **Limits.**
  - MUSE only, 25 mm/s only, gain 5/10/20 mm/mV.
  - Layouts 12×1, 4×3 (2.5 s with 0/1/3 rhythm strips) and 6×2.
  - Only 12×1 is simultaneous across leads.
- **Code.** Python (`load_musepdf.py`, numpy + zlib) or MATLAB, with no model. A port to a phone would be easy, but it would be GPL, and ADR 0007 routes every PDF through the digitizer anyway.
- **Use for DELMIR: ground truth.** Run pdf2ECG offline on MUSE PDFs to get exact signals. Then rasterise the PDF, or print it and photograph it, and score the digitizer against those signals.
  - This covers the 6×2 and 12×1 layouts that ECG-Image-Database lacks.
  - It also exercises ADR 0007's vector-PDF-as-image path.
  - It only helps if MUSE PDFs are at hand (UNVERIFIED for DELMIR's hospital).

## Can it run on the phone?

### ONNX export

Nothing was exported; this is read from the code.

| Part | Exportable? | Notes |
|---|---|---|
| Open-ECG-Digitizer segmentation and lead-name U-Nets | In principle | Conv2d, InstanceNorm2d → `InstanceNormalization`, LeakyReLU, bilinear `Resize` with a size taken from a tensor shape, `padding_mode='replicate'` → `Pad(edge)`. The dynamic resize and the replicate pad need testing. |
| Open-ECG-Digitizer Hough and perspective | Partly traceable | Torch tensor ops, but with data-dependent indexing and quantiles. Easier to rewrite natively. |
| Open-ECG-Digitizer lead identification and signal extraction | No | Hungarian matching, connected-component labelling, template matching, graph merging. Must be ported. |
| ECG-Digitiser nnU-Net | In principle | A plain conv U-Net. But inference runs through the `nnUNetv2_predict` CLI with sliding-window tiling, Gaussian blending and mirror test-time augmentation on by default. That is about 36 forward passes of a 59 M-param net at 1024×1280 per page [calc]. |
| ECG-Digitiser deskew and vectorisation | No | `cv2.HoughLines` plus simple column maths. Trivial to port. |
| Kaggle 5th place | Networks yes, pipeline no | Ensembles at 2048² are not a phone option. |

### ONNX Runtime on Android

- **The package.** `onnxruntime-react-native` pulls the full `onnxruntime-android` AAR. A Gradle flag swaps in the Qualcomm QNN build. It compiles with NNAPI and accepts `"cpu"` and `"xnnpack"` execution providers.
  - Sources: [`build.gradle`](https://github.com/microsoft/onnxruntime/blob/main/js/react_native/android/build.gradle), [`SessionUtils.cpp`](https://github.com/microsoft/onnxruntime/blob/main/js/react_native/cpp/SessionUtils.cpp).
- **Reduced builds.** Reduced-operator and ORT-format builds exist ([custom build](https://onnxruntime.ai/docs/build/custom.html), [ORT format](https://onnxruntime.ai/docs/performance/model-optimizations/ort-format-models.html)). Using one would mean replacing that AAR. How cleanly that works is UNVERIFIED.
- **XNNPACK** covers Conv, ConvTranspose, Resize (bilinear) and pooling ([docs](https://onnxruntime.ai/docs/execution-providers/Xnnpack-ExecutionProvider.html)). Unsupported ops fall back to the CPU EP.
- **NNAPI** has no InstanceNormalization or ConvTranspose ([docs](https://onnxruntime.ai/docs/execution-providers/NNAPI-ExecutionProvider.html)) and is deprecated from Android 15 ([Android docs](https://developer.android.com/ndk/guides/neuralnetworks)). Plan on CPU and XNNPACK, with QNN as a Snapdragon-only bonus.
  - Under NNAPI, both candidate U-Nets would be split between NNAPI and the CPU, because they use InstanceNorm. Retraining with BatchNorm or GroupNorm would avoid this (my inference).

### Compute and memory

- **No benchmark.** No primary benchmark exists for a 1–2k px U-Net on a mid-range phone CPU (UNVERIFIED).
- **Nearest primary data.** [Qualcomm AI Hub's Unet-Segmentation](https://huggingface.co/qualcomm/Unet-Segmentation/blob/main/README.md): 31 M params at 640×1280.
  - 74.5 ms at w8a8 on the Snapdragon 7 Gen 4 NPU.
  - 262 ms at fp32 on the 8 Gen 1 NPU.
  - There are no CPU rows.
- **Open-ECG-Digitizer's U-Net** [calc]:
  - **Compute.** About 234 GMAC at 1024², about 700 GMAC at 1500×2100, and about 1.4 TMAC at its default 2100×3000.
  - **Memory.** A single full-resolution 32-channel fp32 feature map at 2000×1500 is about 384 MB.
  - **What it needs.** A smaller input, tiling, int8, a slimmer network or an NPU.
  - **Latency.** Seconds to tens of seconds per image at fp32 on a phone CPU (estimate).

### Classical computer vision on Android

- **[react-native-fast-opencv](https://github.com/lukaszkurantdev/react-native-fast-opencv)** (MIT, JSI, New Architecture only, tested on RN ≥ 0.85) exposes `HoughLines`, `warpPerspective`, `getPerspectiveTransform`, `connectedComponentsWithStats`, `findContours`, `matchTemplate`, `dft` and others ([function list](https://github.com/lukaszkurantdev/react-native-fast-opencv/blob/main/docs/content/availablefunctions.md)).
- **Gaps.** It lacks `remap`, which mesh rectification needs, and access to the raw Hough accumulator that Open-ECG-Digitizer reads.
- **Native code.** Those gaps, plus Hungarian matching and line-graph merging, need a small native module or a TypeScript port.
- **OpenCV itself.** The [OpenCV Android SDK](https://github.com/opencv/opencv/releases) (Apache-2.0, 5.0.0) is the fallback.

## Output length: 10 s or 2.5 s

- **The printout limits what can be recovered.** A 3×4 page carries 2.5 s of each lead at its own offset (I/II/III 0–2.5 s, aVR/aVL/aVF 2.5–5 s, V1–V3 5–7.5 s, V4–V6 7.5–10 s), plus usually a 10 s lead II. Only 12×1 is simultaneous across all 12 leads ([pdf2ECG README](https://github.com/BIVectors/pdf2ECG)).
- **What each digitizer outputs:**
  - **Open-ECG-Digitizer:** a 10 s canvas with NaN outside each lead's printed window.
  - **ECG-Digitiser, `challenge_submission` branch:** the same NaN canvas.
  - **ECG-Digitiser, cleaned `main` branch:** puts every short lead at t = 0 and writes the remainder as zeros. This was read in the code, not run. Check it before reuse.
  - **ECGtizer:** fills to 10 s with a generative model, which invents signal.
- **For DELMIR.** The classifier is trained on PTB-XL and MIMIC 10 s records. It will see either NaN-windowed 3×4 input or full 12×1 input. This belongs to the classifier and signal-contract tickets, not to the digitizer.

## For the digitizer bake-off

**Candidates:**

| # | Candidate | Why | Licence | Phone path |
|---|---|---|---|---|
| 1 | **Open-ECG-Digitizer** (Ahus-AIM) | Only open tool with positive SNR on real phone photos; handles several layouts; calibrated from the grid | CC BY-SA 4.0 | Export two U-Nets; port Hough, grid and lead matching; shrink or quantise |
| 2 | **ECG-Digitiser** (SignalSavants) | Challenge winner on scans; simplest pipeline | BSD-2 | Export the nnU-Net without test-time augmentation; port the deskew. But the fixed layout and scale and its phone-photo failures make it a baseline, not a pick |
| 3 | **Kaggle 5th place** (dangnh0611) | Best open accuracy on its template; a ceiling for what is achievable | MIT | None: desktop GPU only |

**Not candidates:**

- ECGtizer: no photos.
- Paper-ECG: manual.
- PMcardio: closed.
- BAPORLab, WAVIE, USST_Med: no code.
- mins-eth: weak on real scans (0.70 dB on its own 50 scans).

**Data with known signals:**

1. **ECG-Image-Database phone-photo subsets** (Kaggle, CC BY-ND): PTB-XL and Emory photos of clean, stained and deteriorated prints, and the Ahus OnePlus and iPhone sets. These are public, real and already scored for candidates 1 and 2.
2. **Your own photos of known signals,** taken on your phone, of your hospital's printer output or layout:
   - PTB-XL records rendered by ECG-Image-Kit in the hospital's layout, then printed and photographed;
   - or MUSE PDFs with pdf2ECG ground truth, if available.

   These cover 6×2 and 12×1, and the real paper, printer and phone DELMIR will meet.
3. **ECG-Image-Kit renders** for controlled ablations: rotation, dpi, layout.

**Measure:**

- The Challenge SNR with the `evaluation-2024` code, so numbers compare with published ones.
- Per-lead RMSE and Pearson r.
- Failure rate (no output, or wrong lead assignment).
- For each candidate network: ONNX export success, and latency and peak memory on a mid-range Android phone.

**Score the printed windows only.** Score just each lead's printed window with NaN masking, and compare at the time offsets of the printout's layout.

## Open questions

- Whether the Open-ECG-Digitizer U-Net exports cleanly to ONNX, and its latency on a phone CPU or NPU.
- Which layout, paper speed and cart DELMIR's hospital printouts use (3×4 at 25 mm/s or otherwise), and whether MUSE PDFs exist there.
- The licence of the Kaggle competition data, and the exact Kaggle leaderboard.
- Whether the real hidden files were masked to the printed windows like the recipe.
- Whether the 2024 code of BAPORLab, WAVIE or USST_Med exists anywhere outside GitHub.
