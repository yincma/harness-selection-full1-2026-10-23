"""Shared settings and helpers for the Harness pilot.

Groups
  A  direct: one kiro-cli call, no tools, deliverable extracted from the reply
  B  fixed minimal harness: one kiro-cli agent run (read / write / restricted shell)
  C  H2-lite: B's run as reference -> improver proposes 2 prompts -> 2 probe runs
     -> improver composes 1 prompt -> final run (only the system prompt changes)

Every model call in one pilot uses the same model through kiro-cli (MODEL below,
overridable per pilot with run_pilot.py --model; pilot1 = claude-sonnet-5.5,
pilot2 = claude-haiku-4.5). The model is read at call time and also written into
every installed agent config, so all groups and the improver share it.
This code only orchestrates, records and grades; it never makes an experimental decision.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AGENTS_DIR = ROOT / "agents"
PROMPTS_DIR = ROOT / "prompts"
TASKS_DIR = ROOT / "tasks"
RUNS_DIR = ROOT / "runs"

KIRO = "kiro-cli"
PY = "/opt/homebrew/bin/python3"  # 3.13.7 on this Mac; pinned so every group uses the same interpreter
MODEL = "claude-sonnet-5.5"  # default; run_pilot.py --model sets common.MODEL for a whole pilot
EFFORT = "medium"  # "" = do not pass --effort
ENGINE = "v2"  # pinned: a future default-engine change must not alter the experiment

AGENT_RUN_TIMEOUT_S = 45 * 60   # B, C probes, C final (same cap for every agent run)
SINGLE_CALL_TIMEOUT_S = 20 * 60  # A and improver calls
CONCURRENCY = 2
PILOT_CREDIT_CAP = 150.0  # stop launching new phases once recorded credits exceed this

# Variables that tie a child process to this KiroCrew session.
_DROP_ENV = {"KIRO_SESSION_ID", "KIRO_CHAT_LOG_FILE", "KIRO_CLI_ACP_CLIENT_NAME",
             "KIRO_CLI_CLIENT_APPLICATION"}


def clean_env() -> dict[str, str]:
    """Environment for experiment processes, without KiroCrew session variables."""
    return {k: v for k, v in os.environ.items()
            if not k.startswith("KIROCREW_") and k not in _DROP_ENV}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def write_json(p: Path, obj) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)  # atomic, so a watcher never reads half a file


def read_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
