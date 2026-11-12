"""Lab 5.5 - A coding agent in 100 lines (how tools like Claude Code work).

A coding agent is the loop from Lab 5.1 with four tools - list, read, edit,
run - and a good system prompt. This one fixes a failing test in a sandbox
directory. Project 3 grows it into a real tool.

Run:  python modules/05-agents/labs/05_mini_coding_agent.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from aikit import fake_tool, get_client
from aikit.agent import Agent, print_events
from aikit.tools import ToolRegistry

# --- a tiny broken project to work on ----------------------------------------
ROOT = Path(tempfile.mkdtemp(prefix="mini_agent_"))
(ROOT / "cart.py").write_text(
    "def total(prices, discount=0.0):\n"
    "    subtotal = sum(prices)\n"
    "    return subtotal + subtotal * discount   # BUG: should subtract\n"
)
(ROOT / "test_cart.py").write_text(
    "from cart import total\n\n"
    "def test_discount():\n"
    "    assert total([100, 100], discount=0.1) == 180\n"
)

registry = ToolRegistry(max_result_chars=4000)


def safe_path(path: str) -> Path:
    """Confine every file operation to ROOT. The model must not escape the sandbox."""
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT.resolve()):
        raise PermissionError(f"{path!r} is outside the project directory")
    return p


@registry.tool()
def list_files() -> list:
    """List all files in the project, as paths relative to the project root."""
    return sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


@registry.tool()
def read_file(path: str) -> str:
    """Read a text file. Always read a file before editing it."""
    return safe_path(path).read_text()


@registry.tool(read_only=False)
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact occurrence of old_text with new_text in a file.

    old_text must match the file exactly (including indentation) and appear exactly once;
    include enough surrounding text to make it unique.
    """
    p = safe_path(path)
    content = p.read_text()
    count = content.count(old_text)
    if count != 1:
        raise ValueError(f"old_text appears {count} times in {path}; it must appear exactly once")
    p.write_text(content.replace(old_text, new_text))
    return f"edited {path}"


@registry.tool(read_only=False, timeout_s=60)
def run_tests() -> str:
    """Run the project's test suite with pytest. Returns the exit code and the output."""
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                          cwd=ROOT, capture_output=True, text=True, timeout=50)
    return f"exit code {proc.returncode}\n{(proc.stdout + proc.stderr)[-2500:]}"


SYSTEM = """You are a coding agent working in a small Python project.

How to work:
- Explore before you change anything: list files, read the relevant ones, run the tests.
- Make the smallest change that fixes the problem. Fix the code, not the test, unless the test is wrong.
- After every edit, run the tests. You are done only when they pass.
- Finish with two sentences: what was wrong and what you changed."""

client = get_client(script=[
    fake_tool("list_files", {}),
    fake_tool("run_tests", {}),
    fake_tool("read_file", {"path": "cart.py"}),
    fake_tool("edit_file", {"path": "cart.py",
                            "old_text": "return subtotal + subtotal * discount   # BUG: should subtract",
                            "new_text": "return subtotal - subtotal * discount"}),
    fake_tool("run_tests", {}),
    "The discount was added to the subtotal instead of subtracted. I changed the return line in "
    "cart.py to subtract it, and the test now passes.",
])

if __name__ == "__main__":
    print("project:", ROOT, "\n")
    result = Agent(client, registry, SYSTEM, max_steps=15, on_event=print_events).run(
        "The test suite is failing. Find the bug and fix it."
    )
    print(f"\nstopped: {result.stopped} in {result.steps} steps\n{result.text}")
    print("\ncart.py now:\n" + (ROOT / "cart.py").read_text())

# Why these tool designs:
# - edit_file takes an exact string to replace (not line numbers, not a whole
#   file rewrite). Models are bad at counting lines and rewriting wastes tokens
#   and silently drops code. A failed match returns an error the model can fix.
# - run_tests gives the agent a way to CHECK ITS OWN WORK. This feedback loop
#   is the difference between an agent and a text generator.
# - safe_path is a hard boundary in code. "Please stay in the project folder"
#   in a prompt is not a boundary.
#
# Try it (live mode):
# 1. Introduce a different bug and let the agent find it.
# 2. Add a `search(pattern)` tool (grep). Why do coding agents lean on search
#    rather than embedding the whole repository?
# 3. Add `run_command(cmd)` behind needs_approval=True. Which commands would
#    you auto-approve?
