# Module 3: Tool use

**Week 5.** A model alone can only produce text. Tools let it look things up, compute exactly, and act: query a database, call an API, send an email. Tools are what turn a chatbot into a product, and they are where most production incidents start.

Labs: [`labs/`](labs/) · Toolkit code to read: [`aikit/tools.py`](../../aikit/tools.py)

---

## 3.1 How tool use works

Run [Lab 3.1](labs/01_tool_by_hand.py). The key fact: **the model never executes anything.** Tool use is a protocol in the conversation:

```
you ──► tools + question ─────────────────────► model
you ◄── tool_use {name, input, id} ◄─────────── model     stop_reason = "tool_use"
you run the function yourself
you ──► tool_result {tool_use_id, content} ───► model
you ◄── final answer ◄──────────────────────── model     stop_reason = "end_turn"
```

Because your code sits in the middle of every call, you can validate, log, rate-limit, ask a human, or refuse. That middle position is the whole basis of agent safety.

Three history rules that cause most first-week bugs:

1. Append the assistant's **entire** `content` (text and `tool_use` blocks) to the history, not only its text.
2. Each `tool_use` block gets exactly one `tool_result` with the same `tool_use_id`.
3. All results for one assistant turn go back in **one** user message.

## 3.2 Tool schema design

A tool definition has three parts, and the model reads all three as prompt text:

```python
{
  "name": "get_order_status",
  "description": "Look up the shipping status and estimated delivery date of a customer order. "
                 "Use this whenever the customer asks where their order is. "
                 "Returns status ('processing', 'shipped', 'delivered') and eta (YYYY-MM-DD).",
  "input_schema": { "type": "object",
                    "properties": {"order_id": {"type": "string",
                                   "description": "Order ID exactly as the customer wrote it, e.g. 'A-4471'."}},
                    "required": ["order_id"], "additionalProperties": False },
}
```

**Design tools for the model the way you design an API for a junior developer who cannot ask you questions.**

| Principle | Poor | Better |
|---|---|---|
| Name says what it does | `query`, `handler2` | `search_orders`, `cancel_order` |
| Description says **what, when, and what comes back** | "Gets order." | See above |
| Parameters are unambiguous | `id` | `order_id`, with an example |
| Constrain with types | `sort: string` | `sort: enum["relevance","price"]` |
| Make wrong calls impossible | `date: string` | `date` with format and an example; validate in code |
| Fewer, higher-level tools | `list_users`, `get_user`, `get_user_orders` chained every time | `find_customer_orders(email)` |
| Return what the model needs | 400-line raw JSON with internal IDs | The 5 relevant fields, human-readable names |
| Errors that teach | `"Error 422"` | `"No order 'A-44'. IDs look like 'A-4471'. Ask the customer to confirm."` |

More guidance worth internalizing:

- **Match tools to tasks, not to your REST endpoints.** If a job always takes three calls in a fixed order, that is one tool.
- **Keep the tool list small and distinct.** Overlapping tools (`search`, `find`, `lookup`) make the model hesitate and choose wrongly. With dozens of tools, load definitions on demand (tool search) instead of sending all of them.
- **Control result size.** Add `limit`, pagination or a `fields` parameter; truncate with a note saying how to get the rest. Tool results are often the largest thing in the context window.
- **Use strict schemas.** With `"strict": true` on a tool (and `additionalProperties: false`), the provider guarantees arguments match your schema. Still validate *values* yourself.
- **Test tools with the model, not only with unit tests.** Give it realistic tasks and read the transcripts. Where it stumbles, fix the description first.

## 3.3 Tool infrastructure

Run [Lab 3.2](labs/02_tool_registry.py) with [`aikit/tools.py`](../../aikit/tools.py) open. Hand-written dispatch does not scale, so every serious codebase has a tool layer with these responsibilities:

| Responsibility | Why | In `aikit/tools.py` |
|---|---|---|
| Schema from code | One source of truth; description and code cannot drift | `@registry.tool()` builds a Pydantic model from the signature |
| Argument validation | The model can send wrong types, missing fields, invented values | `args_model.model_validate` |
| Timeouts | One hung HTTP call must not hang the agent | per-tool `timeout_s` |
| Errors become messages | A raised exception kills the loop; a message lets the model recover | `execute()` never raises |
| Result truncation | A 2 MB log file will blow the context window and the bill | `max_result_chars` |
| Permissions | Some tools need a human to approve | `needs_approval` (used in Module 5) |
| Concurrency rules | Reads can run in parallel; writes must not | `read_only` |
| Logging | Every incident review starts with "what did it call?" | `registry.log` |
| Stable ordering | Tool order affects prompt caching | `schemas()` sorts by name |

### MCP: tools as a shared standard

