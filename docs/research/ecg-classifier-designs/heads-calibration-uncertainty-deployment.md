# DELMIR classifier: heads, calibration, uncertainty, attribution, deployment, training (research notes)

Researched 2026-10-21. Each claim is followed by its source. Labels used:
- **[verified]**: read in the primary source.
- **[measured]**: I ran it locally (torch 2.13.0, onnx 1.23.2, onnxruntime 1.27.1, CPU only, AMD Ryzen 9 7950X3D desktop, not a phone). The scripts are in [`scripts/`](scripts/): `xres_count.py`, `onnx_check.py`, `dropout_inspect.py`, `dropout_noopt.py`, `grad_export.py`, `qdq_time.py`.
- **[unverified]**: background knowledge or secondary sources only.
- **[inference]**: my own reasoning from the verified facts.

---

## 1. Multi-task heads with a masked/conditional vessel loss

### PyTorch mechanics
- `nn.CrossEntropyLoss(ignore_index=-100, reduction='mean')` are the defaults. An ignored target "does not contribute to the input gradient", and the mean is taken over non-ignored targets only. The denominator carries the indicator 1{y_n ≠ ignore_index}. "ignore_index is only applicable when the target contains class indices" (not probability targets). Targets must be `long`. [verified] https://docs.pytorch.org/docs/2.14/generated/torch.nn.CrossEntropyLoss.html
- The docs say nothing about how `label_smoothing` interacts with `ignore_index`. [verified absence, same URL]
- **Gotcha** [measured]: if *every* target in a batch is `-100`, `reduction='mean'` returns **NaN**, while `reduction='sum'` returns 0. With some targets ignored, the loss equals the mean over the labelled rows exactly, and ignored rows get zero gradient. In DELMIR most batches can contain no vessel-labelled OMI, so guard against it. Either use `reduction='sum'` divided by `max(n_labelled, 1)`, or skip the vessel term when `n_labelled == 0`. A weighted sampler that guarantees some OMIs per batch also works.
- Recommended loss [inference]: `L = BCEWithLogits(omi_logit, y_omi) + λ · CE(vessel_logits, y_vessel)`. Set `y_vessel = -100` for Not-OMI and for OMIs with a "no vessel" reason (left main, multiple systems, graft, uncertain). Use `BCEWithLogits` rather than `BCELoss`, because `binary_cross_entropy`/`BCELoss` "raise an error in autocast-enabled regions" while `binary_cross_entropy_with_logits` is "safe to autocast". [verified] https://docs.pytorch.org/docs/2.14/amp.html

