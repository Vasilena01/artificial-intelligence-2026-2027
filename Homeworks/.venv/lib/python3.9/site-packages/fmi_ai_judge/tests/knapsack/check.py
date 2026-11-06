# Knapsack checker (GA-style): values must be non-decreasing, ≥10 lines, then blank, then final value.
# Input format: capacity N, then N lines "weight value"

import re

# Optional embedded optima (fallback). Source of truth should be tXX.out when present.
OPT_BY_ID = {
    "t01": 1130,
    "t02": 5119,
}

FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_fnum = re.compile(FLOAT + r"$")
_times_header = re.compile(r"^\s*#\s*TIMES_MS\s*:\s*(.*)$", re.I)

def _nondecreasing(seq, eps=1e-9):
    return all(seq[i+1] + eps >= seq[i] for i in range(len(seq)-1))

def _close(a, b, abs_tol=1e-6, rel_tol=1e-9):
    return abs(a - b) <= max(abs_tol, rel_tol * max(abs(a), abs(b)))

def _parse_values_block(lines, start):
    vals = []
    i = start
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            break
        if not _fnum.match(s):
            break
        vals.append(float(s))
        i += 1
    return vals, i

def check(in_path: str, out_text: str, _ctx: dict):
    # --- parse input (basic validation only) ---
    with open(in_path, "r", encoding="utf-8") as f:
        raw_in = [ln.strip() for ln in f if ln.strip()]
    try:
        parts = raw_in[0].split()
        cap = int(parts[0]); n = int(parts[1])
    except Exception:
        return {"status":"RTE","note":"invalid header: expected 'M N'"}
    if len(raw_in) < 1 + n:
        return {"status":"RTE","note":"missing item lines"}

    # --- parse output ---
    lines = [ln.rstrip("\n") for ln in out_text.splitlines()]
    if not lines:
        return {"status":"WA","note":"empty output"}
    i = 0
    if _times_header.match(lines[0].strip()):
        i = 1

    vals, j = _parse_values_block(lines, i)
    if not vals:
        return {"status":"WA","note":"missing values block"}
    if len(vals) < 10:
        return {"status":"WA","note":"need at least 10 values"}
    if not _nondecreasing(vals):
        return {"status":"WA","note":"values not non-decreasing"}

    k = j
    if k < len(lines) and lines[k].strip() == "":
        k += 1
    if k >= len(lines):
        return {"status":"WA","note":"missing final value"}
    try:
        final_val = float(lines[k].strip())
    except ValueError:
        return {"status":"WA","note":"final value is not a float"}

    if not _close(final_val, vals[-1]):
        return {"status":"WA","note":f"final != last ({final_val} vs {vals[-1]})"}

    # At least one strict improvement unless optimal
    improvements = sum(1 for a,b in zip(vals, vals[1:]) if b > a)

    # Determine expected optimum: prefer sibling .out, fallback to map
    expected = None
    try:
        if in_path.endswith(".in"):
            with open(in_path[:-3] + "out", "r", encoding="utf-8") as f:
                for tok in f.read().split():
                    try:
                        expected = float(tok); break
                    except ValueError:
                        pass
    except Exception:
        pass
    if expected is None:
        # infer test id from filename (tXX.in)
        import os
        tid = os.path.splitext(os.path.basename(in_path))[0]
        expected = OPT_BY_ID.get(tid)

    is_opt = (expected is not None and _close(final_val, expected))

    if is_opt:
        return {"status":"OK","correct":True,"complete":True,"optimal":True,
                "note":f"improvements={improvements}; length={len(vals)}"}

    if improvements == 0:
        return {"status":"WA","note":"no improvement from initial population"}

    return {"status":"OK","correct":True,"complete":True,"optimal":False,
            "note":f"improvements={improvements}; length={len(vals)}; non-optimal"}
