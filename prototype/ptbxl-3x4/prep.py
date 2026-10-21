# PROTOTYPE (#42): read PTB-XL 1.0.3 once into arrays under $DELMIR_DATA/ptb-xl/cache.
#   python prep.py 100   -> X100.npy float32 (N, 12, 1000)
#   python prep.py 500   -> X500.npy float16 (N, 12, 5000)
#   labels.csv: ecg_id, patient_id, strat_fold and the 12 targets below (same row order).
import ast
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import wfdb

ROOT = os.path.join(os.environ.get("DELMIR_DATA", os.path.expanduser("~/.local/share/delmir")), "ptb-xl")
SRC = os.path.join(ROOT, "1.0.3")
OUT = os.path.join(ROOT, "cache")

SUPER = ["NORM", "MI", "STTC", "CD", "HYP"]
TERRITORY = ["IMI", "ASMI", "AMI", "ALMI", "LMI", "ILMI"]
TARGETS = SUPER + TERRITORY + ["INJSTE"]


def labels():
    db = pd.read_csv(os.path.join(SRC, "ptbxl_database.csv"), index_col="ecg_id")
    scp = pd.read_csv(os.path.join(SRC, "scp_statements.csv"), index_col=0)
    diag = scp[scp.diagnostic == 1].diagnostic_class
    rows = []
    for ecg_id, r in db.iterrows():
        codes = ast.literal_eval(r.scp_codes)  # all statements, any likelihood, as in the benchmark
        sup = {diag[c] for c in codes if c in diag.index}
        row = {"ecg_id": ecg_id, "patient_id": int(r.patient_id), "strat_fold": int(r.strat_fold),
               "filename_lr": r.filename_lr, "filename_hr": r.filename_hr, "has_super": int(bool(sup))}
        row.update({s: int(s in sup) for s in SUPER})
        row.update({t: int(t in codes) for t in TERRITORY})
        row["INJSTE"] = int(any(c.startswith("INJ") for c in codes) or "STE_" in codes)
        rows.append(row)
    return pd.DataFrame(rows)


def read(path):
    return wfdb.rdsamp(os.path.join(SRC, path))[0].T.astype(np.float32)  # (12, T), mV


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    df = labels()
    df.to_csv(os.path.join(OUT, "labels.csv"), index=False)
    fs = int(sys.argv[1])
    col, T, dtype = ("filename_lr", 1000, np.float32) if fs == 100 else ("filename_hr", 5000, np.float16)
    X = np.lib.format.open_memmap(os.path.join(OUT, f"X{fs}.npy.tmp"), "w+", dtype, (len(df), 12, T))
    with ProcessPoolExecutor(16) as ex:
        for i, x in enumerate(ex.map(read, df[col], chunksize=64)):
            X[i] = np.nan_to_num(x)
    X.flush()
    del X
    os.replace(os.path.join(OUT, f"X{fs}.npy.tmp"), os.path.join(OUT, f"X{fs}.npy"))
    print(df[[*TARGETS, "has_super"]].sum().to_string())
    t = df[df.strat_fold == 10]
    print("test fold:", len(t), "records,", t.patient_id.nunique(), "patients")
    print(t[[*TARGETS]].sum().to_string())
