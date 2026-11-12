"""Lab 3.2 - Tool infrastructure: a registry that survives bad input.

Hand-writing schemas and if/else dispatch does not scale past two tools.
aikit/tools.py is a ~130-line registry. Read it alongside this lab. It:

  - builds the JSON schema from a typed Python function
  - validates the model's arguments before running anything
  - enforces a timeout
  - converts EVERY failure into an error message the model can act on
  - truncates huge results so they cannot flood the context window
  - logs each call

Run:  python modules/03-tool-use/labs/02_tool_registry.py
"""

import time
from typing import Literal

from aikit import pretty
from aikit.tools import ToolRegistry

registry = ToolRegistry(max_result_chars=200)


@registry.tool()
def search_products(query: str, max_results: int = 5, sort: Literal["relevance", "price"] = "relevance") -> list:
    """Search the product catalogue by keyword.

    Use for any question about what we sell or what something costs.
    Returns a list of {name, price_usd}. Returns an empty list if nothing matches;
    in that case try a broader query before telling the user we don't sell it.
    """
    catalogue = [{"name": "USB-C cable 1m", "price_usd": 9}, {"name": "USB-C charger 65W", "price_usd": 39}]
    return [p for p in catalogue if query.lower() in p["name"].lower()][:max_results]


@registry.tool(timeout_s=0.2)
def slow_report(month: str) -> str:
    """Generate the sales report for a month given as YYYY-MM. Can be slow."""
    time.sleep(1)
    return "report"


@registry.tool()
def dump_logs(service: str) -> str:
    """Return recent log lines for a service name such as 'checkout'."""
    return "\n".join(f"{service} line {i}: everything is fine" for i in range(500))


print("SCHEMA SENT TO THE MODEL:\n", pretty(registry.schemas()[1]), "\n")

cases = [
    ("happy path", "search_products", {"query": "usb-c"}),
    ("wrong type (model sent a string for an int)", "search_products", {"query": "usb", "max_results": "many"}),
    ("missing required argument", "search_products", {}),
    ("value outside the enum", "search_products", {"query": "usb", "sort": "cheapest"}),
    ("tool that does not exist", "delete_database", {}),
    ("timeout", "slow_report", {"month": "2026-10"}),
    ("huge result", "dump_logs", {"service": "checkout"}),
]

for label, name, args in cases:
    result = registry.execute(name, args)
    flag = "ERROR" if result.is_error else "ok   "
    print(f"[{flag}] {label}\n        -> {result.content[:150]!r}\n")

print("CALL LOG:", pretty(registry.log[-2:]))

# What to notice: execute() never raised. A crash in a tool must not crash the
# agent. The model reads the error text and usually corrects itself on the
# next turn - but only if the message says what was wrong and what to do.
#
# Try it:
# 1. Write a tool `get_weather(city: str, unit: Literal["c","f"]="c")`. Print its schema.
# 2. Make an error message unhelpful ("Error."). In live mode, see how many
#    extra turns the model wastes compared to a specific message.
# 3. Add a per-tool call counter and refuse after 5 calls in one conversation.
