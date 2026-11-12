"""Lab 1.5 - Streaming: show words as they are generated.

Users judge speed by time-to-first-word, not total time. Streaming does not
make the model faster; it makes the wait visible.

Run:  python modules/01-foundations/labs/05_streaming.py
"""

import time

from aikit import MODEL, get_client

client = get_client(
    script=["Streaming sends the reply piece by piece, so the user starts reading immediately."]
)

start = time.perf_counter()
first_token_at = None

with client.messages.stream(
    model=MODEL,
    max_tokens=2000,
    messages=[{"role": "user", "content": "In one sentence, why do chat apps stream?"}],
) as stream:
    for piece in stream.text_stream:
        if first_token_at is None:
            first_token_at = time.perf_counter() - start
        print(piece, end="", flush=True)
    final = stream.get_final_message()  # the complete response, with usage

total = time.perf_counter() - start
print(f"\n\ntime to first token: {first_token_at:.2f}s | total: {total:.2f}s")
print("stop_reason:", final.stop_reason)

# Try it (live mode):
# 1. Ask for a 500-word essay. Compare time-to-first-token with total time.
# 2. These two numbers (TTFT and total latency) are the ones you will put on a
#    dashboard in Module 8.
