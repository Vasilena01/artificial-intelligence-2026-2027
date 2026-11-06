# N-Puzzle checker
import math, re, json

_TIMES = re.compile(r"^\s*#\s*TIMES_MS:", re.I)

def _norm(s: str) -> str:
    return s.replace("\r\n","\n").replace("\r","\n").strip()

def _parse_input(inp_text: str):
    lines = [ln for ln in _norm(inp_text).splitlines() if ln.strip()!=""]
    N = int(lines[0])
    goal_z = int(lines[1])
    d = int(round(math.sqrt(N+1)))
    if d*d != N+1:
        raise ValueError("N does not form a square board")
    grid = []
    off = 2
    for i in range(d):
        row = [int(x) for x in lines[off+i].split()]
        if len(row)!=d:
            raise ValueError("bad row width")
        grid.append(row)
    return N, goal_z, d, grid

def _goal_board(N: int, goal_z: int, d: int):
    # tiles 1..N; blank(0) at index goal_z; default -1 => bottom-right (index N)
    if goal_z == -1:
        goal_z = N
    g = list(range(1, N+1)) + [0]
    if goal_z != N:
        g[goal_z], g[N] = g[N], g[goal_z]
    return [g[i*d:(i+1)*d] for i in range(d)]

def _flatten(board):
    return [x for row in board for x in row]

def _pos_map(board):
    # value -> (r,c)
    m = {}
    for r,row in enumerate(board):
        for c,v in enumerate(row):
            m[v] = (r,c)
    return m

def _row_from_bottom(idx, d):
    r = idx // d
    return d - r

def _inv_parity_wrt_goal(start, goal, d):
    """
    Inversion parity of start relative to goal order.
    Compute sequence of goal indices for the start's tile order (excluding 0),
    then take inversion parity of that sequence.
    """
    gs = _flatten(goal)
    # goal index (row-major) for each tile
    gidx = {v:i for i,v in enumerate(gs)}
    seq = [gidx[v] for v in _flatten(start) if v != 0]
    inv = 0
    # parity only; O(n^2) is fine for N<=24
    L = len(seq)
    for i in range(L):
        ai = seq[i]
        for j in range(i+1, L):
            if ai > seq[j]:
                inv ^= 1
    return inv  # 0 even, 1 odd

def _is_solvable(start, goal, d):
    inv_start = _inv_parity_wrt_goal(start, goal, d)
    # start & goal blank row-from-bottom (1..d)
    s_flat = _flatten(start)
    g_flat = _flatten(goal)
    s_blank = s_flat.index(0)
    g_blank = g_flat.index(0)
    s_rfb = _row_from_bottom(s_blank, d)
    g_rfb = _row_from_bottom(g_blank, d)
    if d % 2 == 1:
        # odd width: inversion parity must match (goal parity is 0)
        return inv_start == 0
    else:
        # even width: (inv + row_from_bottom(blank)) parity must match between start & goal
        inv_goal = 0
        return ((inv_start + s_rfb) & 1) == ((inv_goal + g_rfb) & 1)

def _apply_move(board, mv, d):
    """
    Move semantics (as per your spec):
      'left'  = the tile to the RIGHT of blank moves LEFT into the blank (blank moves RIGHT)
      'right' = the tile to the LEFT of blank moves RIGHT into the blank (blank moves LEFT)
      'up'    = the tile BELOW blank moves UP   into the blank (blank moves DOWN)
      'down'  = the tile ABOVE blank moves DOWN into the blank (blank moves UP)
    """
    # locate blank
    br = bc = -1
    for r,row in enumerate(board):
        for c,v in enumerate(row):
            if v == 0:
                br, bc = r, c
                break
        if br != -1:
            break

    if mv == "left":
        nr, nc = br, bc + 1
    elif mv == "right":
        nr, nc = br, bc - 1
    elif mv == "up":
        nr, nc = br + 1, bc
    elif mv == "down":
        nr, nc = br - 1, bc
    else:
        return False

    if not (0 <= nr < d and 0 <= nc < d):
        return False

    board[br][bc], board[nr][nc] = board[nr][nc], board[br][bc]
    return True

def _boards_equal(a,b):
    if len(a)!=len(b): return False
    for r in range(len(a)):
        if a[r]!=b[r]: return False
    return True

def _parse_student_out(out_text: str):
    lines = [ln for ln in _norm(out_text).splitlines()]
    if lines and _TIMES.match(lines[0]):
        lines = lines[1:]
    lines = [ln for ln in lines if ln.strip()!=""]
    if not lines:
        raise ValueError("empty output")

    if lines[0].strip() == "-1":
        return -1, []

    try:
        K = int(lines[0].strip())
    except Exception:
        raise ValueError("first non-header line must be integer K or -1")

    if K < 0:
        raise ValueError("K must be >= 0 or -1 for unsolvable")

    moves = [ln.strip().lower() for ln in lines[1:]]
    return K, moves

def _read_expected_len(expected_path: str):
    try:
        with open(expected_path, "r", encoding="utf-8") as f:
            txt = _norm(f.read())
        for token in txt.split():
            try:
                return int(token)
            except Exception:
                pass
        return None
    except Exception:
        return None

def check(input_path: str, out_text: str, options):
    with open(input_path, "r", encoding="utf-8") as f:
        inp = f.read()
    N, goal_z, d, start = _parse_input(inp)
    goal = _goal_board(N, goal_z, d)

    # Expected optimal length if provided
    exp_path = input_path[:-3] + "out" if input_path.endswith(".in") else None
    opt_len = _read_expected_len(exp_path) if exp_path else None

    try:
        K, moves = _parse_student_out(out_text)
    except Exception as e:
        return {"status":"WA", "note":str(e)}

    # Unsolvable claim
    if K == -1:
        uns = not _is_solvable(start, goal, d)
        if not uns:
            return {"status":"WA", "note":"claimed unsolvable but puzzle is solvable"}
        res = {"status":"OK", "correct":True, "complete":True, "optimal": (opt_len == -1 if opt_len is not None else True)}
        if opt_len is not None and opt_len != -1:
            res["note"] = f"expected {opt_len}, got -1"
        return res

    # K==0 must already be goal
    if K == 0:
        if not _boards_equal(start, goal):
            return {"status":"WA", "note":"reported 0 moves but not at goal"}
        res = {"status":"OK", "correct":True, "complete":True}
        if opt_len is not None:
            res["optimal"] = (opt_len == 0)
            if opt_len != 0:
                res["note"] = f"non-optimal: 0 != {opt_len}"
        return res

    # Standard validation: exactly K moves and reach goal
    if len(moves) != K:
        return {"status":"WA", "note":"K does not match number of moves"}

    legal = {"left","right","up","down"}
    board = [row[:] for row in start]
    for i,mv in enumerate(moves, start=1):
        if mv not in legal:
            return {"status":"WA", "note":f"illegal token at step {i}: {mv}"}
        if not _apply_move(board, mv, d):
            return {"status":"WA", "note":f"illegal move at step {i}: {mv}"}
    if not _boards_equal(board, goal):
        return {"status":"WA", "note":"does not reach goal"}

    res = {"status":"OK", "correct":True, "complete":True}
    if opt_len is not None:
        res["optimal"] = (K == opt_len)
        if K != opt_len:
            res["note"] = f"non-optimal: {K} != {opt_len}"
    return res