### Getting P(vessel | OMI) at inference
- Trained this way, the vessel head's softmax estimates **P(vessel | OMI, single identifiable culprit in LAD/LCx/RCA)**, because it never sees Not-OMI ECGs or "no vessel" OMIs. Show it only when the call is OMI, or show the joint P(OMI)·P(v|OMI). [inference]
- Precedent for the chain rule: Pham et al. train on the subset where the parent label is positive, so each child output is "the conditional probability that this label is positive given its parent being positive". At inference "the unconditional probability … should be computed by multiplying all conditional probabilities produced by the CNN". They then fine-tune only the last FC layer on the full data to improve the parent predictions. Pham, Le, Tran, Ngo, Nguyen, "Interpreting chest X-rays via CNNs that exploit hierarchical disease dependencies and uncertainty labels", *Neurocomputing* (MIDL 2020 short version). [verified] https://arxiv.org/abs/1911.06475
- The original recipe is Chen et al., "Deep hierarchical multi-label classification of chest X-ray images", MIDL 2019, pp. 109–120. A DenseNet-121 was trained on the subset where all parent nodes are positive, then fine-tuned on the whole data. [verified via Pham's description; Chen not read directly]
- Precedent for the masked loss: CheXpert's **U-Ignore** "optimize[s] the sum of the masked binary cross-entropy losses over the observations", masking uncertain labels. Alternatives are U-Zeros/U-Ones (map uncertain labels to 0 or 1), U-SelfTrained, and U-MultiClass (uncertain as its own class). The finding was that "different uncertainty approaches are useful for different pathologies". Irvin et al., AAAI 2019. [verified] https://arxiv.org/abs/1901.07031 , https://ar5iv.labs.arxiv.org/html/1901.07031
  - DELMIR analogue [inference]: U-Ignore corresponds to `ignore_index`. U-MultiClass corresponds to adding a 4th vessel class, "other/none", for left main, multi-vessel and graft OMIs, so the head can say "not a single-vessel culprit". Keep "uncertain" ignored either way.
- ECG culprit-vessel precedent: Wu et al., Front. Cardiovasc. Med. 2022 (doi 10.3389/fcvm.2022.797207). In a search summary: STEMI AUC 0.99 (CNN-LSTM), LAD AUC 0.96, RCA vs LCx AUC 0.81, roughly equal to cardiologists. I could not fetch the full text, so how the culprit task was staged is unknown. [unverified] https://www.frontiersin.org/journals/cardiovascular-medicine/articles/10.3389/fcvm.2022.797207/full
- A 2023 single-centre CNN on 384 primary-PCI STEMI patients reported 83.7% overall accuracy (CWT input) and LCx sensitivity of about 56%. [unverified, search snippet] https://ieeexplore.ieee.org/document/9976059

### Auxiliary heads as regularisers
- Hughes et al., "Using Multitask Learning to Improve 12-Lead ECG Classification" (arXiv 1812.00497; UCSF, 41,522 ECGs, 24 labels): "the addition of common classes can significantly improve CNN performance on rarer classes". Gains were larger for rarer classes, but **no similar gain for very rare classes (<100 examples)**. [verified] https://ar5iv.labs.arxiv.org/html/1812.00497
- Label masking across datasets with different label sets was used in PhysioNet/CinC 2021 entries. [unverified, search snippet] https://physionet.org/files/challenge-2021/1.0.3/papers/CinC2021-019.pdf
- A CinC 2025 paper trains MI detection, localisation (anterior/lateral/inferior/septal) and staging jointly on PTB-XL+. This is the closest precedent for an "infarct territory" auxiliary head. [unverified, search snippet] https://cinc.org/2025/Program/accepted/440.html
- [inference] Practical design: auxiliary heads for PTB-XL superclasses (NORM/MI/STTC/CD/HYP) and MI-location subclasses, masked per sample with `ignore_index` or per-label BCE masks wherever a dataset lacks them. Weight them with a small λ, drop them at export, or keep them as hidden outputs. Expect a benefit for vessel only if the territory labels exist for many more ECGs than the vessel labels do. That holds for PTB-XL, but PTB-XL territory is not angiographic culprit.

---

## 2. Calibration

### Core paper: Guo et al. 2017, "On Calibration of Modern Neural Networks" (ICML 2017)
Source for all bullets: [verified] https://arxiv.org/abs/1706.04599 (full text read)
- "modern neural networks, unlike those from a decade ago, are poorly calibrated". Depth, width, weight decay and BatchNorm all affect calibration. The paper finds "increased model capacity and lack of regularization are closely related to model miscalibration".
- The NLL/accuracy disconnect: NLL overfits after the learning-rate drop while error keeps improving, i.e. the network can "overfit to NLL without overfitting to the 0/1 loss".
- **ECE** partitions predictions into M equally spaced confidence bins and takes the weighted average |acc(B_m) − conf(B_m)|. Tables use **M = 15 bins**. **Reliability diagrams** plot accuracy against confidence per bin. They "do not display the proportion of samples" per bin, so the paper shows confidence histograms with them.
- **Platt scaling**: learn scalar a, b and output q = σ(a·z + b), "optimized using the NLL loss over the validation set". The network's parameters stay fixed. For a binary sigmoid head like OMI, temperature scaling is Platt scaling with b = 0. [inference]
- **Temperature scaling**: q = max_k softmax(z/T)^(k), with "T is optimized with respect to NLL on the validation set". Because T does not change the argmax, "temperature scaling does not affect the model's accuracy". It beat histogram binning, isotonic regression, BBQ, and vector/matrix scaling on vision tasks: "network miscalibration is intrinsically low dimensional".
- Typical uncalibrated ECE was 4–10%.

### Other methods
- scikit-learn 1.9.1 docs [verified] https://scikit-learn.org/stable/modules/calibration.html
  - Isotonic "is more prone to overfitting, especially on small datasets". It performs as well as or better than sigmoid "when there is enough data (greater than ~ 1000 samples)".
  - Sigmoid (Platt) is "most effective for small sample sizes". The page warns the logistic model "works best if the calibration error is symmetrical", which can fail for highly imbalanced problems.
  - Fit the calibrator on data disjoint from training data. For an already-trained model, use `CalibratedClassifierCV(FrozenEstimator(model))`.
  - Reliability diagrams correspond to `calibration_curve`. `method="temperature"` exists.
  - Brier/log-loss mix calibration and resolution, so "A lower Brier loss … does not necessarily mean a better calibrated model".
- Original sources: Platt (1999/2000), "Probabilistic outputs for SVMs…"; Zadrozny & Elkan (KDD 2002) for isotonic and multiclass one-vs-rest. [unverified: originals not read; dates vary across citing sources]
- [inference] For DELMIR, the OMI calibration set will probably be a few hundred ED ECGs at most. Use **temperature or Platt** (1–2 parameters), not isotonic.

### Brier score and proper scoring rules
- Ovadia et al., eq. 1: BS = |Y|⁻¹ Σ_y (p(y|x) − δ(y−y_n))². It decomposes as uncertainty − resolution + reliability. "Brier score is insensitive to predicted probabilities associated with in/frequent events". NLL and Brier are proper scoring rules, ECE and entropy are not. [verified] https://arxiv.org/abs/1906.02530

### Calibration under dataset shift: Ovadia et al., NeurIPS 2019, "Can You Trust Your Model's Uncertainty?"
Source for all bullets: [verified] https://arxiv.org/abs/1906.02530 (full text read)
- Take-homes (Sec. 5):
  - Uncertainty quality "consistently degrades with increasing dataset shift regardless of method".
  - Better calibration on the i.i.d. test set "does not usually translate to better calibration under dataset shift".
  - Temperature scaling on i.i.d. validation data is well calibrated in-distribution and under small shift, "but is significantly outperformed by methods that take epistemic uncertainty into account as the shift increases".
  - "Deep ensembles seem to perform the best across most metrics and be more robust to dataset shift", and "relatively small ensemble size (e.g. M = 5) may be sufficient".
- Criteo text: "temperature scaling has a worse Brier score than Vanilla indicating that post-hoc calibration on the validation set actually harms calibration under dataset shift".
- [inference] For DELMIR (PTB-XL/other sources moving to phone photos of ED printouts): calibrate on data that looks like deployment, i.e. digitised photos from the target population, not on clean PTB-XL. Expect calibration to drift anyway. An ensemble mitigates this but does not fix it.

### Prevalence (label) shift and recalibrating the intercept
- Saerens, Latinne & Decaestecker, "Adjusting the Outputs of a Classifier to New a Priori Probabilities: A Simple Procedure", *Neural Computation* 14(1):21–41, 2002 (doi 10.1162/089976602753284446). Under the assumption that within-class densities p(x|ω) do not change, eq. 4 is p(ω_i|x) = [p(ω_i)/p_t(ω_i)]·p_t(ω_i|x) / Σ_j [p(ω_j)/p_t(ω_j)]·p_t(ω_j|x). The paper calls this "simply the a posteriori probabilities in the conditions of the training set … weighted by the ratio of the new priors to the old priors". It also gives an EM procedure to estimate unknown new priors and a test for whether priors changed. [verified] https://dipot.ulb.ac.be/dspace/bitstream/2013/68391/1/Decaestecker_NeuralComp02.pdf
  - Binary form [inference, follows algebraically from eq. 4]: **logit_new = logit_old + log(π_new/(1−π_new)) − log(π_train/(1−π_train))**. This is a pure intercept shift, so it composes with temperature: p = σ(z/T + Δb).
- Recalibration-in-the-large means fitting only an intercept, with the logit as offset, on local labelled data. Sadatsafavi, Tavakoli & Safari 2021 (arXiv 2110.08648) warn that a fixed odds-ratio correction based on prevalence ignores the non-collapsibility of the OR and "under-corrects predicted risks, especially when predicted risks are more dispersed". They propose an approximate fix using the mean and variance of predicted risks. [verified abstract] https://arxiv.org/abs/2110.08648
- [inference] DELMIR consequence: OMI prevalence differs a lot between a training mix (curated OMI-rich sets, PTB-XL) and an undifferentiated ED. The frozen OMI/Indeterminate/Not-OMI thresholds are only meaningful on the probability scale *after* the final intercept or temperature is fixed. Freeze thresholds last, and record the assumed prevalence π_new alongside them.

### ECG-specific calibration
- I found no ECG-specific temperature-scaling or calibration paper via search. [unverified absence]
- Vranken et al. (below) evaluated calibration of uncertainty methods on ECGs.

---

## 3. Uncertainty

### Methods
- **Deep ensembles**: Lakshminarayanan, Pritzel, Blundell, NIPS 2017. Sources: [verified] https://arxiv.org/abs/1612.01474 (full text read)
  - The recipe is a proper scoring rule as loss, optional adversarial training, and M independently trained nets. "Recommended default values are M = 5".
  - "random initialization of the NN parameters, along with random shuffling of the data points, was sufficient". "bagging deteriorated performance".
  - Each net trains on the entire dataset. Predictions combine as the uniform mixture p(y|x) = M⁻¹ Σ p_θm(y|x).
- **MC dropout**: Gal & Ghahramani, ICML 2016, "Dropout as a Bayesian Approximation". Dropout training is framed as "approximate Bayesian inference in deep Gaussian processes", which gives uncertainty from an existing dropout net at test time by sampling. [verified abstract] https://arxiv.org/abs/1506.02142
- **Ovadia 2019 verdict**: "ensembles consistently perform best across metrics and dropout consistently performed" second-best in most settings. Ensemble M = 10 in the main experiments. Diminishing returns past 5 ensemble members and past 5 dropout samples (App. D). "Last layer Dropout exhibits less uncertainty on shifted and OOD datasets than Dropout". [verified] https://arxiv.org/abs/1906.02530
- **Compute/storage (Ovadia Table S1)**: Vanilla m/m, Dropout mk compute with m storage, Ensemble mk compute with mk storage, LL-Dropout m + d(k−1) compute. [verified, same source]
- Ashukha et al., ICLR 2020, "Pitfalls of In-Domain Uncertainty Estimation and Ensembling": "many sophisticated ensembling techniques are equivalent to an ensemble of only few independently trained networks". The paper introduces the deep-ensemble-equivalent (DEE) score. [verified abstract] https://arxiv.org/abs/2002.06470

### ECG papers using uncertainty for referral
- Vranken et al., "Uncertainty estimation for deep learning-based automated analysis of 12-lead electrocardiograms", *Eur Heart J – Digital Health* 2(3):401–415, 2021. [verified] https://academic.oup.com/ehjdh/article/2/3/401/6311566
  - Methods: MC dropout, VI, ensemble, snapshot ensemble (epistemic); auxiliary output and Bayesian decomposition (aleatoric); plus combinations.
  - Data: UMCU-Triage (316,987 ECGs), UMCU-Diagnose (194,880), CPSC2018 (6,877).
  - Best: "the combination of variational inference with Bayesian decomposition and ensemble with auxiliary output outperformed the other methods". MCD+AUX and SSE+AUX were not recommended because of over-confidence.
  - Referral simulation removed the 25/50/75% most uncertain cases. Accuracy for ENS+AUX: Triage 0.82→0.87→0.93→0.96; Diagnose 0.92→0.98→0.99→1.00; CPSC 0.73→0.77→0.83→0.95.
  - Higher uncertainty went with lower inter-cardiologist agreement (P < 0.001).
  - Ensemble size and MC sample count were not seen in the parts I read (likely in the supplement). [unverified]
- Strodthoff et al., "Deep Learning for ECG Analysis: Benchmarks and Insights from PTB-XL" (IEEE JBHI 2021, arXiv 2004.13701). Model uncertainty was the variance of **an ensemble of 10 identical models** with different random initialisations (no adversarial step, no MC dropout). Plotting it against the annotator likelihood showed "the expected monotonic behavior". [verified] https://ar5iv.labs.arxiv.org/html/2004.13701

### MC dropout through ONNX: dropout disappears, and here is how to keep it
- The ONNX `Dropout` op (opset ≥ 12) has optional inputs `ratio` (default 0.5) and `training_mode`. "If it is false, ratio is ignored and the operation mimics inference mode". The output is `scale * data * mask` with scale = 1/(1−ratio). [verified] https://onnx.ai/onnx/operators/onnx__Dropout.html
- `torch.onnx.export(..., training=...)` is "Deprecated option. Instead, set the training mode of the model before exporting." [verified] https://docs.pytorch.org/docs/2.14/onnx_export.html
- ORT's *Basic* graph optimisations include **"Dropout Elimination"**, and Basic is on by default (as is Conv+BatchNorm fusion). [verified] https://onnxruntime.ai/docs/performance/model-optimizations/graph-optimizations.html
- **What I measured** (toy net: eval mode except the `nn.Dropout` submodule in `.train()`):
  - The dynamo exporter (default) keeps a `Dropout` node with `ratio=0.5` and `training_mode=True` as constants.
  - **ORT at default optimisation still returns identical outputs on 5 runs**, and the log shows the `training_mode` initializer removed.
  - With `GraphOptimizationLevel.ORT_DISABLE_ALL` the outputs are stochastic. `ORT_ENABLE_BASIC` is already deterministic.
  - The TorchScript exporter (`dynamo=False`) dropped the Dropout node entirely.
  - This matches community reports that exported dropout gave identical outputs. [unverified source] https://discuss.pytorch.org/t/onnx-export-with-dropout-layer-training-rest-eval/117826
- **Robust option** [measured]: make the dropout mask an explicit model input, `y = head(feat * mask / (1−p))`, and generate Bernoulli masks in JS/TS. This exported to `Mul` nodes and gave different outputs per mask under default ORT optimisation. It is also reproducible, since the seed lives in the app.
  - [inference] Put the mask only on the penultimate features, so the backbone runs once. A batch of T masks on the head is then nearly free, but this is "last-layer dropout", which Ovadia found weaker under shift. Masks inside the backbone cost T full forwards.
- [inference] **Recommendation: an ensemble of M = 5 small models** (e.g. xresnet1d50, ~1M params each) over MC dropout. It is the best method in Ovadia, needs no export tricks, has storage of only 5× a few MB (see §5), and costs 5 forwards. The ensemble's std/mutual information of P(OMI) feeds the High/Moderate/Low word together with signal quality. Calibrate (T or Platt) on the **averaged** ensemble output.

---

## 4. Lead attribution

### Integrated Gradients
Sundararajan, Taly, Yan, "Axiomatic Attribution for Deep Networks" (arXiv 1703.01365; ICML 2017 by common citation, not stated on the arXiv page). Source: [verified] https://arxiv.org/abs/1703.01365 (full text read)
- Satisfies Sensitivity and Implementation Invariance.
- **Completeness**: "the attributions add up to the difference between the output of F at the input x and the baseline x′".
- Choose the baseline so that "the prediction at the baseline is near zero". "between 20 and 300 steps are enough to approximate the integral (within 5%)". Developers should check that the attributions approximately sum to F(x) − F(x′).
- **Per-lead IG** [inference]: for input (1, 12, T), `attr.sum(dim=-1)` gives 12 numbers whose total is about F(x) − F(baseline), by completeness. Attribute the **OMI logit**, not the probability, and use a zero (flat-line) baseline after baseline-wander removal. Signed sums can cancel within a lead, so report sum(attr) and optionally sum(|attr|). IG is linear in F, so the attribution of an ensemble mean equals the mean of member attributions.
- **Captum API** [verified] https://captum.ai/api/integrated_gradients.html
  - `IntegratedGradients(forward_func, multiply_by_inputs=True)`.
  - `.attribute(inputs, baselines=None, target=None, additional_forward_args=None, n_steps=50, method='gausslegendre', internal_batch_size=None, return_convergence_delta=False)`.

### Can IG run on the phone?
- ONNX Runtime inference has no autograd. **Exporting a module whose forward calls `torch.autograd.grad` failed with both exporters** [measured]:
  - dynamo: `TorchExportError` at the torch.export step.
  - TorchScript: "Cannot insert a Tensor that requires grad as a constant".
- ORT on-device training can build gradient graphs (`generate_artifacts`: training model = base + loss + gradient graph). It needs a separate training build/package (`--enable_training_apis`). Maven `onnxruntime-training-android` was last seen at 1.19.2 (Sep 2024), and the React Native package does not expose it. [partly verified] https://onnxruntime.ai/docs/get-started/training-on-device.html , https://mvnrepository.com/artifact/com.microsoft.onnxruntime/onnxruntime-training-android [status unverified]
- **Forward-only alternative: lead ablation/occlusion** [inference, measured cost]. Run one forward pass on a batch of 13: the original plus 12 copies, each with one lead replaced by the baseline. Lead importance is Δ_i = F(x) − F(x with lead i zeroed). This is Captum's `FeatureAblation` with a `feature_mask` that groups each lead's samples ("Passing a feature mask, allows grouping features to be ablated together"; zero baseline by default; `perturbations_per_eval` batches ablations). [verified] https://captum.ai/api/feature_ablation.html ; `Occlusion` with `sliding_window_shapes=(1, T)` is equivalent. https://captum.ai/api/occlusion.html
  - Measured cost on desktop ORT CPU, single thread, xresnet1d101 at 12×1000: batch 1 = 2.8 ms, batch 13 = 35 ms. Phone will be slower (see §5).
  - Caveat [inference]: zeroing a lead puts the input off-distribution, and Δ_i does not sum to F(x) − F(0) the way IG does. A model trained with random lead dropout as augmentation makes ablation more faithful.
- [inference] Precomputing IG is not possible for unseen ECGs. Python IG can still serve as the *offline* reference to validate that on-device lead ablation ranks leads similarly.

### ECG attribution papers
- Strodthoff 2021 used ε-LRP (ε = 0.1) on a ResNet and showed PVC relevance "located at the extra systole across all leads" and pacemaker spikes for PACE. It was qualitative. [verified] https://ar5iv.labs.arxiv.org/html/2004.13701
- Bender et al., "Analysis of a Deep Learning Model for 12-Lead ECG Classification Reveals Learned Features Similar to Diagnostic Criteria", IEEE JBHI 2023 (doi 10.1109/JBHI.2023.3271858; arXiv 2211.01738).
  - They averaged relevance per class, **per lead**, and per average beat.
  - Lead-wise relevance "corresponds to clinical recommendations" for AF and LBBB on CPSC2018/PTB-XL.
  - Methods are IG and LRP per the search snippet; the abstract does not name them. [verified abstract] https://arxiv.org/abs/2211.01738
- Arends et al., "Signal or noise? Evaluating commonly used attribution methods for explaining deep neural networks in electrocardiogram classification", *EHJ – Digital Health* 7(3) ztag038, 2026. Across 12 attribution methods they found "low correlation and high variability across inter-method comparisons" and self-consistency r = 0.41–0.65. They conclude attribution "should be used cautiously and supported by task-specific sanity checks". [verified abstract] https://researchinformation.umcutrecht.nl/en/publications/signal-or-noise-evaluating-commonly-used-attribution-methods-for-/
  - DELMIR implication [inference]: present per-lead attribution as "what drove the model", not as a diagnosis. Run the weight-randomisation sanity check once offline.

---

## 5. ONNX export, quantisation, Android runtime

### Exporter
- Since **PyTorch 2.9, `dynamo=True` (the torch.export path) is the default**: "Changed in version 2.9: dynamo is now True by default". It is "the recommended and default way to export models to ONNX". [verified] https://docs.pytorch.org/docs/2.14/onnx.html (docs for 2.14)
- The 2.9 release notes say the default opset is 20. They advise pinning opset 18 if the runtime needs it, and falling back to `dynamo=False` only if blocked. [verified] https://github.com/pytorch/pytorch/releases/tag/v2.9.0
- Relevant `torch.onnx.export` parameters [verified] https://docs.pytorch.org/docs/2.14/onnx_export.html
  - `dynamic_shapes` replaces the deprecated `dynamic_axes`.
  - `do_constant_folding` and `training` are deprecated.
  - `optimize=True` is the default.
  - **`external_data=True` is the default**, which saves weights in a side file. Pass `external_data=False` to get one self-contained `.onnx` for the app bundle. [measured: worked]
- **Conv1d export** [measured]: xresnet1d101 exports to plain ONNX `Conv` with 1-D `kernel_shape=[5]`, `strides`, `pads` (opset 20). BatchNorm was folded into Conv by the exporter's optimiser: 103 Conv, only 2 BN left (the head's BN1d). File is 7.96 MB fp32.
- Gotchas [measured]:
  - Call `.eval()` on the *top-level* module you export. With the TorchScript exporter, a wrapper left in train mode switched the inner model back to training (BatchNorm error on a later export).
  - With `dynamic_shapes`, the dict keys must be the forward arg names (`input` for `nn.Sequential`). A tuple is simpler.

