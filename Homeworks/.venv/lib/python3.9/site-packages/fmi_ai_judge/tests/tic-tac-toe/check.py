# Tic-Tac-Toe checker
import re

# --------- Board parsing (boxed only) ----------
# Expect exactly 7 lines (3 rows framed by +---+ and | c | c | c | lines)
_BOX_TOP    = re.compile(r"^\+---\+---\+---\+$")
_BOX_ROW    = re.compile(r"^\|\s([XO_])\s\|\s([XO_])\s\|\s([XO_])\s\|$")
_BOX_SEP    = re.compile(r"^\+---\+---\+---\+$")
_SYM        = {"X","O","_"}

WIN_LINES = [
    (0,1,2),(3,4,5),(6,7,8),    # rows
    (0,3,6),(1,4,7),(2,5,8),    # cols
    (0,4,8),(2,4,6)             # diags
]

def _winner(b):
    for a,b2,c in WIN_LINES:
        if b[a] != '_' and b[a] == b[b2] == b[c]:
            return b[a]
    return None

def _terminal(b):
    return _winner(b) is not None or all(x != '_' for x in b)

def _value_of(b):  # from X's perspective
    w = _winner(b)
    if w == 'X': return +1
    if w == 'O': return -1
    return 0

def _opp(p): return 'O' if p == 'X' else 'X'

def _legal_moves(b):
    for i,ch in enumerate(b):
        if ch == '_':
            yield (i//3+1, i%3+1)

def _apply(b, r, c, p):
    i = (r-1)*3 + (c-1)
    if not (1<=r<=3 and 1<=c<=3) or b[i] != '_':
        return None
    nb = list(b); nb[i] = p; return nb

# Compare (value, dist) with tie-break “win-asap / lose-as-late”
def _better_for(player, a, b):
    va,da = a; vb,db = b
    if player == 'X':
        if va != vb: return va > vb
        if va == +1: return da < db      # win sooner
        if va == -1: return da > db      # lose later
        return False                     # draw: keep first
    else:  # O minimizes
        if va != vb: return va < vb
        if va == -1: return da < db      # O wins sooner
        if va == +1: return da > db      # O loses later
        return False

def _ge_for(player, a, b):  # a >= b in player's ordering
    return not _better_for(player, b, a)

def _search(b, to_move, alpha=(-2, 10**9), beta=(+2, 10**9)):
    """
    Depth-aware alpha-beta. Returns ((val,dist), best_moves)
    val in {-1,0,+1} from X's perspective; dist = plies to end under optimal play.
    best_moves is a list of (r,c) optimal choices per tie-break.
    """
    if _terminal(b):
        return (_value_of(b), 0), []

    best = None
    best_moves = []
    for (r,c) in _legal_moves(b):
        nb = _apply(b, r, c, to_move)
        (vc, dc), _ = _search(nb, _opp(to_move), alpha, beta)
        cand = (vc, dc+1)

        if best is None or _better_for(to_move, cand, best):
            best = cand
            best_moves = [(r,c)]
        elif cand == best:
            best_moves.append((r,c))

        # update alpha/beta under same ordering
        if to_move == 'X':
            if _better_for('X', cand, alpha): alpha = cand
        else:
            if _better_for('O', cand, beta):  beta  = cand

        if _ge_for('X', alpha, beta):
            break

    return best, best_moves

def _parse_boxed(lines, start=0):
    # expects 7 lines: top, row, sep, row, sep, row, sep
    if start + 6 >= len(lines): return None, start
    if not _BOX_TOP.match(lines[start]): return None, start
    b = []
    idx = start
    idx += 1
    for r in range(3):
        m = _BOX_ROW.match(lines[idx]); 
        if not m: return None, start
        row = list(m.groups())
        if any(s not in _SYM for s in row): return None, start
        b.extend(row)
        idx += 1
        if not _BOX_SEP.match(lines[idx]): return None, start
        idx += 1
    return b, idx

def _strip_header(out_lines):
    if out_lines and out_lines[0].strip().lower().startswith("# times_ms:"):
        return out_lines[1:]
    return out_lines

def check(in_path: str, out_text: str, _ctx: dict):
    # Read input
    with open(in_path, "r", encoding="utf-8") as f:
        raw = [ln.rstrip("\n") for ln in f]
    raw = [ln for ln in raw if ln.strip()]

    if not raw:
        return {"status":"RTE","note":"empty .in"}

    mode = raw[0].strip().upper()
    if mode != "JUDGE":
        # We only grade JUDGE in the test suite; GAME is interactive.
        return {"status":"RTE","note":"tests expect JUDGE mode"}

    # JUDGE format (new, fixed):
    # JUDGE
    # TURN X|O
    # <boxed board: 7 lines>
    if len(raw) < 9:
        return {"status":"RTE","note":"JUDGE input too short"}

    # Parse TURN line
    m = re.match(r"^TURN\s+([XO])$", raw[1].strip(), flags=re.IGNORECASE)
    if not m:
        return {"status":"RTE","note":"expected 'TURN X' or 'TURN O' on the 2nd line"}
    to_move = m.group(1).upper()

    # Parse boxed board starting at line 3 (index 2)
    b, k = _parse_boxed(raw, 2)
    if b is None:
        return {"status":"RTE","note":"invalid boxed board"}

    # Compute optimal move set
    if _terminal(b):
        best, best_moves = (_value_of(b), 0), []
    else:
        best, best_moves = _search(b, to_move)

    # Parse output
    out_lines = [ln.rstrip("\n") for ln in out_text.splitlines()]
    out_lines = _strip_header(out_lines)
    out_lines = [ln for ln in out_lines if ln.strip()]

    if not out_lines:
        return {"status":"WA","note":"missing output"}

    # Terminal: expect -1
    if _terminal(b):
        if out_lines[0].strip() == "-1":
            return {"status":"OK","correct":True,"complete":True}
        return {"status":"WA","note":"terminal position: expected -1"}

    # Non-terminal: expect "r c"
    try:
        parts = out_lines[0].split()
        r, c = int(parts[0]), int(parts[1])
    except Exception:
        return {"status":"WA","note":"first line must be 'r c' (1..3)"}

    if not (1<=r<=3 and 1<=c<=3):
        return {"status":"WA","note":"move out of range"}
    i = (r-1)*3 + (c-1)
    if b[i] != '_':
        return {"status":"WA","note":"illegal move (cell not empty)"}

    # Enforce optimality with tie-break
    if (r,c) not in best_moves:
        return {"status":"WA","note":"suboptimal: violates win-now/lose-late tie-break"}

    return {"status":"OK","correct":True,"complete":True}
