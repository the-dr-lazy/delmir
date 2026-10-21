# PROTOTYPE (#42): the four tasks, scored from one 12-output multi-label model.
#   super     macro-AUC over NORM/MI/STTC/CD/HYP, records with any superclass (benchmark convention)
#   mi_norm   MI head; MI records vs NORM records without MI
#   territory macro-AUC over IMI/ASMI/AMI/ALMI/LMI/ILMI heads, within MI records only
#   injury    INJSTE head; INJ* or STE_ records vs NORM records without them
import numpy as np
from sklearn.metrics import roc_auc_score

from prep import SUPER, TARGETS, TERRITORY

TASKS = ["super", "mi_norm", "territory", "injury"]
COL = {t: i for i, t in enumerate(TARGETS)}


def auc(y, p):
    return roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan


def task_aucs(Y, P, has_super):
    """Y, P: (n, 12) labels and probabilities, has_super: (n,) bool. Returns {task: auc, 'per': {...}}."""
    per = {}
    s = has_super.astype(bool)
    for c in SUPER:
        per[c] = auc(Y[s, COL[c]], P[s, COL[c]])
    mi, norm = Y[:, COL["MI"]] == 1, Y[:, COL["NORM"]] == 1
    sel = mi | (norm & ~mi)
    out = {"super": np.nanmean([per[c] for c in SUPER])}
    out["mi_norm"] = auc(Y[sel, COL["MI"]], P[sel, COL["MI"]])
    for c in TERRITORY:
        per[c] = auc(Y[mi, COL[c]], P[mi, COL[c]])
    out["territory"] = np.nanmean([per[c] for c in TERRITORY])
    inj = Y[:, COL["INJSTE"]] == 1
    sel = inj | (norm & ~inj)
    out["injury"] = auc(Y[sel, COL["INJSTE"]], P[sel, COL["INJSTE"]])
    out["per"] = per
    return out


def headline(Y, P, has_super):
    a = task_aucs(Y, P, has_super)
    return float(np.mean([a[t] for t in TASKS]))
