"""Lab 3.3 - The tool loop: several calls, parallel calls, and errors.

Real questions need more than one tool call. The pattern is a loop:
keep calling the model until it stops asking for tools.

Run:  python modules/03-tool-use/labs/03_tool_loop.py
"""

from aikit import MODEL, CostMeter, fake_tools, get_client, text_of
from aikit.tools import ToolRegistry

registry = ToolRegistry()
STOCK = {"usb-c cable": 12, "charger": 0}
PRICES = {"usb-c cable": 9.0, "charger": 39.0}


@registry.tool()
def check_stock(product: str) -> dict:
    """Return how many units of a product are in stock. Product names are lowercase."""
    if product not in STOCK:
        raise KeyError(f"unknown product {product!r}. Known: {sorted(STOCK)}")
    return {"product": product, "units": STOCK[product]}


@registry.tool()
def get_price(product: str) -> dict:
    """Return the unit price in USD of a product. Product names are lowercase."""
    return {"product": product, "price_usd": PRICES[product]}


SYSTEM = "You are a shop assistant. Use the tools for stock and price; never guess them."

client = get_client(
    script=[
        # Turn 1: two independent lookups requested in ONE response (parallel tool use),
        # and one of them has a typo so we see error handling.
        fake_tools([("check_stock", {"product": "usb-c cable"}), ("check_stock", {"product": "chargr"})]),
        # Turn 2: the model read the error message and corrects itself.
        fake_tools([("check_stock", {"product": "charger"}), ("get_price", {"product": "usb-c cable"})]),
        "USB-C cables are in stock (12 units, $9 each). Chargers are currently out of stock.",
    ]
)


def run(question: str, max_steps: int = 8) -> str:
    messages = [{"role": "user", "content": question}]
    meter = CostMeter()
    for step in range(1, max_steps + 1):  # ALWAYS cap the loop
        response = client.messages.create(
            model=MODEL, max_tokens=4000, system=SYSTEM, tools=registry.schemas(), messages=messages
        )
        meter.add(response)
        if response.stop_reason != "tool_use":
            print(f"\n[{step} model calls | {meter.summary()}]")
            return text_of(response)

        messages.append({"role": "assistant", "content": response.content})
        results = registry.run_calls(response)  # runs read-only calls in parallel
        for r in results:
            print(f"  step {step}: {'ERROR ' if r.get('is_error') else ''}{r['content']}")
        messages.append({"role": "user", "content": results})  # all results in ONE message
    return "Stopped: step limit reached."


if __name__ == "__main__":
    print(run("Do you have USB-C cables and chargers? How much is a cable?"))

# Rules this loop follows (each one is a production bug when broken):
# - Append the assistant's FULL content (not just its text) to the history.
# - Every tool_use id gets exactly one tool_result, all in one user message.
# - Failed tools return is_error results; they are never silently dropped.
# - The loop has a hard step limit.
#
# Try it:
# 1. Set max_steps=1. What does the user see? Design a better message.
# 2. Split the two results into two separate user messages. In live mode the
#    API rejects or the model degrades. Read the error.
# 3. Add a tool `place_order(product, qty)` with read_only=False. Why should it
#    never run in parallel with other calls?
