import argparse, json, os, sys, time, subprocess, shlex, runpy, re
from glob import glob
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

try:
    import importlib.resources as ir
except ImportError:
    import importlib_resources as ir

from fmi_ai_judge import __version__

# --- Simple defaults ---
EXTRA_FAST_MS = 25        # calibration: accepted time = time_ms - EXTRA
EXTRA_SLOW_MS = 200
HARD_KILL_MS = 5000       # 5s extra beyond (budget + EXTRA) before we kill the process
SLOW_EXTS = {".py",".js",".ts",".rb",".php",".jl",".ps1",".sh"}
WIN_EXE_EXTS = [".exe", ".bat", ".cmd", ".com"]

# --- Helpers ---
def _norm_text(s: str) -> str:
    return s.replace("\r\n","\n").replace("\r","\n").lstrip("\ufeff").strip()

def load_registry() -> Dict[str,Any]:
    with ir.files("fmi_ai_judge").joinpath("problems.yaml").open("r",encoding="utf-8") as f:
        import yaml; return yaml.safe_load(f)["problems"]

def normalize_alias(s: str) -> str:
    s = s.strip().lower()
    for ch in " _.": s = s.replace(ch,"-")
    return re.sub("-+","-",s)

def resolve_problem(token: Optional[str], registry: dict, path: Path) -> Optional[str]:
    # 1) explicit token
    if token:
        tok = normalize_alias(token)
        for pid, meta in registry.items():
            names = [pid] + list(meta.get("aliases",[]))
            if tok in [normalize_alias(x) for x in names]:
                return pid
        return None
    # 2) infer from filename
    name = normalize_alias(path.name)
    for pid, meta in registry.items():
        names = [pid] + [normalize_alias(x) for x in meta.get("aliases",[])]
        if any(a in name for a in names):
            return pid
    return None

def prob_dir(pid: str) -> Path:
    return ir.files("fmi_ai_judge").joinpath("tests").joinpath(pid)

def list_test_ids(pid: str) -> List[str]:
    root = prob_dir(pid)
    if not root.exists(): return []
    ids = set()
    for p in root.iterdir():
        if p.suffix == ".in": ids.add(p.stem)
    return sorted(ids)

def load_manifest(pid: str) -> Dict[str,Any]:
    y = prob_dir(pid)/"tests.yaml"
    if not y.exists(): return {"defaults":{},"tests":[]}
    import yaml; return yaml.safe_load(y.read_text(encoding="utf-8")) or {"defaults":{},"tests":[]}

def paths_for(pid: str, tid: str) -> Dict[str,Path]:
    root = prob_dir(pid)
    return {
        "in": root/f"{tid}.in",
        "out": root/f"{tid}.out",
        "re":  root/f"{tid}.re",
        "check": root/f"{tid}.check.py",
        "problem_check": root/"check.py",
    }

def is_exe(p: Path) -> bool:
    if os.name == "nt":
        # exact extension
        if p.suffix.lower() in WIN_EXE_EXTS and p.exists():
            return True
        # bare name → check sibling with known extensions
        if p.suffix == "":
            for ext in WIN_EXE_EXTS:
                if p.with_suffix(ext).exists():
                    return True
        return False
    # POSIX: normal x-bit file is fine (works for extensionless ELF/Mach-O)
    return p.is_file() and os.access(p, os.X_OK)

def _resolve_windows_exe(p: Path) -> Optional[Path]:
    if p.suffix.lower() in WIN_EXE_EXTS and p.exists():
        return p
    if p.suffix == "":
        for ext in WIN_EXE_EXTS:
            q = p.with_suffix(ext)
            if q.exists():
                return q
    return None

