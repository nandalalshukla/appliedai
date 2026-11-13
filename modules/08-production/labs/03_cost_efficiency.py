"""Lab 8.3 - Cost-efficient systems: the same quality for a fraction of the price.

Do the arithmetic before you optimise. This lab prices one workload under
six strategies. No model calls: cost engineering starts on paper.

Run:  python modules/08-production/labs/03_cost_efficiency.py
"""

from aikit.llm import PRICES

# The workload: a support assistant.
REQUESTS_PER_DAY = 50_000
PREFIX_TOKENS = 6_000   # system prompt + tools + policy documents (identical every request)
DYNAMIC_TOKENS = 800    # retrieved chunks + user message
OUTPUT_TOKENS = 300


def daily_cost(model: str, *, cached_prefix: bool = False, batch: bool = False,
               share: float = 1.0, output_tokens: int = OUTPUT_TOKENS,
               prefix_tokens: int = PREFIX_TOKENS) -> float:
    p_in, p_out = PRICES[model]
    prefix_price = p_in * 0.10 if cached_prefix else p_in  # cache reads ~10% of input price
    per_request = (prefix_tokens * prefix_price + DYNAMIC_TOKENS * p_in + output_tokens * p_out) / 1e6
    if batch:
        per_request *= 0.5  # batch APIs are ~50% cheaper, results within hours
    return per_request * REQUESTS_PER_DAY * share


big, small = "claude-opus-5-5", "claude-haiku-5-5"

strategies = {
    "1. baseline: big model, nothing else": daily_cost(big),
    "2. + prompt caching on the prefix": daily_cost(big, cached_prefix=True),
    "3. + trim the prefix 6000 -> 3000 tokens": daily_cost(big, cached_prefix=True, prefix_tokens=3000),
    "4. + shorter answers (300 -> 150 tokens)": daily_cost(big, cached_prefix=True, prefix_tokens=3000,
                                                          output_tokens=150),
    "5. routing: 80% small model, 20% big": (
        daily_cost(small, cached_prefix=True, prefix_tokens=3000, output_tokens=150, share=0.8)
        + daily_cost(big, cached_prefix=True, prefix_tokens=3000, output_tokens=150, share=0.2)),
    "6. + semantic cache answers 25% of traffic": 0.75 * (
        daily_cost(small, cached_prefix=True, prefix_tokens=3000, output_tokens=150, share=0.8)
        + daily_cost(big, cached_prefix=True, prefix_tokens=3000, output_tokens=150, share=0.2)),
}

base = strategies["1. baseline: big model, nothing else"]
print(f"{'strategy':<46}{'$/day':>10}{'$/month':>12}{'vs baseline':>13}")
for name, usd in strategies.items():
    print(f"{name:<46}{usd:>10,.0f}{usd * 30:>12,.0f}{usd / base:>12.0%}")

offline = daily_cost(big, batch=True)
print(f"\nSame workload as a nightly batch job (no user waiting): ${offline:,.0f}/day")

# The levers, in the order to pull them. FREE wins first:
#   a. Prompt caching            no quality change at all
#   b. Fewer input tokens        trim prompts, retrieve fewer/better chunks, truncate tool results
#   c. Fewer output tokens       output costs ~5x input; ask for concise answers, structured output
#   d. Fewer calls               cap agent steps, parallel tool calls, cache results
#   e. Batch API                 ~50% off anything that is not interactive
# Then the ones that TRADE quality, which you may only pull with an eval:
#   f. Lower effort / smaller model for easy steps (routing, cascades)
#   g. Semantic caching          (Module 4)
#
# Before building a multi-model cascade, try the strongest model at LOWER
# effort on the same tasks. It is often as good as a cascade, far simpler,
# and keeps one prompt cache instead of several.
#
# Measure cost per SUCCESSFUL TASK, not per request. A cheap model that needs
# three attempts, or produces answers users reject, is not cheap.
#
# Try it:
# 1. Put your own project's numbers in. What is your cost per request? Per user per month?
# 2. Where is the break-even: at what share of "easy" traffic does routing stop paying
#    for its added complexity?
# 3. Add a per-user daily budget: what should the product do when it is reached?
