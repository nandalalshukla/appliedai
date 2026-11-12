# Module 0: Setup

**Goal:** a working environment and one successful lab run. Budget: 30-60 minutes.

## 1. Install the tools

| Tool | Why | Check |
|---|---|---|
| Python 3.10+ | All course code | `python --version` |
| Git | Get the course, save your work | `git --version` |
| A code editor | VS Code is a good default | - |

If Python is missing, install it from [python.org](https://www.python.org/downloads/). On Windows, tick "Add Python to PATH" in the installer.

## 2. Get the course and install it

```bash
git clone https://github.com/nandalalshukla/appliedai.git
cd appliedai

python -m venv .venv            # an isolated place for this course's packages
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .                # installs the course toolkit, `aikit`
```

**What is a virtual environment?** A folder (`.venv`) holding this project's packages so they do not clash with other projects. You must run the `activate` line every time you open a new terminal. Your prompt shows `(.venv)` when it is active.

## 3. Check that it works

```bash
pytest -q
python modules/01-foundations/labs/01_tokens.py
```

All tests should pass, and the lab should print a tokenizer learning merges. Neither needs an API key.

## 4. Get an API key (optional at first, important later)

1. Create an account at [platform.claude.com](https://platform.claude.com/), add a small amount of credit, and create an API key.
2. Copy the example config and paste the key in:

```bash
cp .env.example .env
```

```ini
# .env
ANTHROPIC_API_KEY=sk-ant-...
AIKIT_MODEL=claude-haiku-5-5     # cheapest; good for learning
```

3. Run a live call:

```bash
python modules/01-foundations/labs/03_first_call.py
```

You should see a real answer and a line showing tokens used and cost.

### Three rules for API keys

1. **Never commit a key.** `.env` is already in `.gitignore`. If a key ever reaches GitHub, revoke it in the console immediately; bots scan for them within minutes.
2. **Set a spending limit** in the provider console. An agent stuck in a loop can spend real money.
3. **Never put a key in frontend code.** Keys live on servers only.

### Which model should I use?

| Model | Input / output per 1M tokens | Use it for |
|---|---|---|
| `claude-haiku-5-5` | $0.10 / $0.50 | Learning, high-volume simple tasks |
| `claude-sonnet-5-5` | $2 / $10 | Everyday agent and coding work |
| `claude-opus-5-5` | $4 / $20 | Hard reasoning, the course default |

Prices change; check the provider's pricing page before budgeting a real product. Labs read the model from `AIKIT_MODEL`, so you can switch without touching code. A good habit: develop on the cheap model, then run your evals (Module 7) on a stronger one to see whether it is worth the price.

## 5. How mock mode works

When no key is set (or `AIKIT_MOCK=1`), `aikit.get_client()` returns a `FakeClient` instead of the real client. Each lab hands it a script of responses to replay:

```python
from aikit import get_client, text_of, MODEL

client = get_client(script=["Paris."])        # the script is used only in mock mode
response = client.messages.create(
    model=MODEL, max_tokens=1000,
    messages=[{"role": "user", "content": "Capital of France?"}],
)
print(text_of(response))
```

The call (`client.messages.create(...)`) and the response shape are identical in both modes. Read [`aikit/llm.py`](../../aikit/llm.py) once; it is under 200 lines and you will write something like it at every job.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: aikit` | Virtual environment not active, or you skipped `pip install -e .` |
| `python: command not found` | Try `python3`. On Windows try `py` |
| `AuthenticationError` / 401 | Key is wrong or `.env` is not in the folder you run from. Run from the repository root |
| `RateLimitError` / 429 | You are sending too fast or are out of credit. Wait, then check the console |
| `NotFoundError` for the model | Typo in `AIKIT_MODEL`. Use an ID from the table above exactly |
| Lab prints `[mock] ...` when you expected a real answer | No key found. Check `.env`, and that `AIKIT_MOCK` is empty |
| `BadRequestError` mentioning `temperature` | Current Claude models do not accept sampling parameters. See Module 1 |
| Output stops mid-sentence | `stop_reason` is `max_tokens`. Raise `max_tokens` |
| `pip install` fails on Windows with long paths | Clone the repository to a short path such as `C:\ai` |
| Tests fail right after cloning | Run `pip install -r requirements.txt` again inside the activated environment |

## Done when

- [ ] `pytest -q` passes
- [ ] `01_tokens.py` runs
- [ ] (When you have a key) `03_first_call.py` prints a real answer and a cost

Next: [Module 1: Foundations](../01-foundations/README.md)
