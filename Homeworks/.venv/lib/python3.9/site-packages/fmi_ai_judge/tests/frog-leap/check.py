# Validates a frog-leap solution (ignores comment lines starting with '#')
def _norm(s): return s.replace("\r\n","\n").replace("\r","\n").lstrip("\ufeff").strip()
LEFT, RIGHT, EMPTY = ">", "<", "_"

def ok_step(a, b):
    if len(a) != len(b): return False
    try:
        i = a.index(EMPTY); j = b.index(EMPTY)
    except ValueError:
        return False
    d = j - i
    if d not in (-2, -1, 1, 2): return False
    if d == -1 and a[i-1] == LEFT:  return True
    if d ==  1 and a[i+1] == RIGHT: return True
    if d == -2 and a[i-2] == LEFT and a[i-1] == RIGHT:  return True
    if d ==  2 and a[i+1] == LEFT and a[i+2] == RIGHT:  return True
    return False

def initial(n): return LEFT*n + EMPTY + RIGHT*n
def goal(n):    return RIGHT*n + EMPTY + LEFT*n

def check(stdin_path, stdout_text, options):
    n = int(open(stdin_path, "r", encoding="utf-8").read().strip())
    lines = [ln.strip() for ln in _norm(stdout_text).splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return {"status":"WA","note":"no states"}

    if lines[0] != initial(n):  return {"status":"WA","note":"wrong start"}
    if lines[-1] != goal(n):    return {"status":"WA","note":"wrong goal"}

    for a, b in zip(lines, lines[1:]):
        if not ok_step(a, b):
            return {"status":"WA","note":"illegal step"}

    min_states = (n + 1) ** 2
    if len(lines) != min_states:
        return {"status":"WA","note":"wrong number of states"}

    return {"status":"OK","correct":True,"complete":True,"optimal":True}
