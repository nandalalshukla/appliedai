"""Lab 1.3 - Your first model call, and reading everything that comes back.

Run:  python modules/01-foundations/labs/03_first_call.py
"""

from aikit import MODEL, CostMeter, get_client, mock_mode

client = get_client(script=["A token is a chunk of text, often part of a word, that a model reads and writes."])

response = client.messages.create(
    model=MODEL,
    max_tokens=1000,  # hard cap on the length of the reply
    system="You are a patient tutor. Answer in one sentence.",  # standing instructions
    messages=[{"role": "user", "content": "What is a token?"}],  # the conversation so far
)

print("mode:       ", "mock" if mock_mode() else "live")

# 1. The answer. `content` is a LIST of blocks, not a string. A reply can mix
#    text, thinking and tool calls, so always check the block type.
for block in response.content:
    if block.type == "text":
        print("answer:     ", block.text)

# 2. Why the model stopped. Check this on every call.
#    end_turn   - finished naturally
#    max_tokens - cut off: your cap was too low
#    tool_use   - it wants you to run a tool (Module 3)
#    refusal    - it declined
print("stop_reason:", response.stop_reason)

# 3. What it cost. You pay per token, and output tokens cost about 5x input.
meter = CostMeter()
meter.add(response)
print("usage:      ", meter.summary())

# Try it:
# 1. Set max_tokens=5. What is stop_reason now? What would your app show the user?
# 2. Remove the system prompt. How does the answer change?
# 3. Ask "What is today's date?" Why can the model not know? (See "knowledge
#    cutoff" in the lesson.) How would a product fix this?
