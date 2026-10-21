# ECG foundation models: notes for DELMIR (P(OMI) and culprit vessel from digitized 3x4 photo)

Researched 2026-10-21. Primary sources only: arXiv/medRxiv/publisher pages, official GitHub READMEs and code, Hugging Face (HF) model cards and the HF API (`/api/models/<repo>?blobs=true` for file sizes), PhysioNet.
Tags: **[V]** read directly in the source. **[D]** my own derivation or arithmetic, not stated by the source. **[U]** unverified or conflicting.

---

## 0. Bottom line for DELMIR

- **Best evidence on whether these models are actually better: Al-Masud, Lopez Alcaraz & Strodthoff 2025, "Benchmarking ECG Foundational Models: A Reality Check Across Clinical Tasks"** (arXiv 2509.25095, https://arxiv.org/html/2509.25095v2). It is an independent head-to-head of 8 models on the same protocol, and it uses **2.5 s, 12-lead segments** with test-time averaging over four segments. That is close to DELMIR's 2.5 s-per-lead layout. Findings:
  - **ECG-CPC** (3.8M-parameter S4 state-space model) "dominated 5 of 7 task categories". **[V]**
  - On adult ECG interpretation, the top performers were **ECGFounder, ECG-JEPA and ECG-CPC**. **[V]**
  - HuBERT-ECG and ECG-FM did worse, especially frozen. **[V]**
- **Label efficiency.** Against a supervised S4 baseline, foundation models gave 3.3–9× label efficiency. With 250–1,000 labels, ECG-JEPA is the most label-efficient. **[V]** (same URL)
- **No foundation model has been evaluated on ECGs digitized from paper or photos.** I found no primary source for this. **[U]: absence of evidence after search.**
- **Short segments and missing leads.**
  - Weimann-JEPA, Mehari-CPC and the Al-Masud benchmark all fine-tune and evaluate on 2.5 s crops.
  - ST-MEM and Kim's ECG-JEPA report results with reduced leads.
  - ECG-FM uses random lead masking in pretraining.
  - ECGFounder ships a separate 1-lead checkpoint.
- **Phone weight.**
  - Light enough for ONNX on a phone: **ECGFounder** (about 31M params, community ONNX 124 MB fp32), **MERL ResNet18** (4.6M), **ECG-CPC** (3.8M), **HuBERT-ECG small** (30.5M).
  - Heavy: the ViT-B/BERT-base-class transformers. ECG-FM, HuBERT-ECG base/large, ST-MEM and Kim's ECG-JEPA are 87–97M params and 19–74 GFLOP per segment.
- **Licences.**
  - **ST-MEM code is "© VUNO Inc. All rights reserved"**: no permissive licence.
  - **HuBERT-ECG weights are CC BY-NC 4.0**: fine for a personal research tool, but not for commercial use.
  - ECGFounder, ECG-FM, MERL and Kim's ECG-JEPA are MIT.

---

## 1. Comparison table

Params and compute in the "Al-Masud" columns come from Table 32 of https://arxiv.org/html/2509.25095v2: GFLOP forward pass at batch size 1, on that benchmark's input length. PTB-XL "all" macro-AUROC also comes from that benchmark (Tables 3/4), fine-tuned and frozen, all models on 2.5 s segments where supported.

| Model | Paper / venue | Backbone | Params | Pretraining data | Method | Native input | Weights / licence | PTB-XL all (FT / frozen, Al-Masud) | Al-Masud input timesteps; GFLOP fwd |
|---|---|---|---|---|---|---|---|---|---|
| ECGFounder | Li et al., NEJM AI 2(7) 2025, DOI 10.1056/AIoa2401033 | Net1D (RegNet-like 1D CNN) | 33.8M (benchmark); paper Table S11 says 76.3M [U] | HEEDB: 10,771,552 ECGs / 1,818,247 subjects, 150 labels | **Supervised** multi-label | 12-lead (and 1-lead model), 500 Hz, 10 s (12×5000) | HF PKUDigitalHealth/ECGFounder, MIT | 0.934 / 0.927 | 1250; 0.602 |
| ECG-FM | McKeen et al., JAMIA Open 8(5) 2025, DOI 10.1093/jamiaopen/ooaf122 | wav2vec 2.0: CNN + 12-layer transformer, d=768 | 90.9M (paper); 93.9M (benchmark) | ~1.5M ECGs (1,405,625 segments), PhysioNet 2021 + MIMIC-IV-ECG | wav2vec2 masked contrastive + CMSC (CLOCS) + random lead masking ("WCR") | 12-lead, 500 Hz, **5 s** segments | HF wanglab/ecg-fm, MIT (card); needs fairseq-signals | 0.927 / 0.884 | 2500; 29.2 |
| HuBERT-ECG | Coppola et al., medRxiv 10.1101/2024.11.14.24317328 (preprint; revised 06/2026) | HuBERT (CNN + transformer) | small 30.5M / base 92.9M / large ~0.2B (HF); 97.2M (benchmark) | 9.1M 12-lead ECGs from 4 countries | HuBERT masked prediction of k-means cluster targets | 12-lead, stored at 500 Hz then decimated ×5 to **100 Hz**, **5 s** crops (code) | HF Edoardo-Coppola/*, **CC BY-NC 4.0** | 0.915 / 0.883 | 500; 18.8 |
| ST-MEM | Na et al., ICLR 2024 (arXiv 2402.09450) | ViT-B/75 MAE | 90.3M (benchmark) | 188,480 ECGs (Chapman, Ningbo, CODE-15 subset) | Masked reconstruction (MAE, spatio-temporal), 75% mask | 12-lead, 250 Hz, crop 2250 samples = 9 s [D] | Google Drive (README); code **"© VUNO, all rights reserved"** | 0.908 / 0.910 | 600; 20.9 |
| ECG-JEPA (Kim) | S. Kim, arXiv 2410.08559 (preprint, v5 Apr 2026) | Transformer, 12 layers, d=768, CroPA attention | 87.2M (benchmark) | ~174k (Chapman+Ningbo 43,240; CODE-15 130,900) | JEPA (latent prediction) | 8 leads (I, II, V1–V6), 250 Hz, 10 s | Google Drive (README), MIT | 0.940 / 0.934 | 2500; 73.9 |
| ECG-JEPA (Weimann) | Weimann & Conrad, arXiv 2410.13867 (CIBM per RIS record [U]) | ViT-XS 3.6M / ViT-S 14.3M / ViT-B 85.2M | see backbone | 1,011,849 records, 10 datasets (MIMIC-IV-ECG 800,035) | JEPA | 12-lead, 500 Hz; pretrain on 10 s crops, **fine-tune on 2.5 s crops** | code MIT; **no weights link found** | not in benchmark | n/a |
| MERL | Liu et al., ICML 2024 (arXiv 2403.06659) | 1D-ResNet18 (also ViT variant) + Med-CPT text encoder | 4.6M (benchmark) | MIMIC-IV-ECG: 800,035 ECG-report pairs, 161,352 subjects (771,693 after curation) | ECG-report CLIP-style contrastive + uni-modal alignment | 12-lead, 500 Hz, 10 s | Google Drive (README), repo MIT | 0.925 / 0.909 | 1250; 0.863 |
| ECGFM-KED | Tian et al., Cell Rep Med 2024, DOI 10.1016/j.xcrm.2024.101875 | ResNet + text (benchmark description) | 9.7M (benchmark) | 800k ECGs / ~160k patients (MIMIC-IV-ECG-sized) | Signal–report contrastive with LLM knowledge | [U] | [U] | 0.889 / 0.810 | 5000; 5.42 |
| ECG-CPC | Al-Masud et al. 2025 (arXiv 2509.25095) | S4 state-space model | 3.8M | HEEDB 10.7M | CPC | 12-lead, 240 Hz | figshare checkpoint (repo README); licence not stated [U] | **0.949** / 0.931 | 600; 1.74 |
| CLEF | Shu et al., arXiv 2512.02180 (Nokia Bell Labs) | 3 sizes: 448K / 30.7M / 296M | see backbone | MIMIC-IV-ECG, 161K patients | Contrastive, negatives weighted by clinical risk score | **Single lead (lead I)** at inference | Zenodo; repo BSD-3-Clause-Clear | n/a | n/a |
| Supervised S4 (baseline) | same benchmark | S4 | 2.2M | — | supervised | 100 Hz, 2.5 s | — | 0.941 / — | — |

---

## 2. Per-model detail

### 2.1 ECGFounder (Harvard–Emory / PKU)

- **Paper.**
  - arXiv 2410.04133 (v4, Aug 2025): https://arxiv.org/html/2410.04133
  - Journal version: **NEJM AI vol 2 no 7, July 2025, DOI 10.1056/AIoa2401033**. Sources are the citation block in the GitHub README (https://github.com/PKUDigitalHealth/ECGFounder) and Ovid (https://www.ovid.com/journals/neai/pdf/10.1056/aioa2401033~an-electrocardiogram-foundation-model-built-on-over-10). **[V]**
- **Architecture.**
  - Net1D, based on RegNet: stage-wise design, bottleneck blocks with group convolutions, channel attention (SE) and skip connections. **[V]** arXiv HTML.
  - Released config from the repo `finetune_model.py`: `Net1D(base_filters=64, ratio=1, filter_list=[64,160,160,400,400,1024,1024], m_blocks_list=[2,2,2,3,3,4,4], kernel_size=16)`. Loading drops the `dense.` head. **[V]** https://raw.githubusercontent.com/PKUDigitalHealth/ECGFounder/HEAD/finetune_model.py
- **Parameter count [U]: conflicting.**
  - The paper (Table S11) says 76.3M, with ablation variants of 11.7M, 25.6M and 110M. **[V]** arXiv HTML.
  - Al-Masud's benchmark lists 33.8M (https://arxiv.org/html/2509.25095v2).
  - A community ONNX export is 123.6 MB fp32, which implies about 31M params. **[D]** That supports roughly 31–34M for the *released* checkpoint.
  - The HF `.pth` files are 369.9 MB (`12_lead_ECGFounder.pth`) and 369.8 MB (`1_lead_ECGFounder.pth`), loaded via `checkpoint['state_dict']`. They likely carry extra state such as the optimizer. **[D]** File sizes are **[V]** from the HF API.
- **Data.** HEEDB: 10,771,552 ECGs from 1,818,247 subjects. 150 labels derived from 287 raw phrases. Development split 7,519,035 ECGs; test split 834,926. **[V]** arXiv HTML.
- **Method.**
  - **Supervised** multi-label classification, *not* self-supervised.
  - Loss is a positive-unlabelled-aware variant, L = −(γ−p)p², γ = 1.5.
  - Training: AdamW, learning rate 1e-3, batch 1024, ≤20 epochs. **[V]** arXiv HTML.
- **Input.**
  - 12 leads, 500 Hz, 10 s (12×5000). Shorter recordings are zero-padded. Each segment is z-scored. **[V]**
  - HF `config.json`: `{"input_size": 5000, "sampling_rate": "500Hz", "time": "10s", "lead_num": "12/1"}`. **[V]** https://huggingface.co/PKUDigitalHealth/ECGFounder/resolve/main/config.json
  - Band-pass conflict inside the paper: 0.5–50 Hz (§2.1) vs 1–30 Hz (S3.3). **[V/U]**
  - The README warns that you "must strictly follow the preprocessing steps in dataset.py". **[V]**
- **Weights.** HF `PKUDigitalHealth/ECGFounder`, MIT, not gated. **[V]** HF API. Files: `12_lead_ECGFounder.pth`, `1_lead_ECGFounder.pth`.
- **Results.**
  - Internal: AUROC >0.95 on 80 diagnoses. **[V]**
  - PTB-XL average AUROC 0.924 (95% CI 0.917–0.931), zero-shot on the classes that overlap with its own label set. **[V]**
  - PTB-XL MI classes (Table 2): anterior 0.635, anterolateral 0.945, inferior 0.851, lateral 0.916, anteroseptal 0.945. **[V]**
  - CODE-test 0.981. **[V]**
- **Low-label (linear probe, frozen) on PTB-XL-Super with 1% / 10% / 100% labels:** 79.65 / 87.34 / 91.20. **[V]** arXiv HTML S4.2. For comparison, MERL under the same benchmark protocol scores 82.39 / 86.27 / 88.67 (§2.6).
- **Reduced leads.**
  - A separate single-lead model was trained with lead I plus one random augmented lead at 50% probability. Single-lead internal AUC rose from 83.76 to 86.92 with that augmentation (Table S10). **[V]**
  - PhysioNet 2017 single lead: AUROC 0.975 for normal sinus rhythm, 0.957 for AF. **[V]**
- **Short segments.**
  - Natively 10 s; the paper zero-pads shorter recordings.
  - **Al-Masud ran it on 1250 timesteps, i.e. 2.5 s at 500 Hz [D], and it still ranked top-3 on adult ECG interpretation** (fine-tuned PTB-XL all 0.934). **[V]** https://arxiv.org/html/2509.25095v2
- **ONNX.**
  - The official repo does not mention ONNX. **[V]**
  - A community export exists at HF `ghirani33/ecgfounder-onnx` (MIT; files `ecg_founder_12lead.onnx` 123.6 MB and `ecg_founder_all71.onnx` 123.7 MB). Its card claims input (1, 12, 5000), PTB-XL macro-AUROC 0.909 and **115 ms on a Raspberry Pi 4**. **[V that the card says this; claims unverified]** https://huggingface.co/ghirani33/ecgfounder-onnx
  - It is a plain 1D CNN, so it is ONNX-friendly.
- **Phone cost.**
  - 0.60 GFLOP per 2.5 s segment. **[V]** Al-Masud Table 32.
  - Roughly 31 MB at int8. **[D]**

### 2.2 ECG-FM (UHN / Vector, WangLab)

- **Paper.**
  - arXiv 2408.05178 (v2, 30 May 2025): https://arxiv.org/abs/2408.05178
  - Journal version: **JAMIA Open 8(5), 16 Oct 2025, DOI 10.1093/jamiaopen/ooaf122** (search results showing the PMC and PubMed records, PMC12530324 and PMID 41113504; I could not open the journal page itself) **[V via search metadata]**.
  - arXiv v1 said 1.66M ECGs including private data; v2 and the journal version say 1.5M. **[V via search summary; U]**
- **Architecture.**
  - wav2vec 2.0. CNN feature extractor: 4 blocks of 256 channels, stride 2, kernel 2.
  - Transformer: 12 layers, d = 768, 12 heads, feed-forward 3072.
  - **90.9M params.** **[V]** https://arxiv.org/html/2408.05178 and https://github.com/bowang-lab/ECG-FM
- **Pretraining.**
  - "WCR" = wav2vec2 masked contrastive + CMSC (from CLOCS) + Random Lead Masking (p = 0.5).
  - Data: PhysioNet 2021 (6 subsets) + MIMIC-IV-ECG; 1,405,625 segments.
  - Compute: 3×A100-80GB, about 9.5 days, 240 epochs. **[V]** arXiv HTML.
- **Input.** 12-lead, resampled to 500 Hz, z-scored, non-overlapping **5 s** segments. **[V]**
- **Weights.**
  - HF `wanglab/ecg-fm`, MIT. Files: `mimic_iv_ecg_physionet_pretrained.pt` (1.09 GB) and `mimic_iv_ecg_finetuned.pt` (1.08 GB). **[V]** HF API.
  - The checkpoints cannot be loaded with `transformers`; you need fairseq-signals. **[V]** https://huggingface.co/wanglab/ecg-fm
- **Results.**
  - MI AUROC 0.939 (AUPRC 0.820) on UHN-ECG; 0.928 on MIMIC-IV-ECG machine reads.
  - AF 0.996.
  - LVEF ≤40% 0.929 (linear probe 0.914; random init 0.879). **[V]** arXiv HTML.
  - Independent ACS study (MEDIC prehospital, 5,813 ECGs): ECG-FM AUPRC 0.667±0.024 vs ST-MEM 0.594±0.013. **[V as cited in the ECG-FM paper]**
  - No PTB-XL, STEMI or OMI results in the paper. **[V]**
- **Low-label.**
  - Experiments at 50% / 10% / 1% of training data.
  - The authors say it beats baselines in the "small-to-medium" data regime. Linear probing is comparable to full fine-tuning at the smallest sizes. **[V]**
  - Independent comparison in Kim's ECG-JEPA paper, PTB-XL linear probe: 1% = 0.729, 10% = 0.844, which is below ST-MEM and JEPA. **[V]** https://arxiv.org/html/2410.08559
- **Reduced leads.** Random lead masking was used in pretraining. The authors say it *enables* reduced-lead use but did not test it. **[V]**
- **ONNX.**
  - No export known. **[V: none found]**
  - wav2vec2-style models are generally exportable with `torch.onnx`, but fairseq-signals adds friction. **[D]**
- **Phone cost.** 29.2 GFLOP per 5 s segment; ~360 MB fp32, ~90 MB int8. **[D from 90.9M]** Heavy for a phone.

### 2.3 HuBERT-ECG (Brescia)

- **Paper.**
  - medRxiv 10.1101/2024.11.14.24317328, a preprint; a substantially revised version was posted 06/2026 (GitHub README). **[V]** https://github.com/Edoar-do/HuBERT-ECG
  - I could not open the medRxiv full text (HTTP 403).
  - The abstract (HF card) reports AUROC ranges, not specific results:
    - ECG-primary diagnostic 84–99%
    - supportive diagnostic 76–97%
    - prognostic 74–91%
    - **single-lead benchmarks 88–92%** **[V]**
  - Evaluated on 21 datasets and more than 1.6k targets. **[V]** https://huggingface.co/Edoardo-Coppola/hubert-ecg-large
- **Sizes.**
  - Small 30.5M (`model.safetensors` 121.9 MB). **[V]** https://huggingface.co/Edoardo-BS/hubert-ecg-small and HF API.
  - Base 92.9M (372.5 MB). **[V]**
  - Large "0.2B". **[V]**
  - SSL-pretrained `.pt` files: small 366 MB, base 1.12 GB, large 2.26 GB. **[V]** HF API `Edoardo-Coppola/HuBERT-ECG-SSL-Pretrained`.
- **Data / method.**
  - 9.1M 12-lead ECGs from 4 countries. **[V]**
  - HuBERT masked prediction of k-means codebook targets. `pretraining.sh` sets `mask_time_prob=0.33`, `vocab_sizes=100` and `--downsampling_factor=5`. Later pretraining iterations ran 800k steps for base and 400k for small and large. **[V]** https://raw.githubusercontent.com/Edoar-do/HuBERT-ECG/HEAD/scripts/pretraining.sh
- **Input (from code).** **[V]** `hubert_ecg/utils.py`, `hubert_ecg/dataset.py`.
  - Band-pass 0.05–47 Hz.
  - Resample to 500 Hz.
  - Min-max scale to [−1, 1] per lead.
  - Dataset takes a random **5 s** crop (2500 samples at 500 Hz) and decimates ×5, giving **100 Hz, 12×500**.
- **Licence.** **CC BY-NC 4.0** (models and repo). **[V]**
- **ONNX.** No export known. It loads via `AutoModel` with `trust_remote_code`, so `torch.onnx` export is plausible. **[D]**
- **Phone cost.**
  - Base: 18.8 GFLOP per 5 s segment. **[V]** Al-Masud.
  - Small (30.5M) is phone-feasible.
- **Independent result.** Weak, especially frozen: PTB-XL all frozen 0.883, fine-tuned 0.915. **[V]** Al-Masud.
- **Training note.** HuBERT-ECG and ECG-FM "fail to train without layer-dependent learning rates". **[V]** Al-Masud.

### 2.4 ST-MEM (VUNO)

- **Paper.** Na, Park, Tae, Joo, **ICLR 2024**, arXiv 2402.09450. **[V]** https://arxiv.org/abs/2402.09450
- **Architecture.**
  - ViT-B, patch 75. Decoder: 4 blocks, width 256.
  - 75% masking.
  - 90.3M params (benchmark). **[V]**
- **Pretraining data.** 188,480 ECGs: Chapman 10,247 + Ningbo 34,905 + CODE-15 143,328. **[V]** https://arxiv.org/html/2402.09450
- **Input.** 12-lead, 250 Hz, 0.67–40 Hz band-pass, z-normalised. Config: `seq_len: 2250`, `patch_size: 75`, `fs: 250`. **[V]** https://raw.githubusercontent.com/bakqui/ST-MEM/HEAD/configs/downstream/st_mem.yaml
- **Results.** All on PTB-XL superdiagnostic, single-label, with the authors' own split.
  - Fine-tuned 0.933; linear 0.838.
  - **Low-label, fine-tuned:** 1% = 0.815, 5% = 0.878. CPC on the same splits: 0.740 / 0.838. **[V]**
  - **Reduced leads** (PTB-XL / CPSC2018):
    - 12-lead: 0.933 / 0.980
    - 6-lead: 0.903 / 0.973
    - 1-lead (I): 0.804 / 0.937 **[V]**
- **Weights.** Google Drive links (encoder; encoder + decoder) in the README. **Licence: "© VUNO Inc. All rights reserved … Do not distribute, modify, or use … without explicit permission from VUNO."** **[V]** https://github.com/bakqui/ST-MEM README
- **Phone cost.** 20.9 GFLOP per segment of 600 timesteps (2.4 s at 250 Hz [D]). **[V]** Al-Masud.

### 2.5 ECG-JEPA: two different papers, don't confuse them

**(a) Weimann & Conrad (Zuse Institute Berlin)**, arXiv 2410.13867: "Self-Supervised Pre-Training with Joint-Embedding Predictive Architecture Boosts ECG Classification Performance". **[V]** https://arxiv.org/html/2410.13867
- **Venue.** An RIS record lists Computers in Biology and Medicine. **[U]: not checked on the publisher page.**
- **Sizes.** ViT-XS 3.6M (192-d, 8 blocks); ViT-S 14.3M (384-d, 8 blocks); ViT-B 85.2M (768-d, 12 blocks). **[V]**
- **Data.** 10 public datasets: 1,011,849 records, 10,394,994 ECG-seconds. MIMIC-IV-ECG supplies 800,035 records. **[V]**
- **Input.**
  - 500 Hz, 12-lead, patch 25 samples.
  - Pretraining on random 10 s crops.
  - **Fine-tuning and evaluation on 2.5 s crops, stride 1.25 s.** **[V]** This matches DELMIR's 2.5 s strips.
- **Results.** PTB-XL all statements, 10-run mean:
  - ViT-S JEPA (All) fine-tuned 0.945, linear 0.938.
  - ViT-S JEPA (MIMIC-IV-ECG only) linear 0.940.
  - **ViT-XS (3.6M) JEPA (MIMIC-IV-ECG) fine-tuned 0.943.**
  - Comparisons: CPC 0.942; random-init ViT-S 0.883. **[V]** https://github.com/kweimann/ECG-JEPA README
  - So pretraining on MIMIC-IV-ECG alone is about as good as all 10 datasets combined. Directly relevant to DELMIR's data plan. **[V]**
- **Weights.** Code is MIT. The README has **no link to pretrained weights** and the repo has no GitHub releases. **[V: none found]**
- **Phone cost.** ViT-XS and ViT-S are small: 3.6M / 14.3M. **[V]**

**(b) Sehun Kim (Seoul National University)**, arXiv 2410.08559 (v5, 10 Apr 2026): "Learning General Representation of 12-Lead ECG with a JEPA". **[V]** https://arxiv.org/abs/2410.08559, https://arxiv.org/html/2410.08559
- **Architecture.** 12-layer transformer, d = 768, 16 heads; predictor 6 layers, d = 384. CroPA masked attention. 87.2M params (Al-Masud). **[V]**
- **Data.** About 174k ECGs (Chapman + Ningbo 43,240; CODE-15 130,900). Trained on a **single RTX 3090**, 100 epochs. **[V]**
- **Input.** **8 leads** (I, II, V1–V6; the other 4 derived via Einthoven), 250 Hz, 10 s (2500 samples). **[V]**
- **PTB-XL multi-label results.**
  - Linear: 0.906 / 0.912 (random / multi-block masking).
  - Fine-tuned: 0.931 / 0.926.
  - **Low-label linear probe, 1% / 10%:** JEPA 0.839 / 0.893; ST-MEM 0.817 / 0.865; ECG-FM 0.729 / 0.844; KED 0.772 / 0.841. **[V]**
  - **Reduced leads (linear):** lead II only 0.845 / 0.849; II + V1 0.878 / 0.879. **[V]**
- **Weights.** Google Drive (README), MIT. **[V]** https://github.com/sehunfromdaegu/ECG_JEPA
- **Benchmark identity.** This is the "ECG-JEPA" in the Al-Masud benchmark, which gives 174k samples and 87.2M params. **[V]**
- **Phone cost.** 73.9 GFLOP per input (the heaviest in the benchmark). **[V]** Al-Masud.

### 2.6 MERL (Imperial)

- **Paper.** Liu et al., **ICML 2024**, arXiv 2403.06659. **[V]** https://arxiv.org/abs/2403.06659
- **Architecture.** 1D-ResNet18 ECG encoder (ViT-Tiny was worse); Med-CPT text encoder. 4.6M params (Al-Masud). **[V]**
- **Data.** MIMIC-IV-ECG: 800,035 ECG–report pairs, 161,352 subjects, 771,693 after curation. 500 Hz, 10 s. **[V]** https://arxiv.org/html/2403.06659
- **Method.** ECG–report contrastive (temperature 0.07) + uni-modal alignment (latent dropout 0.1). Zero-shot via LLM-enhanced prompts (CKEPE). **[V]**
- **Linear-probe AUC at 1% / 10% / 100% labels:**
  - PTB-XL super: 82.39 / 86.27 / 88.67
  - sub: 64.90 / 80.56 / 84.72
  - form: 58.26 / 72.43 / 79.65
  - rhythm: 53.33 / 82.88 / 88.34
  - Zero-shot mean over 6 datasets: 75.2. **[V]**
- **Weights.** Google Drive folder (ResNet and ViT variants), repo MIT. **[V]** https://github.com/cheliu-computation/MERL-ICML2024
- **Independent MI results** (Al-Masud Table 8, PTB labels, fine-tuned). **Acute MI: MERL 0.819** (best), ST-MEM 0.809, ECG-CPC 0.793, S4 0.722. **[V]**
- **Why it matters for DELMIR.** It uses exactly the MIMIC-IV-ECG machine reports DELMIR plans to use, and it is a small CNN that is cheap on a phone (0.86 GFLOP).

### 2.7 Others (brief)

- **ECG-CPC** (Al-Masud et al. 2025). 3.8M-param S4 model, CPC on HEEDB, 240 Hz. Trained on 1×L40 for 3 weeks. Checkpoint on figshare (repo README). **[V]** https://arxiv.org/html/2509.25095v2, repo `AI4HealthUOL/ecg-fm-benchmarking` (no licence file **[V]**). Best on PTB-XL all fine-tuned (0.949). S4 ops may be awkward in ONNX **[D/U]**.
- **ECGFM-KED** (Tian et al., Cell Rep Med 2024). Signal–report contrastive with LLM knowledge; 800k ECGs / ~160k patients; zero-shot focus. **[V]** Europe PMC abstract, DOI 10.1016/j.xcrm.2024.101875. Weakest frozen model in Al-Masud (PTB-XL all 0.810).
- **CLEF** (Shu et al., Nokia Bell Labs, arXiv 2512.02180).
  - Single-lead foundation model pretrained on MIMIC-IV-ECG (161K patients) using negatives weighted by clinical risk score. **[V]** https://arxiv.org/abs/2512.02180
  - Sizes: 448K / 30.7M / 296M. Zenodo weights; repo BSD-3-Clause-Clear. **[V]** https://github.com/Nokia-Bell-Labs/ecg-foundation-model
  - Lead-I only, so not a fit for 12-lead OMI. Shows that clinical-metadata supervision is possible.
- **SiamQuality** (Ding et al., Physiol Meas 2024). **PPG, not ECG**: 36M 30 s PPG pairs, CNN. **[V]** https://arxiv.org/pdf/2404.17667. Not relevant.
- **ECG-GPT** (Khunte, Sangha, Khera et al., Yale; medRxiv 10.1101/2024.02.17.24302976).
  - Vision encoder–decoder that generates reports **from ECG images**. Trained on Yale ECGs 2000–2022; validated in 6–7 sites. **[V via search snippets of the medRxiv page]**
  - Journal: EHJ Digital Health 2026 **[U]**. Weights availability **[U]**.
  - It is the main image-native line of work, not a signal foundation model.
- **xECG / BenchECG** (Lunelli et al., arXiv 2509.10151). xLSTM + SimDINOv2. Claims the best BenchECG score among public models. Parameter count and weights not on the abstract page **[U]**. https://arxiv.org/abs/2509.10151

---

## 3. Evidence that self-supervised pretraining helps with few labels

- **Mehari & Strodthoff 2022**, Comput Biol Med 141:105114, DOI 10.1016/j.compbiomed.2021.105114 (arXiv 2103.12676). **[V]** https://arxiv.org/abs/2103.12676, PDF text.
  - **Setup.** 100 Hz, **2.5 s** crops (stride 1.25 s at test). Pretrained on "All" = CinC2020 + Chapman + Ribeiro, 54,566 records.
  - **Architectures.** CPC on 4FC+2LSTM+2FC (5.8M params during fine-tuning); SimCLR/BYOL on xresnet1d50 (930K params).
  - **PTB-XL all-statements macro AUC (lin. eval / finetuned):**

    | Model | Linear eval | Fine-tuned |
    |---|---|---|
    | Supervised 4FC+2LSTM+2FC | 0.7110 | 0.9318 |
    | Supervised xresnet1d50 | 0.7210 | 0.9242 |
    | CPC (All) | **0.9272** | **0.9418** |
    | CPC (PTB-XL only) | 0.9246 | 0.9395 |
    | CPC (CinC w/o PTB-XL) | 0.9192 | 0.9401 |
    | SimCLR (RRC, TO) | 0.8828 | 0.9265 |
    | BYOL (RRC, TO) | 0.8781 | 0.9290 |

  - **Gains.** Fine-tuning gains over supervised: +1.0% (CPC), +0.2% (SimCLR), +0.5% (BYOL). The gain was statistically significant in 90 of 100 comparisons.
  - **Label efficiency.** CPC matches full-data supervised performance at about 5 of 8 folds (**~62% of the data**). "Roughly 50–60% of the samples" in the conclusion. CPC trained on 2 folds (50%) matches supervised at 4 folds.
  - **Per-statement.** Gains correlate negatively with supervised performance: weak classes gain most.
  - **Noise.** Better robustness to physiological noise, especially with pretraining augmentations that mimic physiological noise.
- **CLOCS** (Kiyasseh, Zhu, Clifton; ICML 2021, PMLR 139:5606–5615). Contrastive learning across space (leads), time and patients. "Strong generalization performance with only 25% of labelled training data"; beats BYOL and SimCLR. **[V]** https://proceedings.mlr.press/v139/kiyasseh21a.html. ECG-FM reuses its CMSC loss.
- **ST-MEM** at 1% labels: 0.815 vs CPC 0.740 (PTB-XL super). **[V]** §2.4.
- **Kim's ECG-JEPA** at 1% labels, linear: 0.839 vs ECG-FM 0.729. **[V]** §2.5b.
- **MERL** at 1% labels, linear (PTB-XL super): 82.39 vs SimCLR 63.41. **[V]** §2.6.
- **Al-Masud 2025.**
  - Foundation models give **3.3–9× label efficiency** over supervised S4. Ratio r = N*/N (labels S4 needs / labels the foundation model needs; lower is better) at N = 250 / 500 / 1000 / 2000:
    - ECGFounder 0.30 / 0.40 / 0.51 / 0.62
    - ECG-JEPA 0.11 / 0.17 / 0.27 / 0.40
    - ECG-CPC 0.21 / 0.27 / 0.34 / 0.40 **[V]**
  - Caveat: on EchoNext all foundation models stayed below S4. **[V]**
- **OMI-specific.**
  - Singstad et al. (Akershus, Norway). A pretrained ECG foundation model fine-tuned on about 17k ECGs (1,338 OMI) reached AUROC 0.93 / AUPRC 0.72, per a Research Square preprint seen only via search snippets. **[U]**
  - The protocol (https://dx.doi.org/10.17504/protocols.io.n92ld8837v5b/v1) confirms the authors and that a model was fine-tuned on digital 12-lead ECGs from 2016–2022. It **does not name which foundation model**. **[V]**
  - Gustafsson et al. (medRxiv 10.1101/2025.09.11.25335407): a supervised model on 540,372 emergency ECGs with catheterization outcomes. C-statistic >0.95 for OMI; localizes to LM/LAD, LCx, RCA. **[V]** bioRxiv API abstract. Not a foundation model as far as the abstract says.

---

## 4. Short segments, missing leads, digitized signals

- **2.5 s segments.**
  - Mehari CPC (100 Hz, 2.5 s), Weimann JEPA (fine-tune and evaluate on 2.5 s) and the Al-Masud benchmark (2.5 s for every model whose architecture allows it, averaging over 4 segments) all work at this length.
  - Al-Masud: "2.5-second crops with test-time averaging outperforms the full 10 seconds inputs"; longer windows "substantially increase compute with minimal performance gain". **[V]** https://arxiv.org/html/2509.25095v2
  - Caveat for DELMIR: in a 3×4 printout each lead's 2.5 s comes from a *different* time window. Columns are I/II/III, aVR/aVL/aVF, V1–V3, V4–V6 at 0–2.5, 2.5–5, 5–7.5 and 7.5–10 s. A 12-lead model that expects 12 synchronous leads over 2.5 s gets only 3 leads per time window. No foundation-model paper evaluates this layout. **[D; U: no source found]**
- **Missing / reduced leads.**
  - ST-MEM: 6-lead and 1-lead results.
  - Kim JEPA: 1-lead and 2-lead linear probes; natively uses 8 independent leads.
  - ECG-FM: random lead masking in pretraining, but untested.
  - ECGFounder: separate 1-lead model.
  - HuBERT-ECG: single-lead benchmarks 88–92%.
  - CLEF: lead-I-only. **[V]** sections above.
- **Digitized-from-image signals.** I found **no paper evaluating any of these foundation models on signals digitized from paper or photos**. **[U: absence after search]** Related primary work:
  - PhysioNet/CinC Challenge 2024: digitize and classify ECG images (photos and scans). https://moody-challenge.physionet.org/2024/papers/cinc_paper.pdf **[V title via search]**
  - Open-source digitizer (arXiv 2510.19590): validated on 37,191 images. SNR 7.34 dB on scans, but **1.05–2.03 dB on mobile photos and degraded paper**. **[V via search snippet]** That is a large domain gap for photo input.
  - PTB-Image (arXiv 2502.14909): real scanned paper ECGs paired with digital signals. **[V via search snippet]**
  - The community ECGFounder ONNX card states "Raw digital ECG signals only (not scanned paper ECG images)". **[V]**

---

## 5. MIMIC-IV-ECG (PhysioNet v1.0, published 15 Sep 2023)

Source for everything in this section unless noted: https://physionet.org/content/mimic-iv-ecg/1.0/ **[V]**

- **Size.** About **800,000** diagnostic 12-lead ECGs from nearly **160,000** patients. MERL counts 800,035 ECGs / 161,352 subjects (https://arxiv.org/html/2403.06659). **[V]**
- **Format.** **10 s at 500 Hz**, standard 12 leads, WFDB (.hea/.dat). Collected 2008–2019. About 5% are held back as a hidden test set.
- **`machine_measurements.csv`** (174.2 MB):
  - machine report lines `report_0`…`report_17`
  - `rr_interval`, `qrs_onset`, `qrs_end` (global, not per lead), `filtering`
  - `cart_id`, `subject_id`, `study_id`, `ecg_time`
  - Per-lead measures "may be released later".
- **Cardiologist reports.** A little over 600,000 are linked via `waveform_note_links.csv` (`note_id`, `note_seq`). The free text itself is *not* included; it is planned for MIMIC-IV-Note.
- **Linkage.**
  - `subject_id` links to MIMIC-IV v2.2. About 55% of ECGs overlap a hospital admission and about 25% an ED visit.
  - **ECG machine clocks were not synchronised**, so timestamps may be significantly off from MIMIC-IV.
- **Licence / access.** ODbL v1.0, **open access** (no credentialing in v1.0). ZIP 33.8 GB; 90.4 GB uncompressed.

---

## 6. Phone and ONNX summary

| Model | Params | fp32 size | GFLOP per segment (Al-Masud) | ONNX status |
|---|---|---|---|---|
| ECG-CPC | 3.8M | ~15 MB [D] | 1.74 | none known; S4 kernels may need care [U] |
| MERL ResNet18 | 4.6M | ~18 MB [D] | 0.86 | none known; plain CNN, exports easily [D] |
| Weimann ViT-XS / ViT-S | 3.6M / 14.3M | 14 / 57 MB [D] | n/a | no weights released |
| ECGFounder | ~31–34M (released) | 123.6 MB (community ONNX) [V] | 0.60 | **community ONNX exists** (`ghirani33/ecgfounder-onnx`, card claims 115 ms on RPi4) |
| HuBERT-ECG small | 30.5M | 121.9 MB safetensors [V] | n/a (base 18.8) | none known |
| ECG-FM | 90.9M | 1.09 GB `.pt` (includes training state) [V]; ~364 MB weights [D] | 29.2 | none known; fairseq-signals |
| HuBERT-ECG base | 92.9M | 372.5 MB [V] | 18.8 | none known |
| ST-MEM | 90.3M | ~361 MB [D] | 20.9 | none known; restrictive licence |
| Kim ECG-JEPA | 87.2M | ~349 MB [D] | 73.9 | none known |

Training on an 8 GB RX 6600 XT: GPU memory at batch 64 (Al-Masud Table 32) is 187 MB for ECGFounder, 86 MB for MERL, 482 MB for ECG-CPC, 1.09 GB for ECG-FM and 2.14 GB for Kim's JEPA. Fine-tuning any of them should fit; pretraining a ViT-B from scratch is the expensive case. **[V numbers; D inference]**
