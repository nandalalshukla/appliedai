"""Lab 3.1 - One tool call, by hand, with nothing hidden.

The model cannot run code. "Tool use" is a conversation protocol:

  1. You describe tools (name, description, JSON schema).
  2. The model replies with a tool_use block: "please call X with these args".
  3. YOUR code runs X.
  4. You send the result back in a tool_result block.
  5. The model writes the final answer.

Run:  python modules/03-tool-use/labs/01_tool_by_hand.py
"""

from aikit import MODEL, fake_tool, get_client, text_of

ORDERS = {"A-4471": {"status": "shipped", "eta": "2026-11-15"}}


def get_order_status(order_id: str) -> dict:
    return ORDERS.get(order_id) or {"error": f"No order with id {order_id}"}


TOOLS = [
    {
        "name": "get_order_status",
        "description": (
            "Look up the shipping status and estimated delivery date of a customer order. "
            "Use this whenever the customer asks where their order is. "
            "Returns status ('processing', 'shipped', 'delivered') and eta (YYYY-MM-DD)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID exactly as the customer wrote it, e.g. 'A-4471'.",
                }
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
    }
]

client = get_client(
    script=[
        fake_tool("get_order_status", {"order_id": "A-4471"}, text="Let me check that order."),
        "Your order A-4471 has shipped and should arrive on 15 November 2026.",
    ]
)

messages = [{"role": "user", "content": "Where is my order A-4471?"}]

# --- Step 2: the model asks for a tool ---------------------------------------
response = client.messages.create(model=MODEL, max_tokens=4000, tools=TOOLS, messages=messages)
print("stop_reason:", response.stop_reason)  # "tool_use"

call = next(b for b in response.content if b.type == "tool_use")
print(f"model wants: {call.name}({call.input})   id={call.id}")

# --- Step 3: we run it --------------------------------------------------------
result = get_order_status(**call.input)
print("we ran it ->", result)

# --- Step 4: send the result back --------------------------------------------
# The assistant turn (with its tool_use block) must be in the history, followed
# by a user turn holding a tool_result with the SAME id.
messages.append({"role": "assistant", "content": response.content})
messages.append(
    {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": call.id, "content": str(result)}],
    }
)

# --- Step 5: the model answers ------------------------------------------------
final = client.messages.create(model=MODEL, max_tokens=4000, tools=TOOLS, messages=messages)
print("\nfinal answer:", text_of(final))

# Try it:
# 1. Ask "What's the weather?" in live mode. The model should answer without a
#    tool call: stop_reason is "end_turn". Your code must handle both paths.
# 2. Ask about order "Z-999". The tool returns an error dict. What does the
#    model tell the user?
# 3. Shorten the description to "Gets order." Ask "has my parcel left yet?
#    it's A-4471". Does the model still call the tool? Descriptions are prompts.