def detect_cmd_and_tier(src: Path) -> Tuple[Optional[List[str]], str]:
    # Try resolving bare names on Windows even if the exact path isn't a file
    if os.name == "nt":
        q = _resolve_windows_exe(src)
        if q is not None:
            return ([str(q)], "fast")

    if src.is_file():
        suf = src.suffix.lower()
        if is_exe(src):           return ([str(src)], "fast")
        if suf == ".dll":         return (["dotnet", str(src)], "fast")
        if suf == ".jar":         return (["java","-jar",str(src)], "fast")
        if suf == ".class":       return (["java","-cp",str(src.parent), src.stem], "fast")
        if suf in SLOW_EXTS:
            mapping = {
                ".py": ["python","{src}"], ".js": ["node","{src}"],
                ".ts": ["deno","run","{src}"], ".rb":["ruby","{src}"],
                ".php": ["php","{src}"], ".jl": ["julia","{src}"],
                ".ps1":["powershell","-ExecutionPolicy","Bypass","-File","{src}"],
                ".sh":["bash","{src}"]
            }
            return ([c.format(src=str(src)) for c in mapping[suf]], "slow")
        return (None, "slow")

    return (None, "slow")

def run_command(cmd: List[str], stdin_path: Path, timeout_s: float, env: Optional[dict]=None) -> Tuple[str, bytes, bytes, int]:
    start = time.perf_counter()
    try:
        with stdin_path.open("rb") as fi:
            p = subprocess.Popen(cmd, stdin=fi, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, env=env)
            try:
                out, err = p.communicate(timeout=timeout_s)
                tms = int((time.perf_counter()-start)*1000)
                return (str(p.returncode), out, err, tms)
            except subprocess.TimeoutExpired:
                try: p.kill()
                except Exception: pass
                _ = p.communicate()
                tms = int((time.perf_counter()-start)*1000)
                return ("TLE", b"", b"", tms)
    except FileNotFoundError:
        tms = int((time.perf_counter()-start)*1000)
        return ("RTE", b"", f"exec not found: {cmd[0]}".encode(), tms)

# header parse: "# TIMES_MS: in=.. alg=.."
_TIMES = re.compile(r"^\s*#\s*TIMES_MS:\s*(.*)$", re.I)
def strip_header_and_times(out: bytes) -> Tuple[bytes, Optional[int]]:
    try:
        txt = out.decode("utf-8", errors="replace")
    except Exception:
        return out, None
    lines = txt.splitlines()
    if not lines: return out, None
    m = _TIMES.match(lines[0])
    if not m: return out, None
    alg = None
    mm = re.search(r"\balg\s*=\s*([0-9]+(?:\.[0-9]+)?)", m.group(1), re.I)
    if mm: alg = int(float(mm.group(1)))
    cleaned = "\n".join(lines[1:]).encode("utf-8")
    return cleaned, alg

def run_checker(paths: Dict[str,Path], out_bytes: bytes) -> Dict[str,Any]:
    out_text = _norm_text(out_bytes.decode("utf-8", errors="replace"))
    # prefer per-problem checker
    if paths["check"].exists():
        env = runpy.run_path(str(paths["check"]))
        return env["check"](str(paths["in"]), out_text, {})
    if paths["problem_check"].exists():
        env = runpy.run_path(str(paths["problem_check"]))
        return env["check"](str(paths["in"]), out_text, {})
    # otherwise exact/regex fallback
    if paths["re"].exists():
        pat = _norm_text(paths["re"].read_text(encoding="utf-8"))
        ok = re.fullmatch(pat, out_text, flags=re.DOTALL) is not None
        return {"status":"OK" if ok else "WA", "correct":ok, "complete":ok}
    if paths["out"].exists():
        ok = _norm_text(paths["out"].read_text(encoding="utf-8")) == out_text
        return {"status":"OK" if ok else "WA", "correct":ok, "complete":ok}
    return {"status":"RTE","note":"no expected output/checker"}

# --- Results ---
@dataclass
class Row:
    problem: str
    test: str
    status: str
    time_ms: int
    time_budget_ms: int
    tier: str
    correct: bool
    complete: bool
    optimal: Optional[bool]
    note: Optional[str]
    time_alg_ms: Optional[int] = None
    time_cal_ms: Optional[int] = None

