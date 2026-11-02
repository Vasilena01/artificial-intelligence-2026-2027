# N-Queens — Running Against FMI AI Judge

## Step 1: Install judge tool

Separate venv recommended.

```bash
cd "/Users/I765637/Library/CloudStorage/OneDrive-SAPSE/Documents/Uni/Course 4/IS/Homeworks/HW2-N-Queens"
python3 -m venv venv
source venv/bin/activate
pip install fmi-ai-judge
```

Update later:
```bash
pip install -U fmi-ai-judge
```

## Step 2: Filename handling

Judge auto-detects problem by filename (`nq`, `nqueens`, `n-queens`). Our file is `HW2.py`.

Two options:

**A: Rename**
```bash
cp HW2.py nqueens.py
```

**B: Pass problem explicitly** (preferred — keeps filename)
```bash
judge run -p n-queens HW2.py
```

## Step 3: Smoke test manually

Before running judge, verify output format locally.

```bash
echo "4" | python3 HW2.py
echo "100" | python3 HW2.py --print-board
echo "1000" | FMI_TIME_ONLY=1 python3 HW2.py
echo "2" | python3 HW2.py        # should print -1
echo "1" | python3 HW2.py        # should print [0]
```

Expected format:
- Timing line: `# TIMES_MS: alg=0.075`
- Solution: `[1, 3, 0, 2]`
- Board (with --print-board): `_ _ * _` style rows

## Step 4: Run judge (correctness only)

```bash
judge run -p n-queens HW2.py
```

No `--bench` → only correctness check, no timing.

## Step 5: Run judge with benchmark

```bash
judge run --bench -p n-queens HW2.py
```

With `--bench`: includes timing report, runs performance tests. Judge sets `FMI_TIME_ONLY=1` for large tests.

## Step 6: Interpret output

| Verdict | Meaning | Fix |
|---------|---------|-----|
| PASS | Test ok | — |
| Wrong Answer | Output doesn't match | Check correctness, verify format |
| Timeout | Too slow | Optimize or accept partial |
| Format Error | Brackets/commas off | Check `print(solution)` format |

## Expected results

| N | Expected |
|---|----------|
| 1 | PASS |
| 2, 3 | PASS (prints -1) |
| 4..1000 | PASS |
| 5000 | PASS (~0.6s) |
| 10000 | likely TIMEOUT (~1.2-1.5s observed, budget 1s) |

## Full command sequence (copy-paste)

```bash
cd "/Users/I765637/Library/CloudStorage/OneDrive-SAPSE/Documents/Uni/Course 4/IS/Homeworks/HW2-N-Queens"
python3 -m venv venv
source venv/bin/activate
pip install fmi-ai-judge
judge run --bench -p n-queens HW2.py
```

## If judge doesn't recognize file

Pass interpreter explicitly:
```bash
judge run --bench -p n-queens --exec "python3 {src}" HW2.py
```

## Troubleshooting

**`judge: command not found`**
Venv not activated. Run `source venv/bin/activate` again.

**Judge hangs on large N**
Timeout. N=10000 may exceed 1s budget in Python. Options:
- Switch to C++ reference solution (fastest)
- Try NumPy rewrite
- Accept partial score

**Wrong answer on small N**
Check `verify()` output locally:
```bash
python3 -c "from HW2 import solve, verify; s = solve(100); print(verify(s, 100), s[:10])"
```