### Quantisation (ONNX Runtime)
- Dynamic quantisation computes activation scale/zero-point at run time. Static quantisation uses calibration data. "it is recommended to use dynamic quantization for RNNs and transformer-based models" and static for CNNs. Formats are QOperator (QLinearConv…) and QDQ (Q/DQ pairs around ops). "S8S8 with QDQ is the default setting and balances performance and accuracy". Calibration methods are MinMax, Entropy and Percentile. Use `quant_pre_process()` before quantising. Per-channel helps when weight ranges are large. Requires opset ≥ 10. The U8S8 saturation issue applies only to x86 AVX2/AVX512, with "no such issue on … Arm". [verified] https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html
- "Conv is static-only" is **not literally true**. ORT's dynamic registry (`IntegerOpsRegistry`) maps `"Conv": ConvInteger`, so dynamic quantisation *does* touch Conv. The docs simply recommend static for CNNs. [verified] https://raw.githubusercontent.com/microsoft/onnxruntime/main/onnxruntime/python/tools/quantization/registry.py
  - [unverified] ConvInteger kernels are generally slow or unsupported on EPs, which is why static QDQ is preferred.
- **Measured** (xresnet1d101 at 12×1000, static QDQ, per-channel, S8S8, 8 random calibration inputs):
  - File size 7.96 → 2.39 MB.
  - After ORT optimisation, 69 of 103 Convs became `QLinearConv`; 34 stayed float.
  - Desktop single-thread latency 3.1 → 1.9 ms.
  - Logits were close (e.g. 0.0563 vs 0.0529).
  - Real calibration data and an accuracy/calibration re-check are mandatory. **Re-fit temperature after quantising** [inference].
