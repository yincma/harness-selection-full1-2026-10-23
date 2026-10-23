"""Task definitions for the full run: everything that differs between tasks lives in
tasks/<id>/task.json plus files next to it, so the orchestrator stays task-agnostic.

task.json fields
  id, title, tier          tier: "simple" | "repo" | "spec" (for the report only)
  template                 directory (relative to the task dir) copied to every workspace
  task_prompt              file with the user prompt for every agent run (B, Bx4, C)
  direct_prompt            file with the complete user prompt for A (task + inlined context)
  direct_output            {"mode": "single_file", "path": "x.py"}
                           | {"mode": "files", "prefixes": ["repo/"]}   (FILE: <path> + code block)
  guard                    {"write_files": [...], "write_dirs": [...], "shell": [regex...],
                            "shell_help": "..."}   -> <run_dir>/guard_rules.json for guard.py
  setup                    optional argv run after the template copy; placeholders
                           {py} {task_dir} {ws} {run_dir}  (e.g. a per-run virtualenv)
  visible                  optional {"json_cmd": [...], "text_cmd": [...]} run inside the
                           workspace; the last stdout line of json_cmd is {"passed", "total", ...}
  grader                   argv; placeholders {py} {task_dir} {task_runs}; must write
                           {task_runs}/grades.json  (see report_full.py for the format)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from common import PY, TASKS_DIR, read_json

VISIBLE_TIMEOUT_S = 900


class Task:
    def __init__(self, task_id: str):
        self.dir = TASKS_DIR / task_id
        self.cfg = read_json(self.dir / "task.json")
        self.id = self.cfg["id"]
        assert self.id == task_id, (self.id, task_id)
        self.template = self.dir / self.cfg["template"]
        self.guard = self.cfg["guard"]

    def text(self, key: str) -> str:
        return (self.dir / self.cfg[key]).read_text(encoding="utf-8")

    @property
    def task_prompt(self) -> str:
        return self.text("task_prompt")

    @property
    def direct_prompt(self) -> str:
        return self.text("direct_prompt")

    def _fill(self, argv, **kw):
        kw = {"py": PY, "task_dir": str(self.dir), **{k: str(v) for k, v in kw.items()}}
        return [a.format(**kw) for a in argv]

    def setup(self, ws: Path, run_dir: Path, log) -> None:
        if not self.cfg.get("setup"):
            return
        p = subprocess.run(self._fill(self.cfg["setup"], ws=ws.resolve(), run_dir=run_dir.resolve()),
                           capture_output=True, text=True, timeout=1800)
        (run_dir / "setup.log").write_text(p.stdout[-20000:] + "\n" + p.stderr[-20000:], encoding="utf-8")
        if p.returncode != 0:
            raise RuntimeError(f"{self.id} setup failed ({p.returncode}): {p.stderr[-800:]}")
        log(f"{self.id}: workspace setup done for {run_dir.name}")

    def has_visible(self) -> bool:
        return bool(self.cfg.get("visible"))

    def visible_result(self, ws: Path):
        """(summary dict | None, text). Run without the agents' whole-run limit."""
        if not self.has_visible():
            return None, ("(This task has no provided test set. The agent could run the "
                          "repository's own tests and its own scripts.)")
        env = {**os.environ, "H2_SUITE_LIMIT_S": "0"}
        v = self.cfg["visible"]
        try:
            j = subprocess.run(v["json_cmd"], cwd=ws, capture_output=True, text=True,
                               timeout=VISIBLE_TIMEOUT_S, env=env)
            summary = json.loads(j.stdout.strip().splitlines()[-1])
            t = subprocess.run(v["text_cmd"], cwd=ws, capture_output=True, text=True,
                               timeout=VISIBLE_TIMEOUT_S, env=env)
            return summary, t.stdout[:6000]
        except Exception as e:
            return {"error": str(e)}, f"provided tests could not run: {e}"

    def grader_argv(self, task_runs: Path):
        return self._fill(self.cfg["grader"], task_runs=task_runs.resolve())

    # ---- A: turn the single reply into files --------------------------------
    def allowed_write(self, rel: str) -> bool:
        rel = os.path.normpath(rel)
        if rel.startswith("..") or os.path.isabs(rel):
            return False
        g = self.guard
        return rel in g["write_files"] or any(rel.startswith(d.rstrip("/") + "/") for d in g["write_dirs"])

    def apply_direct_reply(self, text: str, ws: Path) -> list[str]:
        """Write A's deliverable into the workspace; returns the paths written."""
        out = self.cfg["direct_output"]
        if out["mode"] == "single_file":
            code = extract_code(text)
            if not code:
                return []
            (ws / out["path"]).write_text(code, encoding="utf-8")
            return [out["path"]]
        written = []
        for rel, body in extract_files(text):
            if not self.allowed_write(rel) or not any(rel.startswith(p) for p in out["prefixes"]):
                continue
            p = ws / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
            written.append(rel)
        return written


def extract_code(text: str):
    # Fences must sit on their own line: code such as startswith('```') must not close the block.
    blocks = re.findall(r"^```(?:python|py)?[ \t]*\n(.*?)^```[ \t]*$", text, re.S | re.M)
    return max(blocks, key=len) if blocks else None


_FILE_BLOCK = re.compile(r"^(?:#+ *)?FILE: *`?([^\s`]+)`? *\n+```[A-Za-z0-9_+-]*[ \t]*\n(.*?)^```[ \t]*$",
                         re.S | re.M)


def extract_files(text: str):
    """[(path, content)] from blocks written as 'FILE: <path>' followed by a fenced block."""
    return [(m.group(1), m.group(2)) for m in _FILE_BLOCK.finditer(text)]
