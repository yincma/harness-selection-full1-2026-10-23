"""preToolUse guard for the experiment agents (fail closed).

kiro-cli runs this before every tool call with the call as JSON on stdin.
Exit 0 allows the call; exit 2 blocks it and the stderr text goes back to the agent.
Rules (same for every group):
  fs_read      only paths inside the workspace
  fs_write     only cmark.py, NOTES.md, cmark_lib/**, scratch/**
  execute_bash only ./run_tests.sh [options], ./run_md.sh scratch/<file>, ls [dir]
  anything else is blocked
Every decision is appended to ../guard_log.jsonl (outside the workspace).
"""
import json
import os
import re
import sys

WS = os.path.realpath(sys.argv[1])
LOG = os.path.join(os.path.dirname(WS), "guard_log.jsonl")
# Per-task rules live next to the workspace (outside it, so the agent cannot edit them).
# Without that file the pilots' CommonMark rules apply.
RULES = os.path.join(os.path.dirname(WS), "guard_rules.json")
WRITE_FILES = {"cmark.py", "NOTES.md"}
WRITE_DIRS = ("cmark_lib", "scratch")
SHELL_PATTERNS = (
    r"\./run_tests\.sh( [A-Za-z0-9_.,:=-]+)*",
    r"\./run_md\.sh scratch/[A-Za-z0-9_./-]+",
    r"ls( -[a-zA-Z]+)?( [A-Za-z0-9_./-]+)?",
)
SHELL_HELP = "only ./run_tests.sh, ./run_md.sh scratch/<file> and ls are allowed"
if os.path.exists(RULES):
    with open(RULES, encoding="utf-8") as _f:
        _r = json.load(_f)
    WRITE_FILES = set(_r["write_files"])
    WRITE_DIRS = tuple(_r["write_dirs"])
    SHELL_PATTERNS = tuple(_r["shell"])
    SHELL_HELP = _r.get("shell_help", "this command is not on the task's allow-list")
SHELL_OK = [re.compile(p) for p in SHELL_PATTERNS]
SHELL_META = re.compile(r"[;&|`$<>()\\\n\r*?{}\[\]~!#'\"]")


def inside(path, base):
    return path == base or path.startswith(base + os.sep)


def resolve(p):
    return os.path.realpath(os.path.join(WS, os.path.expanduser(p)))


def check(tool, inp):
    if tool in ("fs_read", "read"):
        paths = []
        for op in inp.get("operations") or [inp]:
            paths += [op[k] for k in ("path",) if op.get(k)]
            paths += op.get("image_paths") or []
        if not paths:
            return "read: no path given"
        for p in paths:
            if not inside(resolve(p), WS):
                return f"read outside the workspace is not allowed: {p}"
        return None
    if tool in ("fs_write", "write"):
        p = inp.get("path")
        if not p:
            return "write: no path given"
        rel = os.path.relpath(resolve(p), WS)
        if rel in WRITE_FILES or any(inside(resolve(p), os.path.join(WS, d)) for d in WRITE_DIRS):
            return None
        return (f"write allowed only to {', '.join(sorted(WRITE_FILES))} and under "
                f"{', '.join(d + '/' for d in WRITE_DIRS)} (got {p})")
    if tool in ("execute_bash", "shell"):
        cmd = (inp.get("command") or "").strip()
        if SHELL_META.search(cmd) or ".." in cmd:
            return "command rejected: shell operators and special characters are not allowed"
        if any(r.fullmatch(cmd) for r in SHELL_OK):
            return None
        return "command rejected: " + SHELL_HELP
    return f"tool not available: {tool}"


def main():
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw)
        tool = ev.get("tool_name") or ev.get("toolName") or ""
        inp = ev.get("tool_input") or ev.get("toolInput") or ev.get("input") or {}
        if isinstance(inp, str):
            inp = json.loads(inp)
        reason = check(tool, inp)
    except Exception as e:  # unknown event shape: block rather than guess
        tool, reason = "?", f"guard could not parse the tool call: {e}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"tool": tool, "blocked": bool(reason), "reason": reason,
                            "event": raw[:2000]}, ensure_ascii=False) + "\n")
    if reason:
        print(reason, file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