- **Float16**: `onnxconverter_common.float16.convert_float_to_float16(model, keep_io_types=True)` can halve size and speeds up "some GPUs". Also, "the CPU version of ONNX Runtime doesn't support float16 ops". **Do not use fp16 for phone CPU inference**; use fp32 or int8. [verified] https://onnxruntime.ai/docs/performance/model-optimizations/float16.html

### Android execution providers
- Prebuilt Android packages contain CPU (the default) + NNAPI + XNNPACK. "If the model is quantized, start with the CPU Execution Provider"; for non-quantised models, start with XNNPACK. The custom/reduced build example (ResNet50) shrank arm64 `libonnxruntime.so` from 16.3 MB to 4.0 MB and needs ORT-format models (`--minimal_build=extended`). [verified] https://onnxruntime.ai/docs/tutorials/mobile/
- **onnxruntime-react-native** `executionProviders`: "Android: cpu / xnnpack / nnapi"; iOS: cpu/xnnpack/coreml. Added in PR #16233, merged 2023-06-16. [verified] https://github.com/microsoft/onnxruntime/pull/16233 . Install with `npm install onnxruntime-react-native`. [verified] https://onnxruntime.ai/docs/install/
- **XNNPACK EP**: Conv, MaxPool/AveragePool and QLinearConv are **2D only**. `intra_op_num_threads` defaults to 1; set it to the number of physical cores and disable ORT intra-op spinning. [verified] https://onnxruntime.ai/docs/execution-providers/Xnnpack-ExecutionProvider.html
  - [inference] A Conv1d model's Conv nodes fall back to the CPU EP (MLAS), which is fine. To use XNNPACK, write the net with `Conv2d` kernels of (1, k) on input (N, 12, 1, T). Benchmark first. [unverified benefit]
