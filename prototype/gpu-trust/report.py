# PROTOTYPE (#50): the result tables for README.md from results/*.jsonl and runs/*.json.
#   python report.py > results/tables.md
import glob
import json
import os
import re
import shutil


def rows(path):
    return [json.loads(line) for line in open(path)]


print("## Odd eval shapes: whole test fold (2,198 records), unpadded\n")
print("Cell: records off by > 1e-3 vs the CPU (worst |Δprob|), pass 1 / pass 2 over all five sizes.\n")
print("A run with no rows died with a segfault before its first result (B: logs/shapes_B_100_*).\n")
print("| model | stack | expandable_segments | AMD_SERIALIZE_KERNEL | bs 256 | bs 150 | bs 135 | bs 7 | bs 1 |")
print("|---|---|---|---|---|---|---|---|---|")
for path in sorted(glob.glob("results/shapes_*.jsonl")):
    rs = [r for r in rows(path) if r["probe"] == "shape"]
    model, stack, exp, ser = re.match(r"shapes_(.+)_(nix|wheel)_exp(\d)(_serial1)?\.jsonl", os.path.basename(path)).groups()
    if not rs:
        print(f"| {model} | {stack} | {'on' if exp == '1' else 'off'} | {'3' if ser else 'unset'} | segfault | | | | |")
        continue
    cells = []
    for bs in (256, 150, 135, 7, 1):
        c = []
        for rep in (0, 1):
            r = next((r for r in rs if r["bs"] == bs and r["rep"] == rep), None)
            c.append("-" if r is None else ("crash" if r["error"] else
                                             f"{r['bad_rows']} ({r['max_abs']:.0e})" if r["bad_rows"] else "0"))
        cells.append(" / ".join(c))
    print(f"| {model} | {stack} | {'on' if exp == '1' else 'off'} | {'3' if ser else 'unset'} | " + " | ".join(cells) + " |")

print("\n## Serialized launches, expandable segments on (A 100 Hz, how #42 ran)\n")
print("| stack | AMD_SERIALIZE_KERNEL | bs 256 | bs 150 | bs 135 | bs 7 | bs 1 |")
print("|---|---|---|---|---|---|---|")
for path in sorted(glob.glob("results/triage_A_100_*_serial*.jsonl")):
    rs = [r for r in rows(path) if r["probe"] == "shape"]
    stack, ser = path.split("_s0_")[1].split("_")[0], path[-7]
    cells = []
    for bs in (256, 150, 135, 7, 1):
        c = [next(str(r["bad_rows"]) for r in rs if r["bs"] == bs and r["rep"] == rep) for rep in (0, 1)]
        cells.append(" / ".join(c))
    print(f"| {stack} | {'3' if ser == '1' else 'unset'} | " + " | ".join(cells) + " |")

print("\n## Training throughput, xresnet1d101 design A, bs 128, alone on the GPU (nix stack)\n")
print("| input | AMD_SERIALIZE_KERNEL | first step (MIOpen tuning) | samples/s | peak GiB |")
print("|---|---|---|---|---|")
for r in rows("results/bench.jsonl"):
    print(f"| 25 × {1000 if r['fs'] == 100 else 5000} | {r['env'].get('AMD_SERIALIZE_KERNEL', 'unset')} | "
          f"{r['first_step_s']:.0f} s | {r['samples_per_s']:.0f} | {r['peak_gib']:.2f} |")

print("\n## 30-epoch training runs (nix stack, design A, seed 0, no padding, no serialization)\n")
print("| run | expandable_segments | epochs | s/epoch | non-finite steps | val epochs with records off "
      "| worst val |Δprob| | test records off | best epoch | test mean4 AUC GPU / CPU |")
print("|---|---|---|---|---|---|---|---|---|---|")
for path in sorted(glob.glob("runs/*.json")):
    r = json.load(open(path))
    shutil.copy(path, "results/" + os.path.basename(path))  # the run record, without weights
    log = r["log"]
    m4 = lambda t: sum(t[k] for k in ("super", "mi_norm", "territory", "injury")) / 4
    par = "all" if r["parity"] == 0 else f"first {r['parity']}"
    print(f"| {r['name']} | {'on' if 'expandable' in r['env'].get('PYTORCH_CUDA_ALLOC_CONF', '') else 'off'} | "
          f"{len(log)} | {sum(e['sec'] for e in log) / len(log):.0f} | {sum(e['nonfinite_steps'] for e in log)} | "
          f"{sum(e['val_parity']['bad'] > 0 for e in log)} (val records checked: {par}) | "
          f"{max(e['val_parity']['max_abs'] for e in log):.1e} | {r['test_parity']['bad']} / 2198 | {r['best_epoch']} | "
          f"{m4(r['test']):.4f} / {m4(r['test_cpu']):.4f} |")
