# PROTOTYPE (#42): mirror PTB-XL 1.0.3 records from PhysioNet's open S3 bucket into
# $DELMIR_DATA/ptb-xl/1.0.3, many requests at once (latency-bound), each file checked against SHA256SUMS.
#   python fetch.py records100 [records500]
import hashlib
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from prep import SRC

URL = "https://physionet-open.s3.amazonaws.com/ptb-xl/1.0.3/"
sums = dict(reversed(l.split()) for l in open(os.path.join(SRC, "SHA256SUMS.txt")) if l.strip())


def ok(path):
    f = os.path.join(SRC, path)
    return os.path.exists(f) and hashlib.sha256(open(f, "rb").read()).hexdigest() == sums[path]


def get(path):
    f = os.path.join(SRC, path)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    for attempt in range(10):
        try:
            data = urllib.request.urlopen(URL + path, timeout=60).read()
            if hashlib.sha256(data).hexdigest() == sums[path]:
                open(f + ".part", "wb").write(data)
                os.replace(f + ".part", f)
                return True
        except Exception:
            time.sleep(1 + attempt)
    return False


for part in sys.argv[1:]:
    todo = [p for p in sums if p.startswith(part + "/") and p.endswith((".dat", ".hea"))]
    with ThreadPoolExecutor(64) as ex:
        todo = [p for p, good in zip(todo, ex.map(ok, todo)) if not good]
    print(part, "to fetch:", len(todo), flush=True)
    t0, done, failed = time.time(), 0, []
    with ThreadPoolExecutor(256) as ex:
        for p, good in zip(todo, ex.map(get, todo)):
            done += 1
            if not good:
                failed.append(p)
            if done % 2000 == 0:
                print(f"{part} {done}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
    print(part, "done, failed:", failed, flush=True)