- **NNAPI EP**: requires Android 8.1+ and recommends 9+. Conv/MaxPool are 2D only. [verified] https://onnxruntime.ai/docs/execution-providers/NNAPI-ExecutionProvider.html
  - **NNAPI itself "is deprecated … deprecated in Android 15"** per Google. [verified] https://developer.android.com/ndk/guides/neuralnetworks/migration-guide
  - The ORT NNAPI page carries no deprecation notice. → **Skip NNAPI for DELMIR**; use the CPU EP (int8 QDQ) or XNNPACK (fp32).
- **ORT format**: "Both ORT format models and ONNX models are supported by a full ONNX Runtime build". Convert with `python -m onnxruntime.tools.convert_onnx_models_to_ort`. It is needed only for reduced/minimal builds. [verified] https://onnxruntime.ai/docs/performance/model-optimizations/ort-format-models.html
  - [inference] With the stock `onnxruntime-react-native` build, ship a plain `.onnx` file.

### Size, FLOPs, latency
- Rule of thumb: size ≈ params × 4 B (FP32) or × 1 B (INT8) plus graph overhead. My measured INT8 QDQ file was 2.39 MB for 1.87M params, larger than 1 byte/param because 34 Convs stayed float and Q/DQ nodes add overhead. [measured]
- **xresnet1d101 as in helme/ecg_ptbxl_benchmarking** (expansion 4, layers [3,4,23,3], ks = 5, stem (32,32,64), stage widths all 64 (×4 = 256 out), concat-pool head with `lin_ftrs=[128]`). Architecture read from https://raw.githubusercontent.com/helme/ecg_ptbxl_benchmarking/master/code/models/xresnet1d.py and basic_conv1d.py; I re-implemented it, so counts may differ slightly from the original. [measured]

