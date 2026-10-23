"""Main thread for the full run: several tasks, groups A / B / Bx4 / C, one model.

Jobs per task (dependencies in DEPS; at most CONCURRENCY kiro-cli processes at a time):
  A_direct            one call, no tools, deliverable parsed from the reply
  B_1 .. B_4          the fixed minimal harness, 4 independent runs.
                      B = B_1; C reuses B_1 as its reference run; Bx4 picks one of B_1..B_4
  Bx4_select          selector call (same model): picks one attempt without hidden data
  C_propose -> C_probe_general || C_probe_specific -> C_compose -> C_final   (H2-lite)
Then every task's grader runs and report_full.py writes runs/<label>/report.md.

Fixed rules (decided before any full-run result exists):
  - infrastructure failure of a call (kiro-cli ends without success and without hitting the
    time limit): up to 2 re-runs; still failing -> the job is unscored and reported as such
  - an agent run that hits the time limit is a valid result (its workspace is graded as is)
  - improver output unusable after one retry: C has no deliverable for that task (scored 0)
  - selector output unusable after one retry: Bx4 takes the attempt with the best provided-test
    pass rate (ties and tasks without provided tests: the lowest attempt number)
  - no new job starts once recorded credits exceed --credit-cap
This script makes no experimental judgement; the model makes every choice inside C and Bx4.

Usage
  python3 run_full.py --label full1 --detach            start in its own session, return
  python3 run_full.py --label full1 --resume --detach   continue after an interruption
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

import common
from common import (AGENT_RUN_TIMEOUT_S, CONCURRENCY, ENGINE, KIRO, PROMPTS_DIR, PY, ROOT,
                    RUNS_DIR, SINGLE_CALL_TIMEOUT_S, now_iso, read_json, sha256_file, write_json)
from kiro_runner import Heartbeat, digest, install_agent, new_workspace, run_kiro, summarize
from tasklib import Task

DEFAULT_TASKS = ["humaneval", "commonmark", "jsonschema", "swe1", "swe2"]
DEFAULT_CAP = 300.0
INFRA_RETRIES = 2
N_BX = 4
B_RUNS = [f"B_{i}" for i in range(1, N_BX + 1)]
JOB_ORDER = ["A_direct", "B_1", "C_propose", "C_probe_general", "C_probe_specific", "C_compose",
             "C_final", "B_2", "B_3", "B_4", "Bx4_select"]
DEPS = {"A_direct": [], **{b: [] for b in B_RUNS}, "Bx4_select": B_RUNS,
        "C_propose": ["B_1"], "C_probe_general": ["C_propose"], "C_probe_specific": ["C_propose"],
        "C_compose": ["C_probe_general", "C_probe_specific"], "C_final": ["C_compose"]}
GROUP = {"A_direct": "A", "B_1": "B/Bx4/C", **{b: "Bx4" for b in B_RUNS[1:]}, "Bx4_select": "Bx4",
         "C_propose": "C", "C_probe_general": "C", "C_probe_specific": "C", "C_compose": "C",
         "C_final": "C"}
OK = ("success", "timed_out")  # usable outcomes of an agent / direct run


def prompt_file(name):
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def tag(text, name):
    m = re.search(rf"<{name}>\s*(.*?)\s*</{name}>", text or "", re.S)
    return m.group(1).strip() if m else None


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, TypeError):
        return False


class JobFailed(Exception):
    def __init__(self, msg, kind):
        super().__init__(msg)
        self.kind = kind  # "infra" | "format"


class Full:
    def __init__(self, args):
        self.label, self.root = args.label, RUNS_DIR / args.label
        self.cap = args.credit_cap
        self.tasks = {t: Task(t) for t in args.tasks}
        self.order = list(args.tasks)
        self.status_path = self.root / "status.json"
        if args.resume:
            self.state = read_json(self.status_path)
            self.state.setdefault("resumes", []).append(now_iso())
        else:
            self.state = {"label": self.label, "kind": "full", "model": common.MODEL,
                          "effort": common.EFFORT, "tasks": self.order, "credit_cap": self.cap,
                          "only_jobs": args.jobs,
                          "started": now_iso(), "finished": False, "error": None,
                          "stopped_for_budget": False, "credits_total": 0.0,
                          "credits_overhead": 0.0, "jobs": {}, "running": []}
        self.only = set(self.state.get("only_jobs") or JOB_ORDER)
        self.hb = Heartbeat(self.status_path, self.state)
        self._log = open(self.root / "run.log", "a", encoding="utf-8")
        self._loglock = threading.Lock()

    # ---- bookkeeping ------------------------------------------------------
    def log(self, msg):
        with self._loglock:
            self._log.write(f"[{now_iso()}] {msg}\n")
            self._log.flush()

    def job(self, key):
        return self.state["jobs"].setdefault(key, {})

    def _retotal(self):
        """Caller holds hb.lock."""
        self.state["credits_total"] = round(
            sum(j.get("credits") or 0 for j in self.state["jobs"].values())
            + self.state.get("credits_overhead", 0.0), 4)

    def update(self, key, **kw):
        with self.hb.lock:
            self.state["jobs"].setdefault(key, {}).update(kw)
            self._retotal()
        self.hb.write()

    def add_overhead(self, credits, why):
        """Credits spent outside any job's own result (infra failures, aborted attempts)."""
        with self.hb.lock:
            self.state["credits_overhead"] = round(self.state.get("credits_overhead", 0.0) + credits, 4)
            self.state.setdefault("overhead_notes", []).append(f"{now_iso()} {why}: {credits}")
            self._retotal()
        self.hb.write()

    def jdir(self, task, name):
        return self.root / task / name

    def done(self, key):
        return self.state["jobs"].get(key, {}).get("state") in ("ok", "failed", "skipped")

    def ok(self, key):
        return self.state["jobs"].get(key, {}).get("state") == "ok"

    # ---- one kiro-cli call with infra retries -------------------------------
    def call(self, key, d, agent, sys_prompt, user_prompt, timeout_s, template, task=None, rules=None):
        """Run one kiro-cli call in <d>; re-run on infrastructure failure. Returns (summary, ws)."""
        for attempt in range(INFRA_RETRIES + 1):
            if attempt:
                failed = d.with_name(f"{d.name}.infra{attempt}")
                shutil.move(str(d), str(failed))
            d.mkdir(parents=True, exist_ok=True)
            ws = new_workspace(template, d / "ws")
            if task is not None:
                task.setup(ws, d, self.log)
            install_agent(ws, agent, sys_prompt, rules)
            s = run_kiro(ws, agent, user_prompt, d / "run", timeout_s,
                         on_start=lambda pid: self.update(key, pid=pid))
            s["status"] = "timed_out" if s["timed_out"] else s["status"]
            if s["status"] in OK:
                if attempt:
                    self.update(key, infra_retries=attempt)
                return s, ws
            self.log(f"{key}: infrastructure failure #{attempt + 1}: status={s['status']} "
                     f"exit={s['exit_code']} stderr={(d / 'run' / 'stderr.txt').read_text(errors='replace')[-300:]!r}")
            self.add_overhead(s["credits"], f"{key} infra failure #{attempt + 1}")
        raise JobFailed(f"{key}: still failing after {INFRA_RETRIES} re-runs", "infra")

    def record_run(self, key, d, s, vis):
        self.update(key, status=s["status"], credits=s["credits"], wall_s=s["wall_s"],
                    tool_calls=s["tool_calls"], tool_denied=s["tool_denied"],
                    guard_blocked=guard_blocked(d), context_max_pct=s.get("context_max_pct"),
                    timed_out=s["timed_out"], exit_code=s["exit_code"], ended=now_iso(),
                    visible=vis)

    # ---- job kinds --------------------------------------------------------
    def agent_job(self, task, name, system_prompt):
        key, d = f"{task.id}/{name}", self.jdir(task.id, name)
        (d.parent).mkdir(parents=True, exist_ok=True)
        s, ws = self.call(key, d, "exp-base", system_prompt, task.task_prompt, AGENT_RUN_TIMEOUT_S,
                          task.template, task, task.guard)
        (d / "system_prompt.md").write_text(system_prompt, encoding="utf-8")
        vis, vis_text = task.visible_result(ws)
        (d / "run" / "digest.txt").write_text(digest(d / "run" / "events.jsonl"), encoding="utf-8")
        (d / "visible_result.txt").write_text(vis_text, encoding="utf-8")
        self.record_run(key, d, s, vis)
        return {}

    def direct_job(self, task):
        key, d = f"{task.id}/A_direct", self.jdir(task.id, "A_direct")
        s, ws = self.call(key, d, "exp-direct", prompt_file("direct.md"), task.direct_prompt,
                          SINGLE_CALL_TIMEOUT_S, task.template, task)
        written = task.apply_direct_reply(s["final_text"], ws)
        vis = None
        if written:
            vis, vis_text = task.visible_result(ws)
            (d / "visible_result.txt").write_text(vis_text, encoding="utf-8")
        else:
            self.log(f"{key}: no deliverable could be parsed from the reply")
        self.record_run(key, d, s, vis)
        return {"files_written": written}

    def improver_job(self, task, name, sys_file, prompt, parse):
        """Improver / selector call; one retry if the output format is unusable (both count)."""
        key, d = f"{task.id}/{name}", self.jdir(task.id, name)
        credits, wall = 0.0, 0.0
        for attempt in (1, 2):
            a = d / f"attempt{attempt}"
            s, _ = self.call(key, a, "exp-improver", prompt_file(sys_file), prompt,
                             SINGLE_CALL_TIMEOUT_S, None)
            (a / "input.md").write_text(prompt, encoding="utf-8")
            (a / "output.md").write_text(s["final_text"], encoding="utf-8")
            credits, wall = credits + s["credits"], wall + s["wall_s"]
            self.update(key, status=s["status"], credits=round(credits, 4), wall_s=round(wall, 1),
                        attempts=attempt, context_max_pct=s.get("context_max_pct"))
            out = parse(s["final_text"])
            if out:
                return out
            self.log(f"{key}: attempt {attempt} output unusable")
        raise JobFailed(f"{key}: output unusable after retry", "format")

    # ---- prompts built from earlier jobs (same text as the pilots) -----------
    def visible_text(self, task, name):
        p = self.jdir(task.id, name) / "visible_result.txt"
        return p.read_text(encoding="utf-8") if p.exists() else "(no deliverable)"

    def run_block(self, task, name, title, sys_prompt, n_digest):
        j = self.state["jobs"][f"{task.id}/{name}"]
        out = f"## {title}\n\n"
        if sys_prompt is not None:
            out += f"### System prompt\n\n{sys_prompt}\n\n"
        return (out + f"### Provided-test result\n\n{self.visible_text(task, name)}\n\n"
                f"### Duration and cost\n\n{j.get('wall_s')} s, {j.get('credits')} credits, "
                f"timed out: {j.get('timed_out')}\n\n### Digest\n\n"
                + digest(self.jdir(task.id, name) / "run" / "events.jsonl", n_digest))

    def run_job(self, task, name):
        base = prompt_file("base.md")
        if name == "A_direct":
            return self.direct_job(task)
        if name in B_RUNS:
            return self.agent_job(task, name, base)
        if name == "C_propose":
            p = (prompt_file("propose.md").replace("<<TASK>>", task.task_prompt)
                 .replace("<<CURRENT_PROMPT>>", base)
                 .replace("<<DIGEST>>", digest(self.jdir(task.id, "B_1") / "run" / "events.jsonl", 60000))
                 .replace("<<VISIBLE_RESULT>>", self.visible_text(task, "B_1")))
            return self.improver_job(task, name, "improver.md", p, lambda t: (
                {"prompt_general": tag(t, "prompt_general"), "prompt_specific": tag(t, "prompt_specific")}
                if tag(t, "prompt_general") and tag(t, "prompt_specific") else None))
        cand = self.state["jobs"].get(f"{task.id}/C_propose", {}).get("out") or {}
        if name == "C_probe_general":
            return self.agent_job(task, name, cand["prompt_general"])
        if name == "C_probe_specific":
            return self.agent_job(task, name, cand["prompt_specific"])
        if name == "C_compose":
            blocks = [self.run_block(task, "B_1", "Run 1: reference run (original prompt)", base, 30000),
                      self.run_block(task, "C_probe_general", "Run 2: probe with the general prompt",
                                     cand["prompt_general"], 30000),
                      self.run_block(task, "C_probe_specific", "Run 3: probe with the specific prompt",
                                     cand["prompt_specific"], 30000)]
            p = (prompt_file("compose.md").replace("<<TASK>>", task.task_prompt)
                 .replace("<<RUNS>>", "\n\n".join(blocks)))
            return self.improver_job(task, name, "improver.md", p,
                                     lambda t: {"prompt_final": tag(t, "prompt_final")} if tag(t, "prompt_final") else None)
        if name == "C_final":
            fin = self.state["jobs"][f"{task.id}/C_compose"]["out"]["prompt_final"]
            return self.agent_job(task, name, fin)
        if name == "Bx4_select":
            return self.select_job(task)
        raise ValueError(name)

    def select_job(self, task):
        usable = [b for b in B_RUNS if self.ok(f"{task.id}/{b}")]
        best_vis = None
        if task.has_visible():
            def rate(b):
                v = self.state["jobs"][f"{task.id}/{b}"].get("visible") or {}
                return v.get("passed", -1) if isinstance(v.get("passed"), int) else -1
            best_vis = max(usable, key=lambda b: (rate(b), -B_RUNS.index(b)), default=None)
        fallback = best_vis or (usable[0] if usable else None)
        if not usable:
            raise JobFailed("no usable B attempt", "infra")
        if len(usable) == 1:
            return {"choice": usable[0], "by": "only usable attempt", "best_visible": best_vis}
        blocks = [self.run_block(task, b, f"Attempt {i}", None, 25000) for i, b in enumerate(usable, 1)]
        p = (prompt_file("select.md").replace("<<N>>", str(len(usable)))
             .replace("<<TASK>>", task.task_prompt).replace("<<RUNS>>", "\n\n".join(blocks)))

        def parse(t):
            c = tag(t, "choice")
            m = re.fullmatch(r"\D*(\d+)\D*", c or "")
            n = int(m.group(1)) if m else 0
            return {"choice": usable[n - 1], "by": "selector", "best_visible": best_vis} \
                if 1 <= n <= len(usable) else None
        try:
            return self.improver_job(task, "Bx4_select", "selector.md", p, parse)
        except JobFailed as e:
            if e.kind != "format":
                raise
            self.log(f"{task.id}/Bx4_select: selector unusable -> fallback {fallback}")
            return {"choice": fallback, "by": "fallback (best provided-test rate / first)",
                    "best_visible": best_vis}

    # ---- scheduler ----------------------------------------------------------
    def execute(self, task, name):
        key = f"{task.id}/{name}"
        self.update(key, state="running", group=GROUP[name], started=now_iso())
        self.log(f"start {key}")
        try:
            out = self.run_job(task, name)
            self.update(key, state="ok", out=out, finished=now_iso())
            self.log(f"ok {key}: credits={self.job(key).get('credits')} wall={self.job(key).get('wall_s')} "
                     f"vis={(self.job(key).get('visible') or {}).get('passed')} out={str(out)[:200]}")
        except JobFailed as e:
            self.update(key, state="failed", failure=e.kind, error=str(e), finished=now_iso())
            self.log(f"FAILED {key}: {e}")
        except Exception:
            tb = traceback.format_exc()[-3000:]
            self.update(key, state="failed", failure="error", error=tb, finished=now_iso())
            self.log(f"ERROR {key}\n{tb}")
        if (self.jdir(task.id, name) / "done.json").parent.exists():
            write_json(self.jdir(task.id, name) / "done.json", self.job(key))

    def ready(self):
        """Pending jobs whose dependencies are terminal, in priority order."""
        out = []
        for t in self.order:
            for name in JOB_ORDER:
                if name not in self.only:
                    continue
                key = f"{t}/{name}"
                if self.done(key) or self.state["jobs"].get(key, {}).get("state") == "running":
                    continue
                deps = [f"{t}/{d}" for d in DEPS[name]]
                if not all(self.done(k) for k in deps):
                    continue
                if name != "Bx4_select" and not all(self.ok(k) for k in deps):
                    self.update(key, state="skipped", group=GROUP[name],
                                error="a dependency failed: " + ", ".join(k for k in deps if not self.ok(k)))
                    self.log(f"skip {key}: dependency failed")
                    continue
                out.append((t, name))
        return out

    def schedule(self):
        with cf.ThreadPoolExecutor(CONCURRENCY) as ex:
            running = {}
            while True:
                if not self.state["stopped_for_budget"] and self.state["credits_total"] > self.cap:
                    self.state["stopped_for_budget"] = True
                    self.log(f"credit cap {self.cap} exceeded ({self.state['credits_total']}): "
                             f"no new jobs start")
                for t, name in ([] if self.state["stopped_for_budget"] else self.ready()):
                    if len(running) >= CONCURRENCY:
                        break
                    key = f"{t}/{name}"
                    if key in running.values():
                        continue
                    self.update(key, state="running")  # reserve before the thread starts
                    running[ex.submit(self.execute, self.tasks[t], name)] = key
                with self.hb.lock:
                    self.state["running"] = sorted(running.values())
                if not running:
                    break
                done, _ = cf.wait(running, return_when=cf.FIRST_COMPLETED)
                for f in done:
                    running.pop(f)

    # ---- resume -------------------------------------------------------------
    def recover(self):
        """Jobs a dead orchestrator left 'running': stop leftovers, set the attempt aside."""
        for key, j in list(self.state["jobs"].items()):
            if key == "_meta" or j.get("state") != "running":
                continue
            pid = j.get("pid")
            if pid and pid_alive(pid):
                try:
                    os.killpg(pid, signal.SIGTERM)
                    time.sleep(3)
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            task, name = key.split("/", 1)
            d = self.jdir(task, name)
            spent = 0.0
            if d.exists():
                for ev in d.rglob("events.jsonl"):
                    spent += summarize(ev)["credits"]
                n = 1
                while d.with_name(f"{name}.aborted{n}").exists():
                    n += 1
                shutil.move(str(d), str(d.with_name(f"{name}.aborted{n}")))
            if spent:
                self.add_overhead(spent, f"{key} aborted by an orchestrator stop")
            with self.hb.lock:
                self.state["jobs"][key] = {"aborted_before": j.get("started")}
            self.log(f"resume: {key} was running when the orchestrator stopped; it will run again")

    # ---- grading --------------------------------------------------------------
    def grade(self):
        for t in self.order:
            task = self.tasks[t]
            tr = self.root / t
            if not tr.exists():
                continue
            g = subprocess.run(task.grader_argv(tr), capture_output=True, text=True, timeout=7200)
            self.log(f"grade {t}: exit {g.returncode}\n{g.stdout[-2000:]}\n{g.stderr[-2000:]}")
        r = subprocess.run([PY, str(ROOT / "report_full.py"), "--label", self.label],
                           capture_output=True, text=True)
        self.log(f"report: exit {r.returncode} {r.stderr[-2000:]}")

    def main(self, resume):
        if resume:
            self.recover()
        with self.hb:
            try:
                self.schedule()
                with self.hb.lock:
                    self.state["phase"] = "grading"
                self.grade()
            except Exception:
                self.state["error"] = traceback.format_exc()[-3000:]
                self.log("ERROR\n" + self.state["error"])
            with self.hb.lock:
                self.state.update(finished=True, finished_at=now_iso(), phase="done", running=[])


