"""Lab 6.1 - Working memory: budgeting the context window.

The context window is the agent's working memory. Left alone it fills with
old turns and tool output until quality drops and calls get slow and
expensive. Three strategies, cheapest first:

  1. TRIM     drop the oldest turns          (free, forgets everything dropped)
  2. CLEAR    blank out old tool results     (cheap, keeps the conversation shape)
  3. COMPACT  summarise old turns with a model (costs a call, keeps the gist)

Run:  python modules/06-memory-multi-agent/labs/01_working_memory.py
"""

from aikit import get_client
from aikit.memory import compact, estimate_tokens, safe_cut

# A long support conversation with a crucial fact at the very start.
history = [
    {"role": "user", "content": "Hi, I'm Asha. My account id is ACC-7781 and I'm on the Team plan."},
    {"role": "assistant", "content": "Thanks Asha. How can I help?"},
]
for i in range(1, 9):
    history.append({"role": "user", "content": f"Question {i}: " + "please explain this setting in detail. " * 20})
    history.append({"role": "assistant", "content": f"Answer {i}: " + "here is a long explanation. " * 30})
history.append({"role": "user", "content": "OK. Can you upgrade my storage now?"})

BUDGET = 1500  # tokens we allow the history to occupy
print(f"history: {len(history)} messages, ~{estimate_tokens(history)} tokens (budget {BUDGET})\n")

# --- Strategy 1: trim --------------------------------------------------------
trimmed = history[safe_cut(history, keep_last=5):]
print(f"1. TRIM    -> {len(trimmed)} messages, ~{estimate_tokens(trimmed)} tokens")
print("   account id still present?", any("ACC-7781" in str(m["content"]) for m in trimmed))

# --- Strategy 2: clear old bulky content -------------------------------------
cleared = [
    m if i >= len(history) - 5 or len(str(m["content"])) < 200
    else {"role": m["role"], "content": "[older content cleared to save space]"}
    for i, m in enumerate(history)
]
print(f"2. CLEAR   -> {len(cleared)} messages, ~{estimate_tokens(cleared)} tokens")
print("   account id still present?", any("ACC-7781" in str(m["content"]) for m in cleared))

# --- Strategy 3: compact -----------------------------------------------------
client = get_client(script=[
    "User is Asha, account ACC-7781, Team plan. She asked eight questions about settings, all "
    "answered. No actions taken yet. Open: none before her latest message."
])
compacted = compact(client, history, keep_last=5)
print(f"3. COMPACT -> {len(compacted)} messages, ~{estimate_tokens(compacted)} tokens")
print("   account id still present?", any("ACC-7781" in str(m["content"]) for m in compacted))
print("\n   first message after compaction:\n   ", str(compacted[0]["content"])[:260].replace("\n", "\n    "), "...")


def within_budget(client, messages: list, budget: int = BUDGET) -> list:
    """The policy you would call before every model request."""
    return compact(client, messages) if estimate_tokens(messages) > budget else messages

# A context budget, written down. Decide it; do not let it happen to you:
#
#   system prompt + tool definitions     fixed       (cache it - Module 8)
#   long-term memories                   small, capped
#   retrieved documents                  capped (top-k, max chars)
#   conversation history                 compact above a threshold
#   room for the answer                  max_tokens
#
# Rules that keep compaction correct:
# - Never separate a tool_use from its tool_result (safe_cut handles this).
# - Compact at a threshold well BELOW the hard limit (e.g. 60-70%), not at 99%.
# - A summary is lossy. IDs, numbers and decisions must be called out in the
#   summary prompt, or stored outside the context (a notes file, a database).
# - Some APIs offer server-side compaction and tool-result clearing. Same idea.
#
# Try it:
# 1. Trim with keep_last=5 and ask the model (live) "what is my account id?".
# 2. Make the summariser drop the account id. How would an eval catch that?
# 3. Give the agent a `save_note(text)` tool and tell it to store key facts as
#    it goes. Now compaction can be aggressive. This is "structured note-taking".
