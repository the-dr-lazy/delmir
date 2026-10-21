# DELMIR classifier baselines: research notes

Scope: PTB-XL benchmark, OMI-specific models, missing leads/segments, digitization robustness.
Foundation models deliberately excluded (covered elsewhere).
Convention: every claim carries its source URL. "[UNVERIFIED]" = not confirmed against a primary source in this pass.

---

## 1. PTB-XL benchmark (Strodthoff, Wagner, Schaeffter, Samek, IEEE JBHI 2021, 25(5):1519-1528)

Source repo README: https://github.com/helme/ecg_ptbxl_benchmarking (raw: https://raw.githubusercontent.com/helme/ecg_ptbxl_benchmarking/master/README.md)
DOI: https://doi.org/10.1109/jbhi.2020.3022989 ; arXiv: https://arxiv.org/abs/2004.13701

### Leaderboard (macro-AUC on test fold 10; number in parentheses = CI half-width in last digits, from bootstrap)
Source: README above. Split stated in README: "folds 1-8 for training, fold 9 as validation set and fold 10 as test set".

| Model | all | diagnostic | subdiagnostic | superdiagnostic | form | rhythm | ICBEB all |
|---|---|---|---|---|---|---|---|
| inception1d | 0.925(08) | 0.931(09) | 0.930(10) | 0.921(06) | 0.899(22) | 0.953(13) | 0.963(09) |
| xresnet1d101 | 0.925(07) | 0.937(08) | 0.929(14) | 0.928(05) | 0.896(12) | 0.957(19) | 0.974(05) |
| resnet1d_wang | 0.919(08) | 0.936(08) | 0.928(10) | 0.930(05) | 0.880(15) | 0.946(10) | 0.969(06) |
| fcn_wang | 0.918(08) | 0.926(10) | 0.927(11) | 0.925(06) | 0.869(12) | 0.931(08) | 0.957(08) |
| lstm_bidir | 0.914(08) | 0.932(07) | 0.923(12) | 0.921(06) | 0.876(15) | 0.949(11) | 0.959(11) |
| lstm | 0.907(08) | 0.927(08) | 0.928(10) | 0.927(05) | 0.851(15) | 0.953(09) | 0.964(06) |
| Wavelet+NN | 0.849(13) | 0.855(15) | 0.859(16) | 0.874(07) | 0.757(29) | 0.890(24) | 0.905(14) |

- README leaderboard lists xresnet1d101, NOT xresnet1d50. `reproduce_results.py` trains exactly: xresnet1d101, resnet1d_wang, lstm, lstm_bidir, fcn_wang, inception1d, wavelet_standard_nn. https://raw.githubusercontent.com/helme/ecg_ptbxl_benchmarking/master/code/reproduce_results.py
- Configs also define (but leaderboard does not report) resnet1d18/34/50/101/152, xresnet1d18/34/50/152 (+ _deep/_deeper variants), wrn1d_22, xresnet1d50 with 30/50 epochs and early-stopping variants. https://raw.githubusercontent.com/helme/ecg_ptbxl_benchmarking/master/code/configs/fastai_configs.py
- Takeaway: differences among the top 4 CNNs are within CIs on every task; only Wavelet+NN is clearly worse. Architecture choice matters little on PTB-XL; ResNet/Inception-style 1D CNNs are the safe default.

