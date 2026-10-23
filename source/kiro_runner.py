"""Launch one kiro-cli run and record what it did.

Each run gets its own directory:
  events.jsonl  raw stream-json events (ACP)   stderr.txt   kiro-cli stderr
  run.json      summary: status, credits, duration, tool calls, final text
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

import common  # common.MODEL / common.EFFORT are read at call time (run_pilot.py may override them)
from common import AGENTS_DIR, ENGINE, KIRO, PY, ROOT, clean_env, now_iso, write_json


def install_agent(ws: Path, agent: str, prompt_text: str, rules: dict | None = None) -> None:
    """Put one agent config + its system prompt into <ws>/.kiro, with no inherited resources.

    rules: the task's guard rules. They are written next to the workspace (guard.py reads them
    there) and mirrored into the config's toolsSettings. None = the pilots' CommonMark rules.
    """
    ws_abs = str(ws.resolve())
    cfg = json.loads((AGENTS_DIR / f"{agent}.json").read_text(encoding="utf-8").replace("__WS__", ws_abs))
    cfg["model"] = common.MODEL  # one model per pilot, for every agent
    if rules is not None:
        write_json(ws.parent / "guard_rules.json", rules)
        ts = cfg.get("toolsSettings") or {}
        if "fs_write" in ts:
            ts["fs_write"] = {
                "allowedPaths": [f"{ws_abs}/{f}" for f in rules["write_files"]]
                                + [f"{ws_abs}/{d}/**" for d in rules["write_dirs"]],
                "deniedPaths": [f"{ws_abs}/.kiro/**"]}
        if "execute_bash" in ts:
            ts["execute_bash"] = {"allowedCommands": [f"^{p}$" for p in rules["shell"]],
                                  "denyByDefault": True}
    guard_cmd = f"'{PY}' -E -s -S '{ROOT / 'guard.py'}' '{ws_abs}'"
    for hooks in (cfg.get("hooks") or {}).values():
        for h in hooks:
            if h.get("command") == "__GUARD_CMD__":
                h["command"] = guard_cmd
    adir = ws / ".kiro" / "agents"
    adir.mkdir(parents=True, exist_ok=True)
    (adir / f"{agent}.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    (adir / f"{agent}.prompt.md").write_text(prompt_text, encoding="utf-8")
    sdir = ws / ".kiro" / "settings"
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "cli.json").write_text(
        json.dumps({"chat.disableInheritingDefaultResources": True}, indent=2), encoding="utf-8")


def new_workspace(template: Path | None, ws: Path) -> Path:
    if ws.exists():
        shutil.rmtree(ws)
    if template:
        shutil.copytree(template, ws)
    else:
        ws.mkdir(parents=True)
    return ws


def run_kiro(ws: Path, agent: str, prompt: str, out_dir: Path, timeout_s: int,
             on_start=None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [KIRO, "chat", "--no-interactive", "--output-format", "stream-json",
           "--agent-engine", ENGINE, "--agent", agent, "--model", common.MODEL]
    if common.EFFORT:
        cmd += ["--effort", common.EFFORT]
    cmd.append(prompt)
    (out_dir / "cmd.txt").write_text(" ".join(cmd[:-1]) + f" <prompt: {len(prompt)} chars>\n",
                                     encoding="utf-8")
    t0 = time.time()
    started = now_iso()
    with open(out_dir / "events.jsonl", "wb") as ev, open(out_dir / "stderr.txt", "wb") as er:
        proc = subprocess.Popen(cmd, cwd=ws, env=clean_env(), stdout=ev, stderr=er,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        if on_start:
            on_start(proc.pid)  # lets a resumed orchestrator stop a run its predecessor left behind
        timed_out = False
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            _stop(proc)
    summary = summarize(out_dir / "events.jsonl")
    summary.update({"agent": agent, "started": started, "ended": now_iso(),
                    "wall_s": round(time.time() - t0, 1), "exit_code": proc.returncode,
                    "timed_out": timed_out, "prompt_chars": len(prompt)})
    write_json(out_dir / "run.json", summary)
    return summary


def _stop(proc):
    """SIGINT first so kiro-cli can end the turn (and report usage), then escalate.

    Signals go to the whole process group (start_new_session=True makes proc.pid the group id):
    signalling only the wrapper left kiro-cli-chat and a hung cmark.py running as orphans.
    """
    for sig, wait in ((signal.SIGINT, 30), (signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            continue
        # The leader is gone; give the rest of the group the same signal's grace period.
        time.sleep(2)
        try:
            os.killpg(proc.pid, 0)
        except ProcessLookupError:
            return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def iter_events(path: Path):
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def summarize(path: Path) -> dict:
    metering, ctx_max, chunks = [], 0.0, []
    calls, failed, denied = set(), set(), set()
    final = {}
    for e in iter_events(path):
        t, d = e.get("type"), e.get("data", {})
        if t == "metadata":
            for m in d.get("meteringUsage") or []:
                metering.append(m.get("value", 0.0))
            ctx_max = max(ctx_max, d.get("contextUsagePercentage") or 0.0)
        elif t == "sessionUpdate":
            u = d.get("update", {})
            kind = u.get("sessionUpdate")
            if kind in ("tool_call", "tool_call_update"):
                cid = u.get("toolCallId")
                calls.add(cid)
                if u.get("status") == "failed":
                    failed.add(cid)
                    reason = ((u.get("_meta") or {}).get("kiro") or {}).get("toolCallFailureReason")
                    if reason == "permission_denied":
                        denied.add(cid)
            elif kind == "agent_message_chunk":
                chunks.append((u.get("content") or {}).get("text", ""))
        elif t == "runFinished":
            final = d
    text = final.get("finalText") or ""
    if not text or final.get("finalTextTruncated"):
        text = "".join(chunks)
    return {"status": final.get("status", "no_runFinished"), "stop_reason": final.get("stopReason"),
            "credits": round(sum(metering), 4), "metering_values": metering,
            "context_max_pct": ctx_max, "tool_calls": len(calls), "tool_failed": len(failed),
            "tool_denied": len(denied), "final_text": text}


def _short(x, n):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[: n // 2] + f" ...[{len(s) - n} chars cut]... " + s[-n // 2:]


def _content_text(content) -> str:
    parts = []
    for c in content or []:
        inner = c.get("content") if isinstance(c, dict) else None
        if isinstance(inner, dict) and "text" in inner:
            parts.append(inner["text"])
        elif isinstance(c, dict) and "text" in c:
            parts.append(c["text"])
    return "\n".join(parts)


def digest(path: Path, max_chars: int = 60000) -> str:
    """Readable trace of a run for the improver: messages, tool calls, tool results."""
    steps, msg, seen = [], [], set()
    for e in iter_events(path):
        if e.get("type") != "sessionUpdate":
            continue
        u = e["data"].get("update", {})
        kind = u.get("sessionUpdate")
        if kind == "agent_message_chunk":
            msg.append((u.get("content") or {}).get("text", ""))
            continue
        if msg:
            steps.append("AGENT: " + _short("".join(msg).strip(), 1500))
            msg = []
        if kind not in ("tool_call", "tool_call_update"):
            continue
        cid = u.get("toolCallId")
        if cid not in seen and u.get("rawInput") is not None:
            seen.add(cid)
            steps.append(f"TOOL CALL [{u.get('title', '')}]: " + _short(u.get("rawInput", ""), 800))
        if u.get("status") in ("completed", "failed"):
            out = _content_text(u.get("content")) or u.get("rawOutput", "")
            steps.append(f"TOOL RESULT ({u.get('status')}): " + _short(out, 1200))
    if msg:
        steps.append("AGENT: " + _short("".join(msg).strip(), 3000))
    text = "\n".join(steps)
    if len(text) > max_chars:  # keep the start and the end of a long run
        text = text[: max_chars // 3] + "\n...[middle of run omitted]...\n" + text[-2 * max_chars // 3:]
    return text


class Heartbeat:
    """Touches status.json every 30 s so an outside watcher can tell a stall from progress."""

    def __init__(self, status_path: Path, state: dict):
        self.path, self.state, self._stop = status_path, state, threading.Event()
        self.lock = threading.Lock()  # runs update `state` from several threads
        self._t = threading.Thread(target=self._loop, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join()
        self.write()

    def write(self):
        with self.lock:
            self.state["heartbeat"] = time.time()
            write_json(self.path, self.state)

    def _loop(self):
        while not self._stop.wait(30):
            self.write()
