# Which classifier designs suit OMI detection with few labels on a phone?

Research for [#15](https://github.com/the-dr-lazy/delmir/issues/15), feeding the decision ticket [Which classifier architecture and output heads does DELMIR use?](https://github.com/the-dr-lazy/delmir/issues/23). Researched 2026-10-21 against primary sources: the papers, official repositories and their code, Hugging Face model cards, PhysioNet pages, and the PyTorch, ONNX Runtime, Captum, scikit-learn and ROCm docs.

This file is the synthesis. Each claim links its source. The detailed notes, with every number and its source, are in three companion files:

- [`baselines-and-omi-models.md`](ecg-classifier-designs/baselines-and-omi-models.md): the PTB-XL benchmark, published OMI and culprit models, missing leads, and digitization robustness.
- [`foundation-models.md`](ecg-classifier-designs/foundation-models.md): open-weight ECG foundation models, self-supervised pretraining, and MIMIC-IV-ECG.
- [`heads-calibration-uncertainty-deployment.md`](ecg-classifier-designs/heads-calibration-uncertainty-deployment.md): masked heads, calibration, uncertainty, lead attribution, ONNX export and quantisation, and ROCm.

Some numbers were measured locally because the sources were thin: parameter counts, FLOPs, desktop ONNX Runtime latency, and ONNX Runtime's handling of dropout and gradients. Measurements ran on a desktop CPU (torch 2.13, onnx 1.23, onnxruntime 1.27), never on a phone, and are marked *measured*. The scripts are in [`ecg-classifier-designs/scripts/`](ecg-classifier-designs/scripts/).

## Answer

**Start from an established small 1D CNN, not a large foundation model.** Use the PTB-XL benchmark's xresnet1d101 (1.9 M parameters) or inception1d (0.5 M). Train it on input laid out like a 3×4 printout. Give it two heads: a sigmoid head for P(OMI), and a softmax over LAD, LCx and RCA whose loss is masked, so it learns only from OMIs that have a culprit vessel.

- **Uncertainty:** train five copies of that model (a deep ensemble). The spread of their outputs gives the confidence word.
- **Calibration:** temperature- or Platt-scale the ensemble's averaged logit, fitted on digitized ECGs that look like the ones DELMIR will see.
- **Lead attribution:** on the phone, zero out one lead at a time and see how P(OMI) changes. Integrated gradients serves only as an offline check.
- **On the phone:** the whole bundle is a few MB in fp32 and a few hundred forward passes of a tiny network.

**The few-label problem is solved by transfer, not by architecture.** On PTB-XL the top CNNs sit within each other's confidence intervals. Pretraining, by contrast, is what rescues tiny training sets. Train on PTB-XL's 71 statements and MIMIC-IV-ECG's machine statements first, then fine-tune on OMI labels. Then test one upgrade against that baseline: a backbone initialised from **ECGFounder** (MIT, a CNN, top-3 in an independent benchmark) or **MERL** (MIT, a 4.6 M-parameter ResNet pretrained on MIMIC-IV-ECG).

**Avoid** the transformer foundation models:
- ECG-FM, HuBERT-ECG base/large and Kim's ECG-JEPA are 87–97 M parameters and 19–74 GFLOP per input.
- ST-MEM's code is "all rights reserved".
- HuBERT-ECG's weights are non-commercial.

**Two risks dominate, and no source settles either for DELMIR:**

1. **The 3×4 layout.** In a 3×4 printout each column of three leads comes from a different 2.5 s window. No foundation model, and only one OMI model, has been evaluated on that layout.
2. **Digitizer error on phone photos.** It cuts classification sharply in the PhysioNet Challenge 2024.

Both need measuring, not more reading. A new measuring spike, [#42](https://github.com/the-dr-lazy/delmir/issues/42), compares input designs on PTB-XL with simulated 3×4 layouts. Training on DELMIR's own digitizer output (the round trip below) is the mitigation the sources support.

The rest of this file gives the reasoning, topic by topic.

---

## 1. Baselines: what a "standard" 12-lead classifier is

**The PTB-XL benchmark** (Strodthoff et al., IEEE JBHI 2021, [arXiv 2004.13701](https://arxiv.org/abs/2004.13701); code [helme/ecg_ptbxl_benchmarking](https://github.com/helme/ecg_ptbxl_benchmarking)) is the reference point most ECG papers report against.

| Model | Params (counted from code) | PTB-XL "all" macro-AUC | superdiagnostic |
|---|---|---|---|
| inception1d | 0.52 M | 0.925 | 0.921 |
| xresnet1d101 | 1.88 M | 0.925 | 0.928 |
| resnet1d_wang | 0.48 M | 0.919 | 0.930 |
| fcn_wang | 0.32 M | 0.918 | 0.925 |
| lstm_bidir | 2.34 M | 0.914 | 0.921 |
| Wavelet + NN | — | 0.849 | 0.874 |

AUCs come from the [repository README](https://github.com/helme/ecg_ptbxl_benchmarking). The paper gives no parameter counts, so these were counted by building the repository's own model code.

What this means for DELMIR:

- **Architecture barely matters among the top CNNs.** The top four are within their confidence intervals on every task. A ten-model ensemble adds only about 0.004 AUC. The choice of backbone is therefore not where DELMIR's accuracy will come from.
- **The benchmark's native input is 2.5 s × 12 leads at 100 Hz.** Training takes a random 2.5 s crop of the 10 s record. Testing slides 2.5 s windows at half overlap and takes the maximum over windows. 500 Hz gave no significant gain over 100 Hz on PTB-XL's statements (paper, Table VI). That length matches a 3×4 printout's per-lead strip. But PTB-XL's 2.5 s crops are *synchronous* across leads, which a printout's are not (§4).
- **Pretraining rescues tiny label sets.** In the paper's transfer experiment, xresnet1d101 was pretrained on PTB-XL and fine-tuned on ICBEB2018 with only 85 training ECGs. Its AUC fell only about 10% relative to a 64× larger training set. Training from scratch fell much further. At full data size, pretraining gave no gain. DELMIR's later phases, with a few hundred angiography-confirmed labels, sit in exactly this regime.
- **All of these are tiny by phone standards.** Every benchmark model is under 2.5 M parameters, or under 10 MB in fp32.

**Published OMI models** show what accuracy to expect and how others structured the problem. Details are in [baselines-and-omi-models.md §2](ecg-classifier-designs/baselines-and-omi-models.md#2-published-omi-specific-models).

| Study | Model | OMI labels | Input | Result |
|---|---|---|---|---|
| Al-Zaiti 2023, *Nat Med* ([PMC10353937](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10353937/fullTextXML)) | Random forest on 73 median-beat features | 210 derivation / 209 validation | 10 s prehospital, STEMI excluded | AUROC 0.91 internal, **0.87 external** |
| Herman 2024, *EHJ Digit Health* (PMcardio "Queen of Hearts", [PMC10944682](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10944682/fullTextXML)) | Per-lead CNN (≈60 k) + FC fusion (≈150 k), **≈210 k params** | ≈4,260 of 18,616 training ECGs | **3×4, 2.5 s per lead**, digital + digitized | AUC 0.938; external US 0.903; STEMI criteria 0.651 |
| Gustafsson 2026, *Nat Commun* ([article](https://www.nature.com/articles/s41467-026-73023-1), [code](https://github.com/stefan-gustafsson-work/omi)) | 1D ResNet (≈6.9 M) × 5-model ensemble | 1,583 OMIs among 540 k ECGs | 10 s, 8 leads, 400 Hz, + age and sex | C ≥ 0.95 internal; **external 0.83** (OMI-NSTEMI 0.82); LCx vs RCA poorly separated |
| Wu 2022, *Front Cardiovasc Med* ([PMC8960131](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8960131/fullTextXML)) | Small CNN-LSTM, hierarchical | 315 STEMIs (45 LCx) | 10 s, 1 kHz | LAD AUC 0.96; **RCA vs LCx 0.81** |

The pattern:

- **Small networks are enough.** The only 3×4-native OMI model has about 210 k parameters.
- **Expect lower accuracy on STEMI-negative OMI outside the training site.** External AUROC for NSTE-OMI lands around 0.82–0.87.
- **LCx vs RCA is the hard pair** for culprit vessel. Two independent groups found it.

**PTB-XL's own acute-occlusion signal is thin.** This bears on [#10](https://github.com/the-dr-lazy/delmir/issues/10) and [#21](https://github.com/the-dr-lazy/delmir/issues/21). Counted from `ptbxl_database.csv`:

- Any subendocardial-injury statement (INJ\*): 323 records.
- INJ\* or STE\_: 351.
- Infarction stadium I (the acute stage): 166.
- By contrast, thousands of records carry infarct-territory statements: IMI 2,676 and ASMI 2,357.

So PTB-XL can teach infarct-territory morphology at scale, but only a few hundred acute proxies. This is a further reason to treat PTB-XL as pretraining, not as the OMI training set.

## 2. Foundation models and self-supervised pretraining

A *foundation model* is a network pretrained on a very large set of ECGs, with or without labels, so that its internal features transfer to new tasks with few labels.

- **Fine-tuning** retrains the whole network on the new task.
- **Linear probing** freezes the network and trains only a final layer on top.

The most useful source is an **independent head-to-head benchmark**: Al-Masud, Lopez Alcaraz & Strodthoff 2025, "Benchmarking ECG Foundational Models: A Reality Check" ([arXiv 2509.25095](https://arxiv.org/html/2509.25095v2)). It tests eight models under one protocol, on 2.5 s 12-lead segments with test-time averaging, the same setup as §1. Selected rows follow; the full table is in [foundation-models.md §1](ecg-classifier-designs/foundation-models.md#1-comparison-table).

| Model | Params | Pretraining | PTB-XL all (fine-tuned / frozen) | GFLOP per input | Licence | Phone fit |
|---|---|---|---|---|---|---|
| ECG-CPC | 3.8 M | Contrastive predictive coding (S4), 10.7 M ECGs | **0.949** / 0.931 | 1.7 | not stated | small; S4 ops untested in ONNX |
| ECG-JEPA (Kim) | 87.2 M | JEPA, 174 k ECGs | 0.940 / 0.934 | 73.9 | MIT | too heavy; 8 synchronous leads |
| **ECGFounder** | ≈31–34 M (released checkpoint) | **supervised**, 10.8 M ECGs, 150 labels | 0.934 / 0.927 | **0.6** | **MIT** | community ONNX 124 MB fp32 |
| ECG-FM | 90.9 M | wav2vec 2.0 + CLOCS, 1.5 M ECGs | 0.927 / 0.884 | 29.2 | MIT | heavy (1.09 GB checkpoint) |
| **MERL** | **4.6 M** | ECG–report contrastive on **MIMIC-IV-ECG** | 0.925 / 0.909 | 0.9 | **MIT** | small plain ResNet18 |
| HuBERT-ECG (base) | 97.2 M | HuBERT, 9.1 M ECGs | 0.915 / 0.883 | 18.8 | **CC BY-NC** | heavy; "small" 30.5 M exists |
| ST-MEM | 90.3 M | masked autoencoder, 188 k ECGs | 0.908 / 0.910 | 20.9 | **"all rights reserved"** | heavy; licence blocks it |
| supervised S4 (no pretraining) | 2.2 M | — | 0.941 | — | — | baseline |

What this means for DELMIR:

- **On a full labelled set, foundation models barely beat a well-trained small model.** Compare 0.934–0.949 with 0.941 for supervised S4 and 0.925 for xresnet1d101 in §1. **Their value is label efficiency.** Measured against supervised S4, they needed 3.3–9× fewer labels for the same performance. ECG-JEPA was the most label-efficient with 250–1,000 labels, and ECGFounder needed 30–62% of S4's labels. That regime is DELMIR's: a few hundred angiography-confirmed OMIs.
- **The paper's own parameter counts are not reliable here.** The ECGFounder paper gives 76.3 M (Table S11). The benchmark gives 33.8 M, and the size of a community ONNX export ([`ghirani33/ecgfounder-onnx`](https://huggingface.co/ghirani33/ecgfounder-onnx), 124 MB fp32) implies about 31 M. ECGFounder is a RegNet-style 1D CNN ("Net1D") at about 0.6 GFLOP per 2.5 s. That makes it the only strong foundation model that is cheap per pass. But at 124 MB, a five-member ECGFounder ensemble would be about 620 MB, which is too big (§6).
- **MERL** ([arXiv 2403.06659](https://arxiv.org/abs/2403.06659), [code](https://github.com/cheliu-computation/MERL-ICML2024)) is a 4.6 M-parameter ResNet18. It was pretrained on MIMIC-IV-ECG's 800 k ECG–report pairs, the same data DELMIR plans to use. It had the best acute-MI AUROC in the independent benchmark: 0.819 on PTB labels, above ST-MEM 0.809 and ECG-CPC 0.793. Small enough to ensemble.
- **Self-supervised pretraining on MIMIC-IV-ECG alone works.**
  - Weimann & Conrad's ECG-JEPA ([arXiv 2410.13867](https://arxiv.org/html/2410.13867)) pretrained only on MIMIC-IV-ECG matched pretraining on ten datasets. A 3.6 M-parameter ViT-XS reached 0.943 fine-tuned on PTB-XL. It was fine-tuned and evaluated on 2.5 s crops.
  - Mehari & Strodthoff 2022 ([arXiv 2103.12676](https://arxiv.org/abs/2103.12676)) used contrastive predictive coding at 100 Hz on 2.5 s crops. It reached 0.942 against 0.932 supervised, and matched full-data supervised performance with about 62% of the labels.
  - But Weimann released no weights. ECG-CPC's pretraining took three weeks on one L40 GPU. So self-supervised pretraining from scratch on the RX 6600 XT is a later, optional step, not phase 1.
- **MIMIC-IV-ECG v1.0 is open access** ([PhysioNet](https://physionet.org/content/mimic-iv-ecg/1.0/)), under ODbL with no credentialing: about 800 k 10 s 500 Hz ECGs from about 160 k patients. Machine statements are in `machine_measurements.csv`, and cardiologist report text is not included. Supervised pretraining on those machine statements plus PTB-XL's 71 statements is the cheapest form of transfer. It is the same thing ECGFounder did at larger scale, and it needs no GPU-weeks.
- **No foundation model has been evaluated on signals digitized from paper or photos, or on the asynchronous 3×4 layout.** This is an absence after search. The nearest evidence: PatchECG ([arXiv 2508.09165](https://arxiv.org/html/2508.09165v2)) used a *frozen ECGFounder* as a per-patch encoder on simulated 3×4 and other layouts. It reached AUROC 0.872–0.882 on 23 PTB-XL classes, against 0.829–0.835 for its own encoder trained from scratch. That is a hint that ECGFounder features survive the layout. It comes from one preprint.

## 3. Output heads: P(OMI) and a culprit vessel that exists only for an OMI

The model has two outputs sharing one backbone. The *backbone* is the network body that turns the ECG into a feature vector; *heads* are the small final layers that turn the features into outputs. Details: [heads-calibration-uncertainty-deployment.md §1](ecg-classifier-designs/heads-calibration-uncertainty-deployment.md#1-multi-task-heads-with-a-maskedconditional-vessel-loss).

- **OMI head:** one logit with `BCEWithLogitsLoss`. Use it rather than `BCELoss`, which raises an error under mixed-precision autocast ([PyTorch AMP docs](https://docs.pytorch.org/docs/2.14/amp.html)).
- **Vessel head:** three logits (LAD, LCx, RCA) with `CrossEntropyLoss`.
  - The vessel target is set to `ignore_index = -100` for every Not-OMI ECG and for every OMI with a "no vessel" reason from #4 (no culprit, uncertain, multiple systems, left main, graft).
  - Ignored rows contribute no gradient, and the mean is taken over labelled rows only ([docs](https://docs.pytorch.org/docs/2.14/generated/torch.nn.CrossEntropyLoss.html)).
  - **Trap (*measured*):** if every row in a batch is ignored, the mean is NaN. DELMIR's batches will often contain no vessel-labelled OMI, so either sum the loss and divide by `max(n_labelled, 1)`, or skip the term when the batch has none.
- **What the vessel head then means.** Trained only on OMIs with a single native culprit system, its softmax estimates *P(vessel | OMI with a single culprit system)*. This is the chain-rule recipe for hierarchical labels:
  - Chen et al. (MIDL 2019) and Pham et al. ([arXiv 1911.06475](https://arxiv.org/abs/1911.06475)) train child labels only where the parent is positive.
  - They multiply the conditional probabilities at inference.
  - CheXpert's "U-Ignore" ([arXiv 1901.07031](https://arxiv.org/abs/1901.07031)) is the same masked-loss idea.
  - This fits #6: the vessel bars appear only on an OMI call.
- **Option for #23: a fourth class, "OMI without a single culprit system".** It would cover left main, multiple systems and graft, so the head can say so instead of being forced to pick a vessel. CheXpert's "U-MultiClass" is the precedent. "Uncertain" stays ignored either way.
- **The alternative is one softmax over joint classes**, as Gustafsson did: {control, NOMI, OMI-LAD/LM, OMI-LCx, OMI-RCA}, with P(OMI) as the sum of the OMI classes. It is simple. But it cannot use an ECG whose OMI status is known while its vessel is not, which describes most proxy-labelled and MIMIC data. It also lumps left main with LAD, which #4 keeps apart. The masked two-head design uses every label that exists.
- **Auxiliary heads help most where labels are scarce.** Examples are PTB-XL superclasses and infarct territory, masked per source wherever a dataset lacks them. Hughes et al. ([arXiv 1812.00497](https://ar5iv.labs.arxiv.org/html/1812.00497)) found that adding common classes significantly improved rarer ones, but *not* very rare ones (under about 100 examples). An infarct-territory head trained on PTB-XL's thousands of territory statements is the plausible helper for the vessel head. Infarct territory is still not the culprit vessel (GLOSSARY), so it stays an auxiliary output, never a proxy label shown to the user.

## 4. Input: the 3×4 layout, missing leads and missing segments

**What the input actually looks like.**

- A 3×4 printout shows I/II/III at 0–2.5 s, aVR/aVL/aVF at 2.5–5 s, V1–V3 at 5–7.5 s and V4–V6 at 7.5–10 s, plus a 10 s rhythm strip, usually II. This is verified in ECG-Image-Kit's generator code ([`extract_leads.py`](https://raw.githubusercontent.com/alphanumericslab/ecg-image-kit/main/codes/ecg-image-generator/extract_leads.py)).
- Digitizers return a 10 s canvas with NaN outside each lead's window (#14).
- So the classifier gets, per lead, 2.5 s from its own window. At any instant only three leads plus the rhythm strip are observed.
- ECG-Image-Kit also notes that older machines swept segments asynchronously even within a column ([arXiv 2307.01946](https://arxiv.org/abs/2307.01946)).

**Three input designs**, all trainable from synchronous 10 s PTB-XL and MIMIC-IV-ECG records by simulating the layout:

| Design | How | Precedent | Trade-off |
|---|---|---|---|
| **A. Masked canvas** | 12 × 10 s tensor, zeros outside each lead's window, plus 12 presence-mask channels (and the rhythm strip) into an ordinary xresnet1d | Generalises the CinC 2021 winner's zero-fill + presence-indicator recipe ([Nejedly et al.](https://www.cinc.org/archives/2021/pdf/CinC2021-014.pdf)) | Closest to the benchmarks; mostly zeros, so 4× the compute of 2.5 s |
| **B. Per-lead encoder + fusion** | One shared CNN encodes each lead's 2.5 s plus a lead embedding; a small fusion layer combines the 12 (and the rhythm strip) | **Herman 2024 / PMcardio OMI**, the only 3×4-native OMI model (≈210 k params); PatchECG's lead and time embeddings | Asynchrony and missing leads are natural (drop a lead's embedding); lead attribution is clean (§7); a less standard architecture |
| **C. Pseudo-synchronous stack** | Shift every lead's 2.5 s into one common 0–2.5 s window, giving exactly the benchmark's 12 × 2.5 s input | Benchmark input shape; Herman cut 10 s ECGs as "first 2.5 s of limb leads, last 2.5 s of precordial leads" | Reuses benchmark code and pretrained weights as-is; leads come from different beats, so cross-lead timing is lost |

**Missing leads.** The PhysioNet/CinC 2021 Challenge ([moody-challenge.physionet.org/2021](https://moody-challenge.physionet.org/2021/)) tested 12, 6, 4, 3 and 2 leads.

- Dropping to 6, 4 or 3 leads cost about 2% of the median score, and 2 leads about 4% (computed from the official leaderboards).
- Differences between test databases were far larger (up to −41%).
- The winner used **one model for all lead sets**: zero-fill missing leads, drop a random lead set at each training step, and append a lead-presence vector. It scored identically on every lead set.

That recipe transfers directly. Its labels were mostly rhythm and conduction, though, which limb leads show well. OMI depends on territory-specific leads, so expect a larger cost for OMI.

- **ST-MEM is the only foundation model that reports reduced-lead PTB-XL numbers** ([arXiv 2402.09450](https://arxiv.org/abs/2402.09450)): 0.933 with 12 leads, 0.903 with 6, 0.804 with 1.
- **Under ADR 0006, any unreadable lead declines the ECG** (#5). So "missing" in DELMIR mostly means *missing in time* (the layout), not *missing leads*. Training with random lead dropout is still worth doing. It makes the model, and the lead-ablation attribution in §7, more robust.

**Sampling rate is open for OMI.** PTB-XL showed no 100 → 500 Hz gain for its statements. No source tested sampling rate for OMI, whose ST-segment and T-wave detail might benefit. Gustafsson used 400 Hz and Herman 500 Hz. This is for [#22](https://github.com/the-dr-lazy/delmir/issues/22) and the spike.

**Which design wins is a number, not a reading.** The new prototype ticket [#42](https://github.com/the-dr-lazy/delmir/issues/42) measures A, B and C against the synchronous 10 s upper bound on PTB-XL MI and infarct-territory tasks, at 100 and 500 Hz. It also tests ECGFounder initialisation against training from scratch.

## 5. Robustness to digitizer error

**Phone photos are the hardest input in the literature.** In the PhysioNet Challenge 2024 ([moody-challenge.physionet.org/2024](https://moody-challenge.physionet.org/2024/), official score files), the classification winner (AIMED) scored macro-F 0.833 on clean colour scans but **0.644 on clean phone photos**. The digitization winner's SNR was **−1.07 dB on clean phone photos**, against 4.9 on colour scans. "Acute MI" was the weakest class in that challenge.

**Digitized signals cost accuracy, and retraining on them recovers part of it.** ECGtizer ([arXiv 2412.12139](https://arxiv.org/abs/2412.12139)) trained a classifier on original signals. It reached 0.94 accuracy on the originals, but only 0.85 on the best digitizer's output and 0.47 on the worst. Retraining on digitized data closed part of the gap, not all.

**What the sources support.**

1. **Round-trip training.**
   - Render PTB-XL and MIMIC-IV-ECG with ECG-Image-Kit as 3×4 + II, with photo-like distortions. Its `--mask_unplotted_samples` option writes the matching NaN-masked signal.
   - Digitize the renders with DELMIR's chosen digitizer ([#25](https://github.com/the-dr-lazy/delmir/issues/25)).
   - Train and fine-tune on that output.

   CinC 2024 teams and PatchECG did this in effect.
2. **Time-series augmentations** matching digitizer error: per-lead amplitude rescaling, lead dropout, cut-outs and random slices (the CeZIS signal model, CinC 2024 paper 231). ECGtizer found peak-amplitude errors matter most.
3. **Evaluate on real captures.** ECG-Image-Database is the Challenge's hidden set, now public on Kaggle: 35–37 k real scans and phone photos with their WFDB signals. Then use DELMIR's own photos (#38).

**Calibrate on digitized data too** (§6).

No source injects calibrated "digitizer-like" noise straight into signals and measures the gain. The round trip through the real digitizer is the safer, evidence-backed path.

## 6. Calibration and uncertainty

**Calibration.** A *calibrated* P(OMI) means that among ECGs given 30%, about 30% are OMIs. Modern networks are usually over-confident (Guo et al. 2017, [arXiv 1706.04599](https://arxiv.org/abs/1706.04599)). Details: [heads-calibration-uncertainty-deployment.md §2](ecg-classifier-designs/heads-calibration-uncertainty-deployment.md#2-calibration).

- **Use temperature or Platt scaling.** Temperature scaling divides the logit by one learned number T. Platt scaling learns a slope and an intercept. Both are fitted on held-out data after training. Neither changes AUC.
  - Guo found temperature scaling beat every richer method.
  - Isotonic regression needs roughly 1,000 or more calibration samples ([scikit-learn](https://scikit-learn.org/stable/modules/calibration.html)), more than DELMIR's OMI calibration set will have.
- **Calibrate on deployment-like data, not clean PTB-XL.** Ovadia et al. 2019 ([arXiv 1906.02530](https://arxiv.org/abs/1906.02530)) found that temperature scaling fitted on in-distribution validation data can *worsen* calibration under dataset shift. Phone photos of ED printouts are a large shift from PTB-XL. So the calibration set must be digitized ECGs from the intended-use population, kept apart from training and test.
- **Prevalence shift is an intercept.** If the training mix has a different OMI prevalence from the ED, Saerens et al. 2002 ([*Neural Computation*](https://dipot.ulb.ac.be/dspace/bitstream/2013/68391/1/Decaestecker_NeuralComp02.pdf)) gives the correction. In the binary case it reduces to `logit + log-odds(π_new) − log-odds(π_train)`, which composes with temperature: `σ(z/T + Δb)`. Sadatsafavi et al. ([arXiv 2110.08648](https://arxiv.org/abs/2110.08648)) warn that this fixed odds shift under-corrects when predicted risks are widely spread. So fit the intercept on local data where it exists.
- **Order of operations for [#24](https://github.com/the-dr-lazy/delmir/issues/24):**
  1. Train.
  2. Quantise or export, if used.
  3. Fit T (and Δb) on the ensemble's averaged logit.
  4. Only then freeze the rule-out and rule-in thresholds.

  Re-fit after any re-export. Report ECE (15 bins) with a reliability diagram, plus Brier score and NLL. Brier score and NLL are proper scoring rules; ECE is not.

**Uncertainty for the confidence word.** Details: [heads-calibration-uncertainty-deployment.md §3](ecg-classifier-designs/heads-calibration-uncertainty-deployment.md#3-uncertainty).

- **Deep ensemble of five.** Train M independently initialised copies on the full data; average their probabilities; their spread is the model's uncertainty (Lakshminarayanan et al. 2017, [arXiv 1612.01474](https://arxiv.org/abs/1612.01474), recommends M = 5).
  - Ovadia 2019: ensembles performed best across metrics and were the most robust to dataset shift. MC dropout came second. Returns diminish past five members.
  - The PTB-XL benchmark used a ten-model ensemble's variance as its uncertainty, and it tracked annotator disagreement.
  - In ECGs, Vranken et al. 2021 ([*EHJ Digit Health*](https://academic.oup.com/ehjdh/article/2/3/401/6311566)) found ensemble-based methods among the best. Referring the most uncertain 25–75% raised accuracy sharply (e.g. 0.82 → 0.96). Higher uncertainty tracked lower agreement between cardiologists.
- **MC dropout does not survive ONNX Runtime by default (*measured*).** PyTorch's exporter keeps the Dropout node in training mode. But ONNX Runtime's default *basic* graph optimisation includes "Dropout Elimination" ([ORT docs](https://onnxruntime.ai/docs/performance/model-optimizations/graph-optimizations.html)), so five runs gave identical outputs. Making the dropout mask an explicit model input works, but it adds a non-standard contract for a method that is second-best anyway. **Prefer the ensemble.**
- **Cost.** Five 1–2 M-parameter CNNs are 5 × 4–8 MB in fp32 and five forward passes (§8). Five ECGFounders would be about 620 MB. If ECGFounder wins the spike, an ensemble needs a smaller member, or shared frozen features with five heads, which gives less diversity. That trade-off is for #23.
- **The confidence word** combines the ensemble's spread with signal quality (#6). Ovadia's warning applies: uncertainty quality degrades as shift grows, whatever the method. That is why a declined ECG never reaches the classifier (ADR 0006), and why the cut-offs of the confidence word are set on digitized data (#24).

## 7. Lead attribution on the phone

**Integrated gradients cannot run in ONNX Runtime (*measured*).** Integrated gradients (Sundararajan et al. 2017, [arXiv 1703.01365](https://arxiv.org/abs/1703.01365)) needs gradients. ONNX Runtime inference has none, and a module that computes gradients in its forward pass would not export with either PyTorch exporter.

ORT's separate on-device-training package exists for Android but not for React Native. Its last Maven release, 1.19.2 (September 2024), is old.

**Use lead ablation instead.** It needs forward passes only.

- Run one batch of 13 inputs: the ECG, plus 12 copies with one lead each replaced by the baseline. Lead i's attribution is P(OMI) minus P(OMI) with lead i removed.
- This is Captum's `FeatureAblation` with a per-lead feature mask ([Captum](https://captum.ai/api/feature_ablation.html)).
- It is faithful only if the model has seen missing leads in training, hence the lead dropout in §4.
- With design B (§4), "remove lead i" means dropping its embedding, which the model is trained to handle.
- **Cost (*measured*, desktop CPU, one thread, xresnet1d101 at 12 × 1000):** 2.8 ms for one pass, 35 ms for the batch of 13.

**Check it offline.** Use Captum's integrated gradients summed per lead as the offline reference, on a held-out set, to check that on-device ablation ranks leads similarly. Do a weight-randomisation sanity check once.

Arends et al. 2026 ([*EHJ Digit Health*](https://researchinformation.umcutrecht.nl/en/publications/signal-or-noise-evaluating-commonly-used-attribution-methods-for-/)) compared 12 attribution methods on ECGs. They found low agreement between methods and advise task-specific sanity checks. Lead attribution should be read as "what drove the model", which is how #6 and the glossary already frame it.

## 8. Size and latency after ONNX export

Measured from a re-implementation of the benchmark's xresnet1d (*measured*; FLOPs = 2 × multiply–accumulates):

| Model | Params | fp32 | 12 × 250 (2.5 s @ 100 Hz) | 12 × 1000 (10 s @ 100 Hz) | 12 × 5000 (10 s @ 500 Hz) |
|---|---|---|---|---|---|
| xresnet1d50, kernel 5 | 0.95 M | 3.8 MB | 0.05 GFLOP | 0.21 GFLOP | 1.05 GFLOP |
| xresnet1d101, kernel 5 | 1.87 M | 7.5 MB | 0.08 GFLOP · 0.8 ms | 0.32 GFLOP · 2.8 ms | 1.62 GFLOP · 13.5 ms |
| xresnet1d101, kernel 25 (500 Hz variant) | 4.64 M | 18.6 MB | — | — | 4.24 GFLOP |

The latencies are desktop ONNX Runtime CPU, one thread. No primary source gives phone latency for a 1D ECG CNN.

**Worst case per reading:** 5 ensemble members × 13 ablation passes at 12 × 1000 is 65 forward passes, about 180 ms on desktop. That is an estimated 0.5–2 s on a mid-range phone, assuming a phone core is 3–10× slower. This estimate is unverified; the device prototype [#40](https://github.com/the-dr-lazy/delmir/issues/40) measures the real number. The worst case is acceptable next to the digitizer's seconds (#16), and design C or A at 100 Hz is far cheaper.

**Export and runtime facts** (details in [heads-calibration-uncertainty-deployment.md §5](ecg-classifier-designs/heads-calibration-uncertainty-deployment.md#5-onnx-export-quantisation-android-runtime)):

- **Export.** Since PyTorch 2.9 the dynamo exporter is the default ([docs](https://docs.pytorch.org/docs/2.14/onnx.html)). Pass `external_data=False` to get one self-contained `.onnx`. Conv1d exports as plain ONNX `Conv`, and BatchNorm is folded in (*measured*).
- **Quantisation.**
  - Static int8 QDQ shrank xresnet1d101 from 7.96 to 2.39 MB and cut latency from 3.1 to 1.9 ms on desktop. Only 69 of 103 convolutions were quantised (*measured*).
  - #16 recommends fp32 for v1. At a few MB per model, size is no reason to quantise.
  - Quantisation can wait. If it is ever used, re-check accuracy and re-fit calibration.
  - fp16 is pointless on the phone: ORT's CPU build has no float16 kernels ([docs](https://onnxruntime.ai/docs/performance/model-optimizations/float16.html)).
- **Execution providers.** XNNPACK and NNAPI accelerate only 2D convolutions, and NNAPI is deprecated in Android 15. The CPU execution provider is the target, as #16 concluded. Rewriting the CNN with `Conv2d (1, k)` kernels to use XNNPACK is possible but unbenchmarked.

## 9. Training on the 8 GB RX 6600 XT

How to run PyTorch on this card is settled by #8, and #41 proves it on the host. For model design the facts are:

- **Memory is not a constraint** for these models (*measured*).
  - xresnet1d101 activations are about 3.7 MB per sample at 12 × 250 and 73 MB at 12 × 5000.
  - That puts batch 64 at 10 s / 500 Hz at about 4.7 GB in fp32, or 2.3 GB with fp16 autocast. Parameters plus Adam state are about 30 MB.
  - Fine-tuning ECGFounder or MERL fits easily; the benchmark measured 187 MB and 86 MB at batch 64.
  - Pretraining a ViT-B from scratch is the one expensive case.
- **The first epoch is slow.** MIOpen compiles and searches kernels on first use for each new tensor shape, then caches them in `~/.cache/miopen` ([MIOpen docs](https://rocm.docs.amd.com/projects/MIOpen/en/latest/how-to/find-and-immediate.html)). Keep input length and batch size fixed (fixed-length crops, `drop_last=True`) and persist the cache.
- **Mixed precision.** Use `torch.autocast` with fp16 and `GradScaler`, with `BCEWithLogitsLoss` and `cross_entropy`. RDNA2 has no matrix cores, so fp16 speed-ups may be modest (unverified).
- **Ensembles train one member at a time.** Five 1–2 M-parameter members at 100 Hz train comfortably in sequence.

## 10. What #23 needs to decide, and what this research recommends

| Question in #23 | Recommendation from the evidence | Confidence |
|---|---|---|
| Baseline architecture | xresnet1d101 or inception1d from the PTB-XL benchmark; Herman's ≈210 k per-lead CNN if design B wins | High: established, and architecture matters little |
| Pretraining | Supervised on PTB-XL's 71 statements + MIMIC-IV-ECG machine statements; then try ECGFounder or MERL initialisation; self-supervised pretraining from scratch later and optional | Medium: label-efficiency gains are documented, but not on 3×4 or digitized input |
| OMI and vessel heads | Sigmoid OMI head + LAD/LCx/RCA softmax with `ignore_index`, guarded against all-ignored batches; optional 4th "OMI, no single culprit system" class; masked auxiliary infarct-territory and superclass heads | High for the mechanism; the 4th class is a domain call |
| Input and missing segments | A, B or C from §4, chosen by spike #42; lead dropout + presence mask in every case | Low until measured |
| Digitizer robustness | Round-trip through DELMIR's digitizer + time-series augmentations; evaluate on ECG-Image-Database and own photos | Medium |
| Calibration | Temperature/Platt on the ensemble mean logit, on held-out digitized intended-use ECGs; intercept for prevalence; thresholds frozen last | High |
| Uncertainty | Deep ensemble, M = 5; not MC dropout (ORT removes it) | High |
| Lead attribution | On-device lead ablation (13-batch per member); offline integrated gradients as the check | High for feasibility; faithfulness needs the sanity check |
| Size and latency | Five 1–2 M-param fp32 members, a few MB each, ≲ 2 s worst case on a phone (estimate); confirm in #40 | Medium |

## Open questions and unverified points

- **No primary source exists for these:**
  - performance of any foundation model on the asynchronous 3×4 layout or on photo-digitized signals;
  - sampling rate for OMI;
  - phone latency of 1D ECG CNNs;
  - gains from digitizer-like noise injected straight into signals.
- **ECGFounder's parameter count conflicts:** 76.3 M in the paper, 33.8 M in the benchmark, about 31 M implied by the ONNX size.
- **Not read:**
  - Gustafsson's per-vessel AUCs (in its supplementary Table 2);
  - Herman's digital-vs-digitized breakdown (supplement);
  - Wu 2022's exact hierarchical staging beyond the abstract;
  - Vranken's ensemble size.
- **Known only from search snippets:**
  - Singstad et al., a foundation model fine-tuned on about 17 k Norwegian ECGs with 1,338 OMIs, AUROC 0.93;
  - the Open-ECG-Digitizer photo SNRs.