### Training/inference protocol (from code, defaults of `fastai_model.__init__`)
Source: https://raw.githubusercontent.com/helme/ecg_ptbxl_benchmarking/master/code/models/fastai_model.py and https://raw.githubusercontent.com/helme/ecg_ptbxl_benchmarking/master/code/experiments/scp_experiment.py
- Sampling rate: `sampling_frequency=100` (SCP_Experiment default), i.e. the 100 Hz PTB-XL version.
- Input window: `input_size=2.5` s -> int(2.5*100) = 250 samples x 12 channels.
- Training: `chunkify_train=False` -> random 2.5 s crop from the full 10 s record each time (TimeseriesDatasetCrops).
- Validation/test: `chunkify_valid=True`, chunk length = 250, stride = 125 (input_size//2) -> overlapping 2.5 s windows, predictions aggregated with `aggregate_fn="max"` (np.amax over windows) by default.
- Hyperparameters: bs=128, lr=1e-2, wd=1e-2, epochs=50, fit_one_cycle, loss=binary_cross_entropy (multi-label), head: lin_ftrs_head=[128], ps_head=0.5 dropout, kernel_size=5 (inception1d uses 8*5=40).
- Relevance to DELMIR: the benchmark's native input (2.5 s, 12 leads, 100 Hz) matches exactly the per-lead duration of a 3x4 printout. BUT in PTB-XL all 12 leads of a crop are time-synchronous, whereas in a 3x4 printout each column of 3 leads comes from a different 2.5 s window (I,II,III @0-2.5 s; aVR,aVL,aVF @2.5-5 s; V1-V3 @5-7.5 s; V4-V6 @7.5-10 s). See section 3.

### Other paper facts (Strodthoff et al. 2021 full text, arXiv PDF https://arxiv.org/pdf/2004.13701)
- Table II also reports an **ensemble** (mean of model outputs): all .929(08), diag .939(09), sub-diag .933(12), super-diag .934(05), form .907(14), rhythm .965(07); naive baseline AUC .500. Ensembling gives only slight gains; best single model is within error bars of the ensemble.
- Architecture details (Appendix I): concat-pooling (global avg + max) before a shared head: FC with 128 hidden units, batchnorm, dropout 0.25/0.5. ResNets use enlarged kernels. RNNs: LSTM/GRU, 2 layers, 256 hidden units. Optimizer AdamW, 1-cycle LR schedule, BCE loss. Transfer to ICBEB uses gradual unfreezing + discriminative LRs.
- Test-time: record split into windows of the training window size overlapping by half, predictions aggregated by element-wise **maximum** (mean for age/sex). "This procedure considerably increases the overall performance compared to the performance on random sliding windows without any aggregation." Default window 2.5 s.
- 100 Hz vs 500 Hz (Table VI, super-diag task): no significant gain from 500 Hz (e.g. xresnet1d101 .928 @100 Hz vs .933 @500 Hz; resnet1d_wang .930 vs .922; ensemble .934 vs .931). For 500 Hz they used 5 s windows and 5x larger kernels.
- Patient-wise vs random (record-wise) split: random split inflates super-diag ensemble AUC .934 -> .937; authors call record-wise splits data leakage.
- Per-class AUCs (xresnet1d101, diag task, Fig. 5; n = test-fold count): MI superclass 0.935 (553); IMI 0.946 (328 at subclass level); AMI subclass 0.969 (308); ASMI 0.977 (236); ALMI 0.977 (29); LMI 0.914 (20); ILMI 0.965 (48); PMI 0.970 (2); INJAS 0.993 (22); INJAL 0.990 (14); STTC 0.911 (223); NORM 0.952 (964); IVCD only 0.744 (79) with hidden stratification.
- Transfer learning (xresnet1d101, PTB-XL -> ICBEB2018): with 85 training samples (1/8 of a fold) the finetuned classifier's AUC drops only ~10% relative to training on a 64x larger set; from-scratch degrades much more; at full size pretraining gives no gain. Directly relevant to DELMIR's "few hundred angio-confirmed cases" stage.

### PTB-XL dataset (Wagner et al. 2020, Sci Data 7:154)
Source: https://physionet.org/content/ptb-xl/1.0.3/ ; paper https://doi.org/10.1038/s41597-020-0495-6
- 21,799 clinical 12-lead ECGs, 18,869 patients, 10 s each, 500 Hz (records500/) and downsampled 100 Hz (records100/). 71 SCP-ECG statements. Schiller AG devices, Oct 1989 - Jun 1996. License CC BY 4.0.
- strat_fold 1-10, patient-level assignment; recommended train 1-8, val 9, test 10, because folds 9/10 records "received at least one human evaluation" (higher label quality).
- Superclass counts (multi-label): NORM 9,514; MI 5,469; STTC 5,235; CD 4,898; HYP 2,649.
- MI-related SCP statements (from https://physionet.org/files/ptb-xl/1.0.3/scp_statements.csv): MI superclass includes infarct statements IMI, ASMI, ILMI, AMI, ALMI, LMI, IPLMI, IPMI, PMI AND the acute-injury statements INJAS, INJAL, INJIN, INJLA, INJIL ("subendocardial injury in ... leads", i.e. "ischemic ST-T changes compatible with subendocardial injury"). STE_ ("non-specific ST elevation") and STD_ are FORM statements, not diagnostic. ISC* statements are under STTC.
- Implication for OMI proxy labels: PTB-XL "MI" is dominated by infarct-pattern statements (mostly established/old infarction, cf. infarction_stadium columns) rather than acute occlusion; INJ* + STE_ are the closest acute-injury proxies. [Counts of INJ*/STE_/infarction_stadium: see addendum below if the metadata download completed.]

---

## 2. Published OMI-specific models

### 2a. Al-Zaiti et al. 2023, Nature Medicine 29:1804-1813, "Machine learning for ECG diagnosis and risk stratification of occlusion myocardial infarction"
Source: full text via Europe PMC https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10353937/fullTextXML (PMC10353937; DOI 10.1038/s41591-023-02396-3)
- Population: prehospital 12-lead ECGs of chest-pain patients WITHOUT a STEMI pattern (confirmed prehospital STEMI excluded), US EMS. Derivation 4,026 patients (5.2% OMI, n=210); external validation 3,287 patients from 2 other sites (6.4% OMI, n=209). Total 7,313.
- Culprit distribution (derivation / validation): total LAD occlusion 91 (2.3%) / 94 (2.9%); total LCx 63 (1.6%) / 88 (2.7%); total RCA 101 (2.5%) / 102 (3.1%).
- OMI label: angiographic acute culprit lesion in LAD/LCx/RCA or primary branch with TIMI 0-1; or TIMI 2 with >70% stenosis and peak (4th-gen, not hs) troponin 5-10 ng/mL. Two independent reviewers, kappa 0.771.
- Signals: Philips HeartStart MRX or LIFEPAK-15, 500 Hz, 0.05-150 Hz. ECGs with poor quality or missing leads removed. Features computed by Philips DXL 12/16-lead algorithm on per-lead median beats.
- Model: 73 morphological features selected from 554 temporal-spatial metrics (hybrid data-driven + expert). 10 classifiers compared (RF, KNN, GBM, XGB, SVM, ANN, regularized LogReg, LDA, SGD-LogReg, ...); **random forest** chosen (best bias-variance).
- Results: hold-out test (derivation cohort) AUROC 0.91 (95% CI 0.87-0.96) vs clinicians 0.79 (CI printed as "0.73-0.76" in the paper, apparent typo) vs FDA-cleared commercial system 0.78 (0.70-0.85). External validation AUROC 0.87 (0.85-0.90) vs commercial 0.75 (0.71-0.79) vs clinicians 0.80 (0.77-0.83).
- OMI risk score: 74.4% classified low risk -> rule-out sensitivity 0.91, NPV 0.993, missed-event rate 0.5%; 4.6% high risk -> rule-in specificity 0.976, PPV 0.514.
- Top SHAP features: slight ST depression in V1, V2, I, aVL; slight ST elevation in III and V4-V6; loss of anterior concavity; T-wave enlargement; T axis, TCRT, TpTe, ST80. Median beats pooled: OMI(+) n=414 ECGs vs NSR OMI(-) n=9,072.
- **Public data**: the 73 features + outcomes for derivation and validation cohorts plus Python code: https://github.com/zeineb-bouzid/sharing-github-nature-medicine (raw waveforms only by request/DUA). [Repo contents not opened in this pass: UNVERIFIED whether culprit vessel is included.]
- Relevance: strong evidence that median-beat ST/T morphology features + a simple tree model reach AUROC ~0.87-0.91 for NSTE-OMI with ~200 positives. Requires full 10 s, 12-lead synchronous digital ECG for the Philips feature extractor, so it is not directly reproducible from a 3x4 photo, but a median-beat-per-lead feature approach IS compatible with 2.5 s/lead (2-3 beats per lead).

### 2b. Herman et al., Eur Heart J Digit Health 2024;5(2):123-133 (online 28 Nov 2023), "International evaluation of an artificial intelligence-powered electrocardiogram model detecting acute coronary occlusion myocardial infarction" (PMcardio OMI / "Queen of Hearts", Powerful Medical)
Source: full text (CC BY) via Europe PMC https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10944682/fullTextXML (PMC10944682; DOI 10.1093/ehjdh/ztad074; PMID 38505483)
- Data: Cardiovascular Centre Aalst (Belgium) 2011-2021, 9,764 suspected-ACS patients (GE MUSE XML, 500 Hz) + an "international image database" of 2,368 ACS patients whose ECG images (multiple vendors) were digitized with Powerful Medical's CE-certified PMcardio digitizer. ECGs >24 h before angiography, post-angiography, or poor quality excluded.
- Development set: 18,616 ECGs / 10,543 patients, 22.9% OMI. Test set: 3,254 ECGs / 2,222 patients, 21.6% OMI (internal EU 2,016 ECGs, 240 OMI = 16%; external US 1,238 ECGs / 633 contacts, 213 OMI = 36.2%).
- OMI definition: Universal-Definition MI + angiographic acute culprit with TIMI 0-1, OR TIMI 2-3 with emergent/urgent PCI. Patients without dynamic serial biomarkers ruled out regardless of angiography.
- **Input format (key for DELMIR): all digital and digitized ECGs "standardized into a 3x4 ECG format (2.5 s per lead). For longer ECG formats, the first 2.5 s of limb leads and the last 2.5 s of pre-cordial leads were used."** I.e. training data were cut to mimic the printed 3x4 layout.
- **Architecture: deep CNN, lead-specific feature extractor = 2 conv layers + 6 residual blocks (~60,000 params), applied per lead; classifier = 2 fully connected layers over all leads' features (~150,000 params).** Total ~210k params -> trivially phone-deployable. Explainability in supplement (not read).
- Threshold: chosen on validation set by maximizing MCC (0.1106); second threshold matched to STEMI-criteria specificity.
- Results (overall test): AUC 0.938 (0.924-0.951); accuracy 90.9%, sensitivity 80.6% (76.8-84.0), specificity 93.7% (92.6-94.8). STEMI criteria: AUC 0.651, sens 32.5%, spec 97.7%. Two ECG experts: AUC 0.843, sens 73.0%, spec 95.7%. AI at STEMI-matched specificity (97.5%): sensitivity 65.8%. EU internal AUC 0.946 (0.925-0.961); US external AUC 0.903 (0.893-0.939).
- Culprit vessel distribution among test OMIs: LAD 234 (37.1%), LCx 142 (22.5%), RCA 220 (34.9%), LMCA 11, PDA 9, RI 11, multi-vessel 4. No culprit-localization output reported in this paper.
- False positives: 111 (AI) vs 41 (STEMI criteria) vs 77 (experts); STEMI criteria missed 330 OMIs (67.5% of all OMI).
- Caveats: retrospective, company-authored; training data and weights not public.

### 2c. Gustafsson et al., Nature Communications 17:4336 (2026), "A deep learning ECG model for identification and localization of occlusion myocardial infarction" (preprint medRxiv 10.1101/2025.09.11.25335407, Sep 2025)
Sources: article https://www.nature.com/articles/s41467-026-73023-1 (CC BY); abstract via https://api.biorxiv.org/details/medrxiv/10.1101/2025.09.11.25335407 ; code https://github.com/stefan-gustafsson-work/omi
- Authors: Gustafsson, A.H. Ribeiro, Gedon, ..., A.L.P. Ribeiro, Lindholm, Schön, Sundström (Uppsala; same group as Ribeiro et al. 2020 Nat Commun "Automatic diagnosis of the 12-lead ECG using a DNN").
- Data: Swedish Emergency Department Database (SwED), 540,372 ECGs / 465,471 ED visits / 225,824 patients (Karolinska GE MUSE v9). Labels: 1,583 OMI (0.3%), 4,279 nOMI (0.8%), 534,510 controls (98.9%). OMI = newly formed total or near-total occlusion (TIMI 0) per angiographer (SWEDEHEART SCAAR). Culprit among OMIs: LM/LAD 595 (37.6%), LCx 359 (22.7%), RCA 629 (39.7%).
- Split: patient-level 70% train / 10% val / random test + temporal test (patients first seen in 2016). Max one ECG per visit in val/test.
- Input: 10 s, 8 leads (I, II, V1-V6; the other 4 are linear combinations), baseline wander removed, resampled to 400 Hz, zero-padded to 4096 samples. Plus age and sex (embedded to 64-d, concatenated before final FC).
- Architecture: 1D ResNet from Ribeiro et al. 2020; repo defaults kernel 17, filters [64,128,196,256,320], seq lengths [4096,1024,256,64,16], dropout 0.8 (https://raw.githubusercontent.com/stefan-gustafsson-work/omi/main/model/main.py). **My count from the repo's resnet.py: 6,915,872 params for the ResNet trunk (excluding final FC + age/sex), per member; ensemble of 5 members (logits averaged) -> ~35M total.** Up to 150 epochs.
- Label design (directly reusable for DELMIR): one softmax over 10 mutually exclusive classes: control_nomyoperi, control_myoperi, mi_nstemi_nonomi, mi_stemi_nonomi, mi_{nstemi,stemi}_omi_{lmca_lad,lcx,rca}; plus a separate sigmoid for LBBB (co-occurring). Loss = w*CE + (1-w)*BCE, best BCE:CE weight ratio 0.3. Source: https://raw.githubusercontent.com/stefan-gustafsson-work/omi/main/03.01-train.sh and paper Methods. OMI probability = sum of OMI sub-class probabilities; culprit = argmax among OMI sub-classes.
- Results: SwED test sets OvA C-statistic >= 0.95 for OMI super-class, >= 0.87 for nOMI; at 5% FPR, OMI sensitivity 0.87 across both test sets; culprit localization "performed well" OvA but **poor OvO discrimination between OMI-LCx and OMI-RCA** (exact per-vessel numbers are in Supplementary Table 2, not read). Beat GE 12SL statements for STEMI at equal false positives.
- External: InCor (São Paulo, 401 ECGs) OMI vs control C-statistic 0.83; OMI-STEMI 0.96 vs OMI-NSTEMI 0.82. Also tested on PTB-XL and CODE-II for STEMI/LBBB vs control only. Calibration "acceptable".
- Weights: NOT public ("parameter/hyperparameter estimates ... available upon request"). Code public.
- Relevance: the only large model with explicit LAD/LCx/RCA culprit output from outcome labels. It shows (a) LCx vs RCA is the hard pair, (b) OMI-NSTEMI external AUC ~0.82 is the realistic ceiling to expect, (c) it needs full 10 s synchronous leads (not 3x4).

### Parameter counts of PTB-XL benchmark models (computed by me)
Method: instantiated the repo's model classes (https://github.com/helme/ecg_ptbxl_benchmarking/tree/master/code/models) with PyTorch 2.x CPU, minimal fastai stubs (Flatten, bn_drop_lin, Lambda, listify), 12 input channels, 71 outputs (the "all" task), head lin_ftrs=[128], same kernel sizes as fastai_model.py (5; inception 40). Input (2, 12, 250) forward pass verified.
- xresnet1d50: 962,503 | xresnet1d101: 1,880,775 | resnet1d_wang: 481,863 | inception1d: 516,167 | fcn_wang: 318,279 | lstm: 912,199 | lstm_bidir: 2,339,143.
- Caveat: these are from code, not from the paper (the paper gives no parameter counts). Head stubs mirror fastai v1's bn_drop_lin; counts could differ by a few hundred parameters from the original fastai head.
- All are < 2.5M params: every PTB-XL baseline fits easily into ONNX Runtime Mobile. Herman's PMcardio OMI model is ~210k.

### 2d. Culprit-vessel CNN (STEMI only): Wu et al. 2022, Front Cardiovasc Med 9:797207, "Deep Learning Networks Accurately Detect ST-Segment Elevation Myocardial Infarction and Culprit Vessel"
Source: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8960131/fullTextXML (PMC8960131)
- Single Chinese center; digital 10 s 12-lead ECG at 1,000 Hz. Cohort 1: 793 angiography patients, 315 STEMI (isolated LAD 163, RCA 107, LCx 45); multi-vessel disease excluded. Test: 883 cases (506 control, 377 STEMI) internal + external.
- Models: small CNN (3 conv layers, kernel 2, 32/32/48 filters), LSTM, and CNN-LSTM. Hierarchical: stage 1 control vs STEMI; stage 2 model A {control, LAD, LCx-RCA} + model B {LCx vs RCA}.
- Results: CNN-LSTM STEMI AUC 0.99; LAD discrimination AUC 0.96 (similar to cardiologists/EM physicians); RCA vs LCx AUC 0.81 (comparable to doctors).
- Relevance: tiny label counts (45 LCx!) still give LAD AUC ~0.96 on STEMI; the hierarchical LAD-vs-(LCx/RCA) then LCx-vs-RCA split mirrors the Gustafsson finding that LCx/RCA is the hard pair. STEMI only, so optimistic relative to NSTE-OMI.

---

## 3. Missing leads / segments

### 3a. PhysioNet/CinC Challenge 2021, "Will Two Do? Varying Dimensions in Electrocardiography"
Sources: challenge page https://moody-challenge.physionet.org/2021/ ; Reyna et al., "Issues in the automated classification of multilead ECGs using heterogeneous labels and populations", Physiol Meas 2022 (text read from the authors' PDF; challenge page cites it); Reyna et al., CinC 2021;48:1-4 ("Will Two Do?"); official leaderboards https://moody-challenge.physionet.org/2021/results/ (files 2021_Challenge_Test_Results_Leaderboard_For_Official_Entries-{12,6,4,3,2}-lead.csv)
- Data: 131,149 12-lead recordings from 10 international sources; 88,253 public training; rest hidden validation/test. 30 scored diagnoses (mostly rhythm/conduction/axis; few ischemia classes). Sampling 250 Hz-1 kHz, durations 5 s-30 min.
- Lead sets: 12 (all); 6 = I, II, III, aVR, aVL, aVF; 4 = I, II, III, V2; 3 = I, II, V2; 2 = I, II. Training data always full 12-lead; reduced sets only at validation/test.
- 68 teams, 1,056 entries; 39 official. ~90% of official entries were deep learning (ResNet-type CNNs most common); ~30% of DL entries added hand-crafted features.
- Headline finding (paper abstract): "The performance differences across the different lead combinations were smaller than the performance differences across the different test databases." Median relative change from validation to full test set: -17% (12-lead), -19% (6), -17% (4), -19% (3), -18% (2); to the undisclosed (no training data) database: -36% to -41% (Table 6). Mean change across lead combinations 2.6%. A post-hoc voting model improved performance by 3.5%.
- My computation from the official leaderboards (39 teams, hidden test "Test set" challenge metric): relative change vs 12-lead, median (mean): 6-lead -2.1% (-4.2%), 4-lead -2.3% (-4.0%), 3-lead -2.1% (-4.3%), 2-lead -4.1% (-6.7%). Top 5 teams 12/6/4/3/2: ISIBrno-AIMT 0.58/0.58/0.58/0.58/0.58; NIMA 0.55/0.51/0.56/0.55/0.56; DSAIL_SNU 0.55/0.58/0.58/0.57/0.57; cardiochallenger 0.55/0.51/0.53/0.51/0.53; USST_Med 0.54/0.52/0.50/0.51/0.50.
- **Winning method (ISIBrno-AIMT; Nejedly et al., CinC 2021, https://www.cinc.org/archives/2021/pdf/CinC2021-014.pdf): ONE model for all lead sets.** Input always expanded to a fixed 12 x T matrix; missing leads zero-filled. Resample to 500 Hz, 1-47 Hz Butterworth bandpass, per-lead z-score, zero-pad/random-crop to 8,192 samples. **Augmentation: during training randomly choose a lead configuration (12/6/4/3/2) and zero the unused leads.** Features after the CNN+multi-head attention are **concatenated with a binary lead-indicator vector** before the FC classifier. ResNet blocks (first conv kernel 15, then kernel 9, stride 2), adaptive max pooling, BCE + differentiable challenge-score loss + sparsity loss; ensemble of 3. Result: identical 0.58 test score on all five lead sets (validation 0.64/0.62/0.63/0.63/0.62).
- Caveat for DELMIR: the 2021 label set is dominated by rhythm/conduction diagnoses, which are visible in limb leads; ischemia/OMI depends on precordial and territory-specific leads, so a 2-lead result says little about OMI. The transferable lessons are the mechanics: zero-fill + random lead-set masking + lead-presence indicator gives one model robust to missing leads.

### 3b. Papers explicitly handling the 3x4 asynchronous layout
1) **Herman et al. 2024 (PMcardio OMI)**, see 2b: trained on everything converted to 3x4 with 2.5 s/lead; for 10 s digital ECGs they took "the first 2.5 s of limb leads and the last 2.5 s of pre-cordial leads" (i.e. 2 windows rather than the true 4 printed windows). Lead-specific feature extractor (shared or per-lead weights not stated) + FC fusion. This is the only OMI model found that is natively 3x4. Source: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10944682/fullTextXML

2) **PatchECG: Zhang, ..., Hong, "Masked Training for Robust Arrhythmia Detection from Digitalized Multiple Layout ECG Images", arXiv:2508.09165v2 (rev. 27 Mar 2026)**. Source: https://arxiv.org/html/2508.09165v2 ; code https://github.com/zhangshanwei-mm/PatchECG
- Problem statement matches DELMIR: digitized printouts in 3x4 / 6x2 / 12x1 give asynchronous 2.5 s or 5 s per-lead segments; avoids interpolation.
- Method: per-lead random contiguous masking during training (NaN); leads cut into non-overlapping patches of P=64 samples; binary observed/missing indicator concatenated per patch; fully-missing patches DROPPED before the Transformer; learnable lead + time embeddings (so a patch knows which lead and which time window it came from); Net1D-style patch encoder with SE blocks; "Segment-Shuffle-Stitch" module (3 layers); Transformer hidden 768, depth 3, 8 heads, CLS token. 21.72M params. Adam 1e-3, wd 1e-4, batch 64, 30 epochs, focal loss.
- Data: PTB-XL 21,388 records, 23 diagnostic subclasses, official folds; 21,388 ECG-Image-Kit 3x4 images digitized with the 2024 CinC winning digitizer; external Chaoyang Hospital 400 patients (200 AF), manually digitized with PaperECG.
- Results: simulated layouts mean AUROC ~0.835 (Net1D encoder 0.829-0.835; with frozen ECGFounder encoder 0.872-0.882); interpolation baselines (zero-fill, KNN, SAITS) 0.750-0.775. Chaoyang AF AUROC 0.778 vs ECGFounder 0.667; 12x1 subset 0.893 vs 0.703.
- Caveat: these 23-subclass AUROCs (~0.83) are well below the synchronous 10 s PTB-XL sub-diag benchmark (~0.93) — not directly comparable (different model/training), but it signals a real cost of 3x4 asynchrony + digitization. [Exact per-lead time windows of their simulated 3x4 not stated in the text read: UNVERIFIED.]

3) **Generic lead-masking recipe** (from CinC 2021 winner, 3a): zero-fill + random lead-set dropout + lead-presence indicator. For 3x4, the natural generalization is a per-lead *time* mask: from a synchronous 10 s PTB-XL record, keep for lead L only the 2.5 s window its printout column would show (I/II/III 0-2.5 s, aVR/aVL/aVF 2.5-5 s, V1-V3 5-7.5 s, V4-V6 7.5-10 s), optionally keep full 10 s of the rhythm-strip lead (usually II), and feed a presence mask. This is what PatchECG's lead/time embeddings + missing indicator implement. (Design inference, not from a single paper.)

### Addendum to section 1: PTB-XL MI/injury label counts (computed by me)
Source file: https://physionet.org/files/ptb-xl/1.0.3/ptbxl_database.csv (21,799 records, 18,869 patients, columns include infarction_stadium1/2, validated_by_human, baseline_drift, static_noise, burst_noise, electrodes_problems, extra_beats, pacemaker, strat_fold).
- Record counts with statement present (any likelihood): IMI 2,676; ASMI 2,357; ILMI 478; AMI 353; ALMI 288; LMI 201; IPLMI 51; IPMI 33; PMI 17. Injury: INJAS 214; INJAL 145; INJIN 18; INJLA 17; INJIL 15 -> any INJ* = 323 records; any INJ* or STE_ = 351. STE_ alone 28; STD_ 1,009; ISC_ 1,272; ISCAL 659; ISCIN 218; ISCIL 179; ISCAS 169; ISCLA 140; ISCAN 44.
- infarction_stadium1: Stadium I 166, I-II 5, II 88, II-III 943, III 980, "unknown" 3,430, empty 16,187. infarction_stadium2: I 19, II 19, III 65. (Stadium I = acute-phase; III = old/chronic per the PTB-XL paper; exact definitions not re-read here: UNVERIFIED wording.)
- Fold sizes: 2,173-2,198 records each (fold 10 = 2,198; fold 9 = 2,183).
- Takeaway: PTB-XL acute-injury-like positives are only ~300-350 records (INJ*/STE_), and acute-stage infarcts (Stadium I / I-II) ~170. PTB-XL can teach "MI territory morphology" (thousands of IMI/ASMI) but offers very few acute-occlusion proxies.

---

## 4. Robustness to digitization / image input

### 4a. George B. Moody PhysioNet Challenge 2024, "Digitization and Classification of ECG Images"
Sources: challenge page https://moody-challenge.physionet.org/2024/ ; results files https://moody-challenge.physionet.org/2024/results/official_scores_digitization.tsv , .../official_scores_classification.tsv , .../team_summary_table.tsv ; Reyna et al., CinC 2024 challenge paper "Digitization and Classification of ECG Images: The George B. Moody PhysioNet Challenge 2024" (PDF text read)
- Data: public = 21,799 PTB-XL waveforms + labels, with ECG-Image-Kit-generated images (teams could generate more). Hidden = 1,977 12-lead records (PTB-XL + Emory University Hospital) printed and captured as **35,595 real ECG images** ("ECG-Image-Database"). 250 or 500 Hz, 16-bit WFDB.
- 11 classes: acute MI, AF/AFL, bradycardia, conduction disturbance, hypertrophy, normal, old MI, PAC, PVC, ST/T change, tachycardia. Acute vs old MI split came from PTB-XL+ labels.
- Metrics: digitization = per-channel SNR (alignment-tolerant to small shifts, scaled by fraction digitized); classification = macro F-measure.
- Participation: 62 teams, 568 algorithms; 11 teams ranked for digitization, 12 for classification.
- **Digitization (SNR in dB, leaderboard / extended hidden mean)**: 1 SignalSavants 12.151 / 0.57; 2 BAPORLab 5.493 / 1.47; 3 wavie_ABI 5.469 / N/A; 4 Ahus AI Lab 3.047; 5 USST_Med 2.202. Per-condition SNRs of the winner collapse on real captures: color scans clean 4.930, B/W scans clean 3.479, **mobile phone photos clean -1.071, phone photos stained -0.723, phone photos deteriorated -1.304**, screenshots -1.759. BAPORLab: color scan 6.220, phone clean -0.261, phone deteriorated 0.807. (Leaderboard SNR is on synthetic-like leaderboard data; the extended real-paper data are far worse.)
- **Classification (macro F, leaderboard)**: 1 AIMED 0.817 (extended mean 0.73); 2 Inventec AIC 0.742 (0.70); 3 BAPORLab 0.730 (0.66); 4 CeZIS 0.645. AIMED per condition: color scan clean 0.833, B/W clean 0.796, **phone photo clean 0.644, phone stained 0.636, phone deteriorated 0.711**, screenshots 0.636. Inventec AIC was more photo-robust: phone clean 0.697, stained 0.694, deteriorated 0.739.
- Challenge-paper discussion: teams with higher SNR generally had higher F, but several teams with **negative SNR still reached F close to the top** -> organizers read this mostly as "an indictment of our signal fidelity measure" (SNR is dominated by high-amplitude errors that do not matter clinically), and only possibly as evidence that an intermediate time series is unnecessary. Powerful Medical's PMcardio digitizer was evaluated via API and "outperformed the Challenge algorithms" but also varied across hidden-data variants (no numbers given).
- Winning approaches:
  - AIMED (classification #1; Dias et al., CinC 2024 paper 398): **direct image classification**, ConvNeXt pre-trained on ECG images rendered from CODE-15% (+ private InCor image sets) via ECG-Image-Kit, then PTB-XL images; internal 5-fold F1 0.698 +/- 0.022; hidden 0.817.
  - Inventec AIC (#2; Chou & González, paper 224): dual system: contour-based grid detection/rotation fix, YOLOv7 lead localization, CNN+self-attention digitizer, separate classifier; SNR 1.479 & F 0.728 (official-phase numbers in their paper).
  - SignalSavants (digitization #1; Krones, Lyons, Mahdi, Walker, paper 97): Hough transform (rotation) + deep-learning segmentation; code "ECG-Digitiser" https://github.com/felixkrones/ECG-Digitiser (link from PatchECG paper; not opened).
- **Direct image-vs-signal comparison (CeZIS; Antoni et al., CinC 2024 paper 231, DOI 10.22489/CinC.2024.231)**: on identical PTB-XL records, 5-fold CV macro F1: **image model (ImageNet-pretrained ConvNeXt, 600x512 synthetic ECG-Image-Kit images) 0.8496 +/- 0.0020 vs 1D ResNet-50 (1/4 width, 4,608 samples x 12 leads @500 Hz) on the original digital signal 0.8518 +/- 0.0050.** Per-label F1 very similar; Acute MI the worst label (few positives). Hidden test only 0.645 (worst on B/W scans). Signal-model augmentations: random fixed-length slices, lead rescaling, lead dropout, periodic slice cutout.
- Takeaways for DELMIR: (1) phone photos are the hardest condition for both digitization (SNR ~ -1 dB even for the winner) and classification (F drops ~0.15-0.2 vs scans for AIMED); (2) a classifier trained on synthetic images can match a signal classifier on synthetic images, but generalization to real captures is the bottleneck; (3) "acute MI" was the weakest class in this challenge.

### 4b. ECG-Image-Kit (Shivashankara, Deepanshi, Shervedani, Clifford, Reyna, Sameni; arXiv:2307.01946v4, 7 Feb 2024; Physiol Meas 2024)
Sources: arXiv PDF https://arxiv.org/abs/2307.01946 (v4 text read); repo https://github.com/alphanumericslab/ecg-image-kit ; generator README https://github.com/alphanumericslab/ecg-image-kit/tree/main/codes/ecg-image-generator ; code https://raw.githubusercontent.com/alphanumericslab/ecg-image-kit/main/codes/ecg-image-generator/extract_leads.py and config.yaml
- Generates synthetic paper-ECG images from WFDB time series: standard grid (red/pink/blue/green/brown or B/W, or no grid), calibration pulse, printed header text, handwritten-style text (7 styles), wrinkles and creases (image-quilting texture synthesis), perspective transforms, rotation, color temperature, random resolution (50..r DPI), padding, QR codes; optional time-series noise before rendering (PhysioNet Noise Stress Test + OSET synthetic baseline wander, powerline, motion, EMG). Stores lead bounding boxes and per-lead start/end sample indices in JSON (`--store_config`, `--lead_bbox`).
- **3x4 layout timing (verified in code):** `paper_len: 10.0`, `format_4_by_3: [[I,II,III],[aVR,aVL,aVF],[V1,V2,V3],[V4,V5,V6]]`; for columns=4 each lead is cut to 10/4 = 2.5 s and column k starts at k*2.5 s (`shiftedStart = start + int(k*rate*lead_length_in_seconds)`), i.e. I/II/III 0-2.5 s, aVR/aVL/aVF 2.5-5 s, V1-V3 5-7.5 s, V4-V6 7.5-10 s; plus a full 10 s rhythm strip (`--full_mode`, default II). `--mask_unplotted_samples` writes the companion WFDB signal with unplotted samples set to NaN -> ready-made training targets for 3x4-masked classifiers.
- Paper notes that older machines swept 2.5 s segments asynchronously (segments in a column may not share a time frame), so multichannel synchrony cannot be assumed in general.
- Case study: 21,801 images from the PhysioNet QT database; DL digitizer on 1,000 synthetic eval images: mean SNR 11.88 dB (SD 8.91), median-based SNR 26.54 dB (SD 10.11), MSE 0.039 mV, PSNR 31.26 dB; spike errors dominate. Recommends >= 200 DPI for scanning (ECG content mostly < 100 Hz). Generated images used 200 +/- 5 DPI.
- Clinical parameters (QRS width, RR, QT) from digitized vs ground truth were compared on 10,000 images [numbers not extracted in this pass: UNVERIFIED].

### 4c. Classifier accuracy on digitized vs original signals
1) **CeZIS (CinC 2024)**: synthetic images -> image classifier F1 0.8496 vs signal classifier 0.8518 on originals (see 4a). Near parity on synthetic data.
2) **ECGtizer (Lence et al., arXiv:2412.12139v1, 9 Dec 2024)**, https://arxiv.org/abs/2412.12139 : DenseNet TdP-risk (sotalol IKr-block) classifier, Generepol dataset 3,066 Sot- / 2,734 Sot+ ECGs rendered to paper via ecg2pdf then digitized; lead II 10 s strip only. Trained on original XML, tested on digitized (Table 4): accuracy original 0.94 / F1 0.93 vs ECGtizerFull 0.85 / 0.82, ECGtizerFrag 0.83 / 0.80, ECGtizerLazy 0.76 / 0.75, ECGminer 0.47 / 0.64. Retraining on digitized training data (Table 5) improved results but still did not match the original. Authors blame peak-amplitude errors plus smoothing/resampling in digitization.
3) **Herman et al. 2024 (PMcardio)**: training mixed native digital ECGs (Aalst, 500 Hz) with ~2,368 patients' digitized images; reports overall AUC 0.938 but no separate digital-vs-digitized breakdown in the main text [supplement not read].
4) **PatchECG (arXiv:2508.09165)**: trained on PTB-XL with masking; evaluated on 21,388 ECG-Image-Kit 3x4 images digitized by the 2024 winning digitizer and on 400 real manually-digitized hospital ECGs (AF AUROC 0.778). Text did not give the PatchECG AUROC on the generated-image set.
5) **Nguyen et al., arXiv:2502.14909 (Feb 2025)**, "Comparing Deep Neural Network for Multi-Label ECG Diagnosis From Scanned ECG": compares AlexNet/VGG/ResNet/ViT on scanned ECGs and whether digitized signals keep diagnostic information; abstract gives no numbers (full text not read: UNVERIFIED).