def print_table(rows: List[Row]):
    # Header + divider
    h = ("problem", "test", "status", "time(ms)", "limit", "alg(ms)", "cal(ms)", "note")
    print(f"{h[0]:12} {h[1]:4}  {h[2]:6}  {h[3]:8}  {h[4]:5}  {h[5]:7}  {h[6]:7}   {h[7]}")
    print(f"{'-'*12} {'-'*4}  {'-'*6}  {'-'*8}  {'-'*5}  {'-'*7}  {'-'*7}   {'-'*32}")
    # Rows
    for r in rows:
        print(
            f"{r.problem:12} {r.test:4}  {r.status:6}  {r.time_ms:8}  {r.time_budget_ms:5}  "
            f"{'' if r.time_alg_ms is None else r.time_alg_ms:7}  "
            f"{'' if r.time_cal_ms is None else r.time_cal_ms:7}   {r.note or ''}"
        )

def write_artifacts(rows: List[Row], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    j = out_dir/"results.json"; c = out_dir/"results.csv"
    j.write_text(json.dumps([r.__dict__ for r in rows], ensure_ascii=False, indent=2), encoding="utf-8")
    with c.open("w", encoding="utf-8") as f:
        f.write("problem,test,status,time_ms,time_budget_ms,tier,correct,complete,optimal,time_alg_ms,time_cal_ms,note\n")
        for r in rows:
            note_csv = (r.note or "").replace(",", ";").replace("\n", " ").strip()
            f.write(
                f"{r.problem},{r.test},{r.status},{r.time_ms},{r.time_budget_ms},{r.tier},"
                f"{str(r.correct).lower()},{str(r.complete).lower()},"
                f"{'' if r.optimal is None else str(r.optimal).lower()},"
                f"{'' if r.time_alg_ms is None else r.time_alg_ms},"
                f"{'' if r.time_cal_ms is None else r.time_cal_ms},"
                f"{note_csv}\n"
            )
    print(f"Artifacts: {j}  {c}")

# --- CLI ---
def main():
    reg = load_registry()
    ap = argparse.ArgumentParser(
        prog="judge",
        description="Run AI homework solutions against official tests."
    )
    # Expose CLI version (reads the package’s installed version)
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List problems")

    rp = sub.add_parser("run", help="Run one or more programs")
    rp.add_argument("--fail-fast", action="store_true", help="Abort immediately on unresolved problem during discovery")
    rp.add_argument("--problem", "-p", help="Problem id or alias (e.g., frog-leap, flp)")
    rp.add_argument("--slow", action="store_true", help="Use slow tier timing for all programs")
    rp.add_argument("--exec", type=str, help="Override runner, e.g. 'python {src}'")
    rp.add_argument("--bench", action="store_true", help="Parse '# TIMES_MS: alg=..' header on stdout")
    rp.add_argument("--out", default=".judge", help="Artifacts directory")
    rp.add_argument("paths", nargs="+", help="Program paths")

    args = ap.parse_args()

    if args.cmd == "list":
        print("Known problems:")
        for pid, meta in reg.items():
            als = ", ".join(meta.get("aliases", []))
            print(f"- {pid} ({als})")
        return

    # Expand wildcards (PowerShell doesn’t expand for external cmds)
    expanded = []
    for p in args.paths:
        if any(ch in p for ch in "*?[]"):
            matches = sorted(glob(p))
            # if nothing matched, keep the original so errors are clear
            expanded.extend(matches if matches else [p])
        else:
            expanded.append(p)
    args.paths = expanded

    # If a path is a directory, expand to files inside (simple heuristic)
    tmp = []
    for p in args.paths:
        pp = Path(p)
        if pp.is_dir():
            # include common runnable files; tweak as you like
            files = sorted(
                list(pp.glob("*.py")) + list(pp.glob("*.exe")) +
                list(pp.glob("*.jar")) + list(pp.glob("*.dll")) +
                list(pp.glob("*.class")) + list(pp.glob("run.*"))
            )
            tmp.extend(files if files else [pp])
        else:
            tmp.append(pp)
    args.paths = [str(x) for x in tmp]

    all_rows: List[Row] = []
    for path_str in args.paths:
        rows: List[Row] = []
        src = Path(path_str).resolve()
        pid = resolve_problem(args.problem, reg, src)
        if pid is None:
            note = f"cannot infer problem for file: {src.name}; use --problem"
            print(f"Warning: {note}", file=sys.stderr)  # stderr hint
            rows = [Row(str(src.name), "-", "RTE", 0, 0, "-", False, False, None, note)]
            print_table(rows)
            print("-" * 95)
            print()
            all_rows.extend(rows)
            if args.fail_fast:
                write_artifacts(all_rows, Path(args.out))
                sys.exit(2)
            continue

        # build command
        if args.exec:
            cmd = [s.format(src=str(src), exe=str(src), cp=str(src.parent)) for s in shlex.split(args.exec)]
            tier = "slow" if (args.slow or any(x in args.exec for x in ("python","node","deno","ruby","php","julia","powershell","bash"))) else "fast"
        else:
            cmd, tier_auto = detect_cmd_and_tier(src)
            tier = "slow" if args.slow else (tier_auto or "fast")
            if cmd is None:
                print(f"[{pid}] No runnable entrypoint; supply --exec", file=sys.stderr)
                rows.append(Row(pid,"-","NOENTRY",0,0,tier,False,False,None,"no entrypoint"))
                # PRINT + APPEND BEFORE CONTINUE
                print_table(rows)
                print("-" * 95)
                print()
                all_rows.extend(rows)
                continue

        manifest = load_manifest(pid)
        defaults = manifest.get("defaults", {})
        test_ids = list_test_ids(pid)
        if not test_ids:
            rows.append(Row(pid,"-","RTE",0,0,tier,False,False,None,"no tests"))
            # PRINT + APPEND BEFORE CONTINUE
            print_table(rows)
            print("-" * 95)
            print()
            all_rows.extend(rows)
            continue

        tests_cfg = {t["id"]: t for t in manifest.get("tests", []) if isinstance(t, dict) and "id" in t}

        # ---------- per-test loop with repeats aggregation ----------
        for tid in test_ids:
            p = paths_for(pid, tid)
            if not p["in"].exists():
                rows.append(Row(pid,tid,"RTE",0,0,tier,False,False,None,"missing .in")); continue

            tc = tests_cfg.get(tid, {})
            repeats = int(tc.get("repeats", 1))
            min_success = int(tc.get("min_success", repeats))

            # local helper: one execution → Row
            def run_once() -> Row:
                # budgets
                base = tc.get("timeout", defaults.get("timeout", 1.0))
                if (tier=="slow"):
                    budget_s = float(tc.get("timeout_slow", defaults.get("timeout_slow", base)))
                else:
                    budget_s = float(base)
                budget_ms = int(budget_s*1000)
                extra_ms = EXTRA_SLOW_MS if tier=="slow" else EXTRA_FAST_MS
                effective_ms = budget_ms + extra_ms
                timeout_s = budget_s + extra_ms/1000.0

                # env (time-only hint)
                env = os.environ.copy()
                time_only = bool(tc.get("time_only", defaults.get("time_only", False)))
                if time_only:
                    env["FMI_TIME_ONLY"] = "1"

                # run process
                rc, out, err, tms = run_command(cmd, p["in"], timeout_s + HARD_KILL_MS/1000.0, env=env)

                # computed timings
                time_cal = max(tms - extra_ms, 0)
                over_ms = max(tms - effective_ms, 0)

                # hard kill → TLE
                if rc == "TLE":
                    note = f"over time (+{over_ms}ms; eff={effective_ms}ms)"
                    return Row(pid, tid, "TLE", tms, budget_ms, tier, False, False, None, note,
                               time_alg_ms=None, time_cal_ms=time_cal)

                # parse header first (if requested)
                alg_ms = None
                out_bytes = out
                if args.bench:
                    out_bytes, alg_ms = strip_header_and_times(out)

                # non-zero exit → RTE
                if rc != "0":
                    note_msg = f"exit {rc}"
                    if rc == "RTE" and err:
                        try:
                            note_msg = err.decode("utf-8", errors="replace")
                        except Exception:
                            pass
                    return Row(pid, tid, "RTE", tms, budget_ms, tier,
                               False, False, None, note_msg.strip(),
                               time_alg_ms=alg_ms, time_cal_ms=time_cal)

                # soft over-time → TLE (keep times in note)
                if tms > effective_ms:
                    note = f"over time (+{over_ms}ms; eff={effective_ms}ms)"
                    if args.bench and alg_ms is not None:
                        alg_over = max(alg_ms - budget_ms, 0)
                        note += f"; alg={alg_ms}ms" + (f" (+{alg_over}ms)" if alg_over > 0 else "")
                    return Row(pid, tid, "TLE", tms, budget_ms, tier, False, False, None, note,
                               time_alg_ms=alg_ms, time_cal_ms=time_cal)

                # time-only path
                if time_only:
                    status = "OK" if time_cal <= budget_ms else "TLE"
                    note = "time-only"
                    if status == "TLE":
                        note += f"; over time (+{over_ms}ms; eff={effective_ms}ms)"
                        if args.bench and alg_ms is not None:
                            alg_over = max(alg_ms - budget_ms, 0)
                            note += f"; alg={alg_ms}ms" + (f" (+{alg_over}ms)" if alg_over > 0 else "")
                    return Row(pid, tid, status, tms, budget_ms, tier, True, True, None, note,
                               time_alg_ms=alg_ms, time_cal_ms=time_cal)

                # correctness via checker
                res = run_checker(p, out_bytes)
                status = res.get("status","WA")
                correct = bool(res.get("correct", status=="OK"))
                complete = bool(res.get("complete", status=="OK"))
                optimal = res.get("optimal", None)
                note = res.get("note")

                # enforce require_optimal
                require_optimal = bool(tc.get("require_optimal", defaults.get("require_optimal", False)))
                if status == "OK" and require_optimal and (optimal is False):
                    status = "WA"
                    note = (note + "; " if note else "") + "non-optimal"

                # calibrated pass hint
                if status == "OK" and tms > budget_ms and time_cal <= budget_ms:
                    note = (note+"; " if note else "") + "calibrated pass"

                return Row(pid, tid, status, tms, budget_ms, tier, correct, complete, optimal, note,
                           time_alg_ms=alg_ms, time_cal_ms=time_cal)

            # run repetitions and aggregate
            runs: List[Row] = [run_once() for _ in range(repeats)]
            succ = sum(1 for r in runs if r.status == "OK")

            if succ >= min_success:
                ok_rows = [r for r in runs if r.status == "OK"]
                final = min(ok_rows, key=lambda r: r.time_ms)
                final.status = "OK"
            else:
                # preserve failure severity: TLE > RTE > WA
                if any(r.status == "TLE" for r in runs):
                    tle_rows = [r for r in runs if r.status == "TLE"]
                    final = min(tle_rows, key=lambda r: r.time_ms)
                    final.status = "TLE"
                elif any(r.status == "RTE" for r in runs):
                    rte_rows = [r for r in runs if r.status == "RTE"]
                    final = rte_rows[0]
                    final.status = "RTE"
                else:
                    wa_rows = [r for r in runs if r.status == "WA"] or runs
                    final = min(wa_rows, key=lambda r: r.time_ms)
                    final.status = "WA"

            # append runs summary to note
            note = (final.note or "")
            note += ("" if not note else " ") + f"(runs: {succ}/{repeats} OK)"
            final.note = note

            rows.append(final)
        
        print_table(rows)
        print("-" * 95)     # visual separator between problems
        print()

        all_rows.extend(rows)

    write_artifacts(all_rows, Path(args.out))

    if any(r.status not in ("OK",) for r in all_rows):
        sys.exit(1)

if __name__ == "__main__":
    main()
