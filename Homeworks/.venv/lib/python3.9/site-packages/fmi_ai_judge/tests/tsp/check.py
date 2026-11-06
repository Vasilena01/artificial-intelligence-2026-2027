# TSP checker
import math, re

# Known optimal *open path* totals for named datasets
OPT_BY_DATASET = {
    "UK12": 1595.738522033024,
}

FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_fnum = re.compile(FLOAT + r"$")
_times_header = re.compile(r"^\s*#\s*TIMES_MS\s*:\s*(.*)$", re.I)

def _parse_floats_block(lines, start):
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

def _euclid(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def _path_len_open(pts, order):
    """Open path length: sum over consecutive edges only (no return to start)."""
    if not order:
        return 0.0
    s = 0.0
    for i in range(len(order) - 1):
        s += _euclid(pts[order[i]], pts[order[i+1]])
    return s

def _split_path_names(s):
    r"""Accept separators: spaces, '-', '->', ',', with or without spaces."""
    t = s.strip()
    t = re.sub(r"\s*->\s*", ",", t)
    t = re.sub(r"\s*-\s*",  ",", t)
    parts = [p for p in re.split(r"[,\s]+", t) if p]
    return parts

def _nonincreasing(seq, eps=1e-9):
    return all(seq[i+1] <= seq[i] + eps for i in range(len(seq)-1))

def _close(a,b,abs_tol=1e-6,rel_tol=1e-9): 
    return abs(a-b) <= max(abs_tol, rel_tol*max(abs(a),abs(b)))

def check(in_path: str, out_text: str, _ctx: dict):
    # ---------- read input ----------
    with open(in_path, "r", encoding="utf-8") as f:
        raw_in = [ln.rstrip("\n") for ln in f]
    raw_in = [ln for ln in raw_in if ln.strip()]

    dataset_name = None
    pts = None
    city_names = None

    # Case 1: starts with integer N -> random points
    # Case 2: dataset name, then N, then N lines "Name x y"
    try:
        int(raw_in[0].strip())
        case = 1
    except ValueError:
        case = 2

    if case == 2:
        dataset_name = raw_in[0].strip()
        try:
            N = int(raw_in[1].strip())
        except Exception:
            return {"status": "RTE", "note": "invalid dataset header: missing/invalid N"}
        if len(raw_in) < 2 + N:
            return {"status": "RTE", "note": "dataset missing coordinate lines"}
        names, coords = [], []
        for ln in raw_in[2:2+N]:
            parts = ln.split()
            if len(parts) < 3:
                return {"status":"RTE","note":"dataset line must be: <name> <x> <y>"}
            name = parts[0]
            try:
                x = float(parts[-2]); y = float(parts[-1])
            except ValueError:
                return {"status":"RTE","note":"invalid coordinate format"}
            names.append(name); coords.append((x, y))
        city_names = names
        pts = coords

    # ---------- parse output ----------
    out_lines = [ln.rstrip("\n") for ln in out_text.splitlines()]
    if not out_lines:
        return {"status":"WA","note":"empty output"}

    i = 0
    if _times_header.match(out_lines[0].strip()):
        i = 1  # strip timing header

    dists, j = _parse_floats_block(out_lines, i)
    if not dists:
        return {"status":"WA","note":"missing distances block"}

    if len(dists) < 10:
        return {"status":"WA","note":"need at least 10 distances"}
    if not _nonincreasing(dists):
        return {"status":"WA","note":"distances not non-increasing"}

    k = j
    if k < len(out_lines) and out_lines[k].strip() == "":
        k += 1  # consume blank line if present

    note_parts = []
    improvements = sum(1 for a, b in zip(dists, dists[1:]) if b < a)
    note_parts.append(f"improvements={improvements}")
    note_parts.append(f"length={len(dists)}")

    tol = 1e-6

    if case == 1:
        # Random points: expect a final float (equal to last distance)
        if k >= len(out_lines):
            return {"status":"WA","note":"missing final distance"}
        try:
            final_val = float(out_lines[k].strip())
        except ValueError:
            return {"status":"WA","note":"final distance is not a float"}
        if not _close(final_val, dists[-1]):
            note_parts.append(f"final != last ({final_val} vs {dists[-1]})")
            return {"status":"WA","note":"; ".join(note_parts)}
        # Require at least one strict improvement
        if improvements == 0:
            note_parts.append("no improvement from initial population")
            return {"status":"WA","note":"; ".join(note_parts)}
        return {"status":"OK","correct":True,"complete":True,"note":"; ".join(note_parts) or None}

    # ----- Case 2 (dataset with names; open path) -----
    if k >= len(out_lines):
        return {"status":"WA","note":"missing path line"}
    path_line = out_lines[k].strip(); k += 1
    if k >= len(out_lines):
        return {"status":"WA","note":"missing final distance after path"}
    try:
        final_val = float(out_lines[k].strip())
    except ValueError:
        return {"status":"WA","note":"final distance is not a float"}

    path_names = _split_path_names(path_line)
    if len(path_names) != len(city_names):
        return {"status":"WA","note":f"path has {len(path_names)} cities, expected {len(city_names)}"}

    if set(path_names) != set(city_names):
        missing = sorted(set(city_names) - set(path_names))
        extra   = sorted(set(path_names) - set(city_names))
        msg = []
        if missing: msg.append("missing=" + ",".join(missing))
        if extra:   msg.append("extra=" + ",".join(extra))
        return {"status":"WA","note":"path not a permutation; " + "; ".join(msg)}

    idx = {name:i for i,name in enumerate(city_names)}
    order = [idx[n] for n in path_names]
    L = _path_len_open(pts, order)
    note_parts.append(f"recomputed={L}")

    # final must equal recomputed (open path) and the last reported distance
    if not _close(final_val, L):
        note_parts.append(f"final != recomputed ({final_val} vs {L})")
        return {"status":"WA","note":"; ".join(note_parts)}
    if not _close(final_val, dists[-1]):
        note_parts.append(f"final != last ({final_val} vs {dists[-1]})")
        return {"status":"WA","note":"; ".join(note_parts)}

    # Prefer sibling .out; fallback to embedded map
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
        expected = OPT_BY_DATASET.get(dataset_name)
    
    is_opt = (expected is not None and _close(L, expected))
    
    # If final equals the known optimum, accept even with zero improvements
    if is_opt:
        return {"status":"OK","correct":True,"complete":True,"optimal":True,
                "note":"; ".join(note_parts)}

    # Otherwise, require at least one strict improvement
    if improvements == 0:
        note_parts.append("no improvement from initial population")
        return {"status":"WA","note":"; ".join(note_parts)}

    # Non-optimal but otherwise valid
    return {"status":"OK","correct":True,"complete":True,"optimal":False,
            "note":"; ".join(note_parts)}
