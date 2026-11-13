"""Smoke tests: every lab and every reference solution runs offline, in mock mode.

If one of these fails after you change something, you broke a lab.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LABS = sorted(ROOT.glob("modules/*/labs/*.py"))
SOLUTIONS = [
    ("projects/01-support-triage/solution/triage.py", []),
    ("projects/02-ask-my-docs/solution/ask.py", []),
    ("projects/02-ask-my-docs/solution/ask.py", ["--eval"]),
    ("projects/03-coding-agent/solution/agent.py", []),
    ("projects/04-research-team/solution/research.py", []),
    ("projects/05-eval-harness/solution/run_evals.py", []),
]
# Lab 7.1 demonstrates a failing regression gate, so it exits with code 1 on purpose.
EXPECTED_EXIT = {"01_first_eval.py": 1}


def run(path: Path, args: list[str], tmp_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "AIKIT_MOCK": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, str(path), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("lab", LABS, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_lab_runs(lab: Path, tmp_path: Path):
    result = run(lab, [], tmp_path)
    assert result.returncode == EXPECTED_EXIT.get(lab.name, 0), result.stderr[-2000:]
    assert result.stdout.strip(), "lab printed nothing"


@pytest.mark.parametrize("path,args", SOLUTIONS, ids=lambda v: v if isinstance(v, str) else " ".join(v))
def test_solution_runs(path: str, args: list[str], tmp_path: Path):
    result = run(ROOT / path, args, tmp_path)
    assert result.returncode == 0, result.stderr[-2000:]


def test_capstone_api():
    env = {**os.environ, "AIKIT_MOCK": "1"}
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "projects/06-capstone/solution"], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout[-2000:]
