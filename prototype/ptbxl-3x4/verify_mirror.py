# PROTOTYPE (#42): take PTB-XL records from an unofficial zip mirror only where they match PhysioNet's
# own SHA256SUMS (fetched from PhysioNet's bucket), copying them into $DELMIR_DATA/ptb-xl/1.0.3.
#   python -I verify_mirror.py <extracted dir>      (prints what is still missing; fetch.py fills gaps)
import hashlib
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

from prep import SRC

root = sys.argv[1]
sums = dict(reversed(l.split()) for l in open(os.path.join(SRC, "SHA256SUMS.txt")) if l.strip())
want = [p for p in sums if p.startswith(("records100/", "records500/"))]
by_name = {}
for d, _, fs in os.walk(root):
    for f in fs:
        if f.endswith((".dat", ".hea")):
            by_name.setdefault(f, os.path.join(d, f))


def take(p):
    dst = os.path.join(SRC, p)
    if os.path.exists(dst) and hashlib.sha256(open(dst, "rb").read()).hexdigest() == sums[p]:
        return "ok"
    src = by_name.get(os.path.basename(p))
    if src is None:
        return "missing"
    if hashlib.sha256(open(src, "rb").read()).hexdigest() != sums[p]:
        return "mismatch"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    return "ok"


with ThreadPoolExecutor(16) as ex:
    res = list(ex.map(take, want))
bad = [p for p, r in zip(want, res) if r != "ok"]
print({r: res.count(r) for r in set(res)}, "of", len(want))
open(os.path.join(SRC, "MISSING.txt"), "w").write("\n".join(bad))