def guard_blocked(run_dir):
    log = run_dir / "guard_log.jsonl"
    if not log.exists():
        return 0
    n = 0
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            n += bool(json.loads(line).get("blocked"))
        except json.JSONDecodeError:
            continue
    return n


def write_manifest(root, tasks):
    kv = subprocess.run([KIRO, "--version"], capture_output=True, text=True).stdout.strip()
    pv = subprocess.run([PY, "--version"], capture_output=True, text=True).stdout.strip()
    files = [*(ROOT / "agents").glob("*.json"), *(ROOT / "prompts").glob("*.md"),
             *(ROOT / f for f in ("guard.py", "kiro_runner.py", "run_full.py", "tasklib.py",
                                   "common.py", "report_full.py"))]
    for t in [*tasks, "swe_common"]:
        td = common.TASKS_DIR / t
        if not td.is_dir():
            continue
        files += [p for p in td.rglob("*") if p.is_file() and ".venv" not in p.parts
                  and "__pycache__" not in p.parts and p.stat().st_size < 5_000_000]
    write_json(root / "manifest.json", {
        "created": now_iso(), "kiro_cli": kv, "python": pv, "os": platform.platform(),
        "model": common.MODEL, "effort": common.EFFORT, "engine": ENGINE, "concurrency": CONCURRENCY,
        "agent_run_timeout_s": AGENT_RUN_TIMEOUT_S, "single_call_timeout_s": SINGLE_CALL_TIMEOUT_S,
        "tasks": tasks, "n_bx": N_BX, "infra_retries": INFRA_RETRIES,
        "file_sha256": {str(f.relative_to(ROOT)): sha256_file(f) for f in sorted(set(files)) if f.exists()},
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--model", default="claude-haiku-4.5")
    ap.add_argument("--effort", default="", help='"" = do not pass --effort')
    ap.add_argument("--tasks", default=",".join(DEFAULT_TASKS))
    ap.add_argument("--credit-cap", type=float, default=DEFAULT_CAP)
    ap.add_argument("--jobs", default="", help="comma list: run only these jobs (smoke tests)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--detach", action="store_true", help="start in a new session and return")
    args = ap.parse_args()
    args.tasks = [t for t in args.tasks.split(",") if t]
    args.jobs = [j for j in args.jobs.split(",") if j] or None
    if args.jobs and set(args.jobs) - set(JOB_ORDER):
        raise SystemExit(f"unknown jobs: {set(args.jobs) - set(JOB_ORDER)}")
    root = RUNS_DIR / args.label
    pidf = root / "orchestrator.pid"

    if args.detach:
        root.mkdir(parents=True, exist_ok=True)
        argv = [PY, str(Path(__file__).resolve())] + [a for a in sys.argv[1:] if a != "--detach"]
        out = open(root / "orchestrator.out", "a", encoding="utf-8")
        p = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=out,
                             start_new_session=True)
        print(f"started pid {p.pid} for {args.label}")
        return

    if pidf.exists() and pid_alive(int(pidf.read_text() or 0)):
        raise SystemExit(f"an orchestrator for {args.label} is already running (pid {pidf.read_text()})")
    if args.resume:
        if not (root / "status.json").exists():
            raise SystemExit(f"nothing to resume in runs/{args.label}")
        st = read_json(root / "status.json")
        args.model, args.effort, args.tasks = st["model"], st["effort"], st["tasks"]
        if st.get("finished"):
            raise SystemExit(f"runs/{args.label} already finished")
    elif (root / "status.json").exists():
        raise SystemExit(f"runs/{args.label} already holds a run; use --resume or a new label")
    common.MODEL, common.EFFORT = args.model, args.effort
    root.mkdir(parents=True, exist_ok=True)
    pidf.write_text(str(os.getpid()))
    f = Full(args)
    if not args.resume:
        write_manifest(root, args.tasks)
    f.log(f"{'resume' if args.resume else 'start'} pid {os.getpid()} model={args.model} tasks={args.tasks}")
    f.main(args.resume)


if __name__ == "__main__":
    main()
