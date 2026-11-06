# N-Queens checker
import re

def _strip_header(s: str) -> str:
    lines = s.splitlines()
    if lines and lines[0].lstrip().startswith("# TIMES_MS:"):
        return "\n".join(lines[1:])
    return s

def _parse_out(text: str):
    """
    Returns either:
      ("unsat", None)     if output is single -1
      ("sol", cols)       where cols is a list of ints (0-based)
      ("bad", reason)
    Accepts: spaces, commas, brackets, or one-per-line. 0-based or 1-based.
    """
    body = _strip_header(text).strip()
    if body == "-1":
        return ("unsat", None)

    # Pull all integers from the text; this tolerates [1,3,0,2], "1, 3, 0, 2", newlines, etc.
    nums = [int(m.group(0)) for m in re.finditer(r"-?\d+", body)]
    if not nums:
        return ("bad", "no integers in output")

    return ("sol", nums)

def _has_conflicts(cols):
    d1 = set()  # r - c
    d2 = set()  # r + c
    for r, c in enumerate(cols):
        a = r - c
        b = r + c
        if a in d1 or b in d2:
            return True
        d1.add(a); d2.add(b)
    return False

def check(stdin_path: str, stdout_text: str, options: dict):
    # Read N from stdin (first non-empty token)
    with open(stdin_path, "r", encoding="utf-8") as f:
        tokens = [t for t in re.findall(r"-?\d+", f.read())]
    if not tokens:
        return {"status":"WA", "note":"missing N in input"}
    N = int(tokens[0])

    kind, payload = _parse_out(stdout_text)

    # Unsatisfiable cases
    if N in (2, 3):
        if kind == "unsat":
            return {"status":"OK", "correct":True, "complete":True}
        else:
            return {"status":"WA", "note":"N in {2,3} must output -1"}

    # Solvable cases (N != 2,3)
    if kind == "unsat":
        return {"status":"WA", "note":"missing or -1 for solvable N"}

    if kind == "bad":
        return {"status":"WA", "note":payload}

    nums = payload
    if len(nums) != N:
        return {"status":"WA", "note":f"expected {N} numbers, got {len(nums)}"}

    # Detect 0-based vs 1-based and normalize to 0-based
    mn, mx = min(nums), max(nums)
    if mn == 0 and mx == N-1:
        cols = nums[:]  # already 0-based
    elif mn == 1 and mx == N:
        cols = [x-1 for x in nums]  # 1-based → 0-based
    else:
        return {"status":"WA", "note":"values must be a permutation of 0..N-1 or 1..N"}

    # Check permutation and conflicts
    if sorted(cols) != list(range(N)):
        return {"status":"WA", "note":"not a permutation"}
    if _has_conflicts(cols):
        return {"status":"WA", "note":"conflicts detected"}

    return {"status":"OK", "correct":True, "complete":True}
