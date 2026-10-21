# PROTOTYPE — #42: what the 3×4 printout layout costs a PTB-XL classifier

Throwaway spike for [#42](https://github.com/the-dr-lazy/delmir/issues/42). Never merged; the answer lives in
the issue's resolution comment and `RESULTS.md`.

## Run

```sh
cd prototype/ptbxl-3x4
uv venv -p python3.12 .venv
uv pip install -p .venv/bin/python --index-url https://download.pytorch.org/whl/cpu torch
uv pip install -p .venv/bin/python numpy pandas scipy scikit-learn wfdb onnx onnxruntime onnxscript captum huggingface_hub
export DELMIR_DATA=~/.local/share/delmir         # PTB-XL 1.0.3 at $DELMIR_DATA/ptb-xl/1.0.3
.venv/bin/python prep.py 100 && .venv/bin/python prep.py 500
./run_grid.sh jobs_100.txt 4                      # then jobs_500.txt
.venv/bin/python evaluate.py runs > results_table.md
.venv/bin/python deploy.py runs/*_s0.pt > deploy_table.md
```

ECGFounder weights: `PKUDigitalHealth/ECGFounder` → `$DELMIR_DATA/ecgfounder/12_lead_ECGFounder.pth`.

## Files

- `prep.py`: PTB-XL → arrays plus the 12 targets (5 superclasses, 6 MI-location statements, INJ\*/STE\_).
- `layout.py`: the 3×4 layout (ECG-Image-Kit windows plus a 10 s lead II strip) and designs S/A/B/C.
- `models.py`: xresnet1d (benchmark re-implementation), plus design B's per-lead encoder and fusion.
- `net1d.py`: ECGFounder's Net1D, vendored (MIT).
- `train.py`: one arm. Folds 1–8 train, 9 select the epoch, 10 test.
- `metrics.py`: the four tasks.
- `evaluate.py`: patient-bootstrapped CIs and the paired drop from S.
- `deploy.py`: params, GFLOP, ONNX Runtime latency, and lead ablation vs integrated gradients.
- `fetch.py`: a checksum-verified PTB-XL mirror from PhysioNet's S3 bucket.