The **Model Context Protocol (MCP)** is an open standard for exposing tools (and data and prompts) to AI applications. Instead of writing a custom integration for every app, a service ships one MCP server and any MCP-capable client (Claude, IDEs, your own agent) can use it. Think "USB for tools". You will meet it constantly at work:

- Use an existing MCP server when one exists for the system you need (GitHub, Slack, databases, browsers).
- Write one when several agents or teams need the same internal tools.
- An MCP server is still a set of tools with names, descriptions and schemas, so everything in 3.2 applies.
- Treat third-party MCP servers as untrusted code *and* untrusted content: their tool descriptions and results enter your model's context.

## 3.4 The tool loop

Run [Lab 3.3](labs/03_tool_loop.py). Real tasks take several calls, so you loop until the model stops asking:

```python
for step in range(max_steps):                         # always capped
    response = client.messages.create(model=MODEL, max_tokens=4000, system=SYSTEM,
                                      tools=registry.schemas(), messages=messages)
    if response.stop_reason != "tool_use":
        return text_of(response)
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": registry.run_calls(response)})
```

That loop is the seed of every agent in Module 5. Notice in the lab output:

- **Parallel tool use.** The model asked for two lookups in one turn. Independent read-only calls run concurrently, which cuts latency.
- **Self-correction.** One call had a typo. The error message listed the valid product names, so the next turn fixed it.

The SDK also ships a *tool runner* that drives this loop for you. Use it at work; write the loop by hand here, because you cannot debug what you have never built.

## 3.5 Production gotchas

These are the things that break after the demo. Each has cost somebody a weekend.

**Correctness**

1. **The model calls a tool with invented arguments** (an order ID that was never mentioned). Validate against real data; return an error that says what a valid value looks like.
2. **The model answers from memory instead of calling the tool.** Say in the system prompt when tool use is mandatory ("never state a price without calling `get_price`") and check for it in evals.
3. **The model claims it did something it did not.** "I've sent the email" with no `send_email` call in the trace. Verify actions from the tool log, never from the model's words.
4. **Wrong tool chosen.** Usually overlapping descriptions. Merge or sharpen the tools.
5. **You cannot force a specific tool on some models.** Current Claude models reject forced `tool_choice`; steer with the prompt and verify the call happened.

**Safety**

6. **Tool results are untrusted input.** A web page or email returned by a tool can contain instructions (prompt injection). Never give one agent both untrusted content and a dangerous tool without a human check between them.
7. **Least privilege.** A read-only database user for a read-only tool. Scope API keys per tool. The model should be *unable* to do damage, not merely told not to.
8. **Irreversible actions need confirmation**: payments, deletions, outbound messages. Gate them in code (Module 5), not in the prompt.

**Reliability**

9. **Retries can repeat side effects.** If `charge_card` times out and the model retries, you may charge twice. Make write tools **idempotent**: accept an idempotency key and return the earlier result on repeats.
10. **Unbounded loops.** A model can call the same failing tool forever. Cap steps, cap spend, detect repeated identical calls.
11. **Timeouts everywhere.** On each tool and on the whole task.
12. **Partial failure.** Three of four parallel calls succeed. Return all four results, one marked `is_error`. Never drop one; the API requires a result per call.

**Cost and latency**

13. **Tool definitions cost tokens on every request.** Twenty verbose tools can be thousands of tokens before the user says anything. Keep the set small; cache it (Module 8).
14. **Huge results.** Truncate, paginate, summarize, or write to a file and return the path.
15. **Sequential calls that could be parallel.** Mark read-only tools and run them together.

**Operations**

16. **Changing a description is a behaviour change.** Version tools and re-run evals, as with prompts.
17. **Log every call**: name, arguments, result size, duration, error flag, and the conversation it belongs to.

---

## Checkpoint

1. Who executes a tool, the model or your code? Why does that matter for safety?
2. What three things must a good tool description state?
3. A tool raises an exception. What should the model receive, and why not let the exception propagate?
4. What is an idempotency key, and which gotcha does it solve?
5. Why should read tools and write tools be treated differently when the model requests several calls at once?
6. The model says "I've cancelled your order" but the order is still active. How do you find out what happened, and how do you prevent this class of bug?
7. What problem does MCP solve?

## Exercises

1. **Calculator.** Add a `calculate(expression: str)` tool that safely evaluates arithmetic (use `ast`, never `eval`). Ask a question that needs exact math on large numbers, with and without the tool.
2. **Idempotent write.** Implement `create_refund(order_id, amount_usd, idempotency_key)` backed by a dict. Prove that calling it twice with the same key refunds once.
3. **Loop detector.** Extend Lab 3.3 so that three identical calls in a row stop the loop with a clear message. Script a `FakeClient` that triggers it.

## Go deeper

[Module 3 in RESOURCES.md](../../RESOURCES.md#module-3-tool-use).

Next: [Module 4: Retrieval-augmented generation](../04-rag/README.md)
