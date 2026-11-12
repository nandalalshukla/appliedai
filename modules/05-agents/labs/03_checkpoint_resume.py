"""Lab 5.3 - Checkpoint and resume: surviving a crash at step 7 of 10.

Long agent runs die: the process is redeployed, the laptop sleeps, an API call
times out. Without checkpoints you restart from zero - paying again, and
REPEATING side effects (a second email, a second refund).

Because an agent's whole state is its message list, a checkpoint is just that
list written to disk after every step. Agent.run does this when you pass
`checkpoint=`; resume() loads it and continues.

Run:  python modules/05-agents/labs/03_checkpoint_resume.py
"""

from pathlib import Path

from aikit import fake_tool, get_client
from aikit.agent import Agent, print_events
from aikit.tools import ToolRegistry

CHECKPOINT = Path(".checkpoints/report_run.json")
CHECKPOINT.unlink(missing_ok=True)
calls_made: list[str] = []


def build_registry(crash_on: str | None) -> ToolRegistry:
    registry = ToolRegistry()

    @registry.tool()
    def fetch_sales(region: str) -> dict:
        """Fetch last month's sales total in USD for a region: 'north', 'south' or 'east'."""
        if region == crash_on:
            raise SystemExit(f"\n*** process killed while fetching {region!r} ***\n")  # simulated crash
        calls_made.append(region)
        return {"region": region, "usd": {"north": 120, "south": 90, "east": 75}[region]}

    return registry


SYSTEM = "Fetch sales for north, south and east one at a time, then report the total."
SCRIPT = [
    fake_tool("fetch_sales", {"region": "north"}),
    fake_tool("fetch_sales", {"region": "south"}),
    fake_tool("fetch_sales", {"region": "east"}),
    "Total sales: $285 (north 120, south 90, east 75).",
]

# ---- Run 1: crashes during the third step -----------------------------------
print("RUN 1")
agent = Agent(get_client(script=list(SCRIPT)), build_registry(crash_on="east"), SYSTEM,
              on_event=print_events, checkpoint=CHECKPOINT)
try:
    agent.run("Produce the sales report.")
except SystemExit as crash:
    print(crash)

print("checkpoint on disk:", CHECKPOINT.exists(), "| regions fetched so far:", calls_made)

# ---- Run 2: a NEW process picks up where the old one stopped ----------------
print("\nRUN 2 (resume)")
agent = Agent(get_client(script=SCRIPT[2:]), build_registry(crash_on=None), SYSTEM,
              on_event=print_events, checkpoint=CHECKPOINT)
result = agent.resume()
print("\nanswer:", result.text)
print("every region fetched exactly once:", calls_made)

# What makes resume CORRECT, not just possible:
# 1. Save after every completed step, atomically (write temp file, then rename).
# 2. The history must end in a valid state: every tool_use has its tool_result.
#    We save only after results are appended, so a crash mid-tool loses that
#    one step and the model simply asks for it again.
# 3. That re-ask means a tool may run twice. Reads do not care. WRITES must be
#    idempotent (Module 3) or a resume double-charges someone.
# 4. In production the checkpoint lives in a database keyed by run id, not a
#    local file, so any worker can resume any run.
#
# Try it:
# 1. Move the crash to "south". How many model calls does the resume save?
# 2. Make fetch_sales a write (e.g. it appends to a file). Show the duplicate
#    after a crash-and-resume, then fix it with an idempotency key.