| model | params | FP32 size | 12×250 (2.5 s@100 Hz) | 12×1000 (10 s@100 Hz) | 12×2500 (5 s@500 Hz) | 12×5000 (10 s@500 Hz) |
|---|---|---|---|---|---|---|
| xresnet1d101, ks 5 | 1.87 M | 7.5 MB | 0.082 GFLOP | 0.32 GFLOP | 0.81 GFLOP | 1.62 GFLOP |
| xresnet1d50, ks 5 | 0.95 M | 3.8 MB | 0.053 | 0.21 | 0.53 | 1.05 |
| xresnet1d101, ks 25 (500 Hz variant) | 4.64 M | 18.6 MB | 0.22 | 0.85 | 2.13 | 4.24 |

  - FLOPs = 2 × MACs, from `torch.utils.flop_counter`.
  - In Strodthoff's 500 Hz ablation the kernel sizes were "multiplied by five" and the windows were 5 s. The main results use **100 Hz, 2.5 s random crops**, with the test-time sliding window aggregated by max. That is why the ks 25 row exists. [verified] https://ar5iv.labs.arxiv.org/html/2004.13701
  - FLOPs scale linearly with T. 10 s@500 Hz is 20× the 2.5 s@100 Hz cost for the same kernels.
- Desktop ORT CPU, single thread, xresnet1d101 ks 5: 0.8 ms (L 250), 2.8 ms (L 1000), 13.5 ms (L 5000). [measured]
  - [unverified estimate] A mid-range phone's big core is perhaps 3–10× slower, so even 5 ensemble members × 13 ablation passes at 12×1000 (65 forwards ≈ 180 ms desktop) would be roughly 0.5–2 s on a phone. Benchmark on the real device.