### 4d. Augmentations that simulate digitizer error (from the sources above)
- Time-series side (CeZIS signal model, CinC 2024): random fixed-length slices, per-lead amplitude rescaling, lead dropout, periodic slice cutout. (CinC 2021 winner: random lead-set zeroing.) (PatchECG: per-lead random contiguous NaN masks + missing indicator.)
- Image side (ECG-Image-Kit): wrinkles, creases, handwriting, printed text, rotation/perspective, B/W, grid color/absence, low DPI (50+), padding.
- Round-trip augmentation: render PTB-XL/MIMIC-IV-ECG with ECG-Image-Kit (3x4 + rhythm strip, `--mask_unplotted_samples`), then run DELMIR's own digitizer and train the classifier on its output. This is what CinC 2024 teams and PatchECG effectively did; the ECGtizer result (retraining on digitized data closes part of the gap) supports it.
- Error types that matter most per sources: peak/amplitude errors (ECGtizer), spike errors (ECG-Image-Kit), and phone-photo conditions (CinC 2024 per-condition scores). [No source found that injects calibrated "digitizer-like" noise directly into time series and measures the gain: open gap.]

---

## 5. Synthesis for DELMIR (my reading of the above; not from one source)
- Backbone: 1D CNN in the 0.2-2M param range is enough (PTB-XL top models 0.3-1.9M; PMcardio OMI ~210k). Parameter size will not be the bottleneck on the phone.
- Input representation: train on PTB-XL/MIMIC-IV-ECG with the exact ECG-Image-Kit 3x4 windows (I/II/III 0-2.5, aVR/aVL/aVF 2.5-5, V1-V3 5-7.5, V4-V6 7.5-10 s) + 10 s lead II, with a per-sample/per-patch presence mask; PMcardio and PatchECG are precedents. 100 Hz is sufficient for PTB-XL statements (Strodthoff Table VI) but ST-segment detail for OMI may warrant 250-500 Hz [no source tested sampling rate for OMI: open question].
- Labels: copy Gustafsson's single softmax {control, nOMI, OMI-LAD/LM, OMI-LCx, OMI-RCA} (optionally x STEMI/NSTEMI); expect LCx vs RCA to be the weakest discrimination (Gustafsson OvO; Wu 2022 RCA-vs-LCx AUC 0.81).
- Realistic targets: NSTE-OMI external AUROC ~0.82-0.87 (Gustafsson InCor OMI-NSTEMI 0.82; Al-Zaiti external 0.87); PMcardio 0.90-0.95 with ~4,000 OMIs in training. With a few hundred angio cases, PTB-XL pretraining helps most in the small-data regime (Strodthoff ICBEB transfer experiment).
- Digitization robustness is the dominant risk: phone photos cut CinC 2024 winners' F by ~0.15-0.2 and digitization SNR to about -1 dB. Plan to train on the outputs of DELMIR's own digitizer.

---
Provenance note: some primary-source PDFs/TSVs (CinC 2021 Physiol Meas paper, CinC 2021 winner paper 014, CinC 2024 challenge paper and team papers 224/231/398, ECG-Image-Kit arXiv v4, ECGtizer arXiv, 2024 official score TSVs) were read from text extractions downloaded by sibling research agents during this research; their identity was checked by title/author/DOI headers. The CinC 2021 leaderboards, 2024 results listing, PTB-XL metadata, Al-Zaiti/Herman/Wu full texts, Gustafsson article and repo, PTB-XL benchmark repo and paper, and ECG-Image-Kit code were fetched by me directly.
