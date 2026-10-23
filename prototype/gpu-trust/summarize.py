# PROTOTYPE (#50): print shape-probe JSONL as one line per call.
#   python summarize.py results/shapes_*.jsonl
import json
import sys

for path in sys.argv[1:]:
    print(f"## {path}")
    for line in open(path):
        r = json.loads(line)
        if r["probe"] == "start":
            print(f"--- {r['model']} torch {r['torch']} env {r['env']} od {r['od']}")
        elif r["probe"] == "shape":
            print(r["rep"], r["bs"], f"{r['sec']:.1f}s", r["error"] or
                  f"max={r['max_abs']:.1e} bad={r['bad_rows']} [{r['bad_first']}..{r['bad_last']}] nan={r['nan_rows']}")