- **Published phone latency for 1D-CNN 12-lead ECG**: none found in a primary source. The closest is a GitHub repo reporting a TFLite fp16 ResNet1D at 19.47 ms/sample and 9.83 MB on unstated hardware. [unverified] https://github.com/Saifeddine-Rejeb/Multi-Label-12-Lead-ECG-Classification

---

## 6. Training on an 8 GB RX 6600 XT (gfx1032) with ROCm

### Official vs community
- **Official**: the ROCm Linux system-requirements page (current release referenced: ROCm 7.14.0) lists RDNA2 only as **gfx1030 = Radeon PRO W6800, PRO V620**. **gfx1032 (RX 6600/6600 XT) is not listed**: "If a GPU is not listed on this table, it's not officially supported by AMD." Unlisted GPUs "may be community-enabled through TheRock nightly builds", which is not part of the official release. [verified] https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html
- **Community**: `HSA_OVERRIDE_GFX_VERSION=10.3.0` makes the runtime treat gfx1032 as gfx1030, so official gfx1030 kernels run. It is widely reported to work for RX 6600 on Linux (rocBLAS on Linux with 10.3.0; reported not to work on Windows). I did not find it documented on the rocm.docs.amd.com pages I read. [unverified/community] https://github.com/LostRuins/koboldcpp/issues/655 , https://github.com/ROCm/TheRock/issues/1719
- **Newer option (AMD-run, nightly, not "official release")**: TheRock's SUPPORTED_GPUS.md lists **RDNA2 gfx1032 ✅ Build Passing / ✅ Sanity Tested / ✅ Release Ready** on Linux. [verified] https://github.com/ROCm/TheRock/blob/main/SUPPORTED_GPUS.md
  - RELEASES.md maps "RX 6600 XT / 6600, PRO W6600 → gfx1032 → `device-gfx1032`". Install: `pip install --index-url https://nightly.repo.amd.com/rocm/whl-next/ "torch[device-gfx1032]" "torchvision[device-gfx1032]" torchaudio`. "Nightly packages … may be unstable." [verified] https://github.com/ROCm/TheRock/blob/main/RELEASES.md
  - [inference] Native gfx1032 binaries remove the need for the override. If you use them, do *not* set `HSA_OVERRIDE_GFX_VERSION`.
- AMD's PyTorch-on-ROCm page recommends Docker `rocm/pytorch:latest`. Validated tags are ROCm 7.2.4 with PyTorch 2.9.1/2.8.0/2.7.1. `hipErrorNoBinaryForGPU` means there is no kernel for your gfx target. [verified] https://rocm.docs.amd.com/projects/install-on-linux/en/latest/install/3rd-party/pytorch-install.html
- In PyTorch, "PyTorch for HIP intentionally reuses the existing torch.cuda interfaces". Use device `'cuda'` ("'rocm' or 'hip' are not valid"). Detect ROCm with `torch.version.hip`. [verified] https://docs.pytorch.org/docs/2.14/notes/hip.html

### Mixed precision
- `torch.autocast(device_type='cuda')` defaults to float16 on CUDA/HIP; pair float16 with `torch.amp.GradScaler`. `conv1d` and `matmul` autocast to fp16; `softmax` and `sum` to fp32. Use `BCEWithLogits`/`cross_entropy`, not `BCELoss`. [verified] https://docs.pytorch.org/docs/2.14/amp.html
- [unverified] RDNA2 has packed-FP16 ALUs but no WMMA/matrix cores (those arrived with RDNA3), so fp16 speedups for conv may be modest. bf16 on gfx103x may be emulated or slow. Prefer fp16 + GradScaler and measure. TF32 is irrelevant: the HIP notes mention TF32 only for MI300.

### MIOpen quirks
Source for all bullets: [verified] https://rocm.docs.amd.com/projects/MIOpen/en/latest/how-to/find-and-immediate.html , https://rocm.docs.amd.com/projects/MIOpen/en/latest/conceptual/cache.html , https://rocm.docs.amd.com/projects/MIOpen/en/latest/conceptual/finddb.html
- **Find modes** (`MIOPEN_FIND_MODE`): NORMAL = 1 (benchmark all solvers), FAST = 2, HYBRID = 3, DYNAMIC_HYBRID = 5, TRUST_VERIFY = 6, TRUST_VERIFY_FULL = 7. "The default find mode is `DYNAMIC_HYBRID`".
- "the first call to `miopenConvolution*Immediate` might take more time because the kernel must be compiled". Compiled kernels are cached in `$HOME/.cache/miopen`, "so they don't need to be compiled the next time".
- A per-user **User FindDb** in the home directory stores Find() results and "always takes precedence" over the system FindDb. A new MIOpen version ignores old user FindDb files.
- [inference] Practical consequences:
  - The first epoch (and first validation pass) is slow while kernels compile and get benchmarked per new tensor shape.
  - Keep input length and batch size fixed (random fixed-length crops, `drop_last=True`) so the shape set stays small.
  - Persist `~/.cache/miopen` and the user DB between runs (mount them if you use Docker).
- [unverified] PyTorch's Conv1d is lowered to a 2-D convolution with height 1 (ATen "view1d_as_2d"), so MIOpen sees 2-D problems.
- [unverified] `torch.backends.cudnn.benchmark=True` on ROCm triggers MIOpen's exhaustive Find.

### Memory estimate (fits easily)
- **Measured** (xresnet1d101 ks 5): the sum of forward outputs of Conv/BN/ReLU/pool layers per sample is 3.7 MB at 12×250, 14.6 MB at 12×1000, 36.5 MB at 12×2500, and 72.8 MB at 12×5000, all FP32. This is a rough proxy for saved activations: in-place ReLU is double-counted, autograd internals are not.
  - So at 10 s@500 Hz, batch 64 ≈ 4.7 GB FP32 activations, ~2.3 GB with fp16 autocast.
  - At 100 Hz, batch 256 ≈ 3.7 GB FP32 (12×1000) or under 1 GB (12×250).
  - Parameters + Adam state: 1.9M × 16 B ≈ 30 MB, negligible.
  - [inference] MIOpen workspace and the PyTorch caching allocator add overhead. Start at batch 64 (500 Hz) or 128–256 (100 Hz) and lower it on OOM.
- Five ensemble members at 100 Hz, ~1–2M params each, train comfortably one after another on 8 GB. [inference]

---

## Bottom-line design implied by the sources [inference]
1. **Heads**: shared xresnet1d backbone feeding two heads. The OMI logit uses BCEWithLogits. The vessel softmax (LAD/LCx/RCA, optional 4th "other/none" class) uses CE with `ignore_index=-100`, guarded against all-ignored batches. Report P(v|OMI) only when the call is OMI. Optional masked auxiliary heads (PTB-XL superclass / MI location) with small λ.
2. **Calibration**: temperature or Platt on the *ensemble-mean* OMI logit, fit on held-out, deployment-like data (digitised photos). Apply a Saerens/intercept prevalence shift if the ED prevalence is known. Freeze the two thresholds *after* the final calibration. Report ECE (15 bins) with a reliability diagram plus Brier/NLL.
3. **Uncertainty**: deep ensemble of M = 5 (independent seeds, full data). Member spread combined with signal quality gives the High/Moderate/Low word. Avoid MC dropout unless you use explicit mask inputs: ORT's default optimiser removes Dropout.
4. **Attribution on phone**: lead ablation. One batched forward of 13 per member; average Δ across members. Validate offline against Captum IG per-lead sums (n_steps ≥ 50, check the convergence delta).
5. **Export**: `torch.onnx.export(model.eval(), (x,), f, dynamo=True, external_data=False)`. Static QDQ int8 (per-channel, real calibration ECGs) on the CPU EP, or fp32 with XNNPACK. No NNAPI, no fp16. Re-check calibration after quantising.
6. **Training**: TheRock nightly `torch[device-gfx1032]` (native) or official gfx1030 wheels with `HSA_OVERRIDE_GFX_VERSION=10.3.0` (community). fp16 autocast + GradScaler. Expect a slow first epoch from MIOpen compile/find. Memory is not a constraint for 1–5M-param 1D CNNs.
