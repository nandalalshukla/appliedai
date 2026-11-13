"""Lab 7.2 - Model-graded evals (LLM-as-judge), and checking the judge.

Code can check "is the label right". It cannot check "is this reply polite,
accurate and free of promises we can't keep". For that you use a model as the
grader - and then you must test the grader, because a judge you have not
validated is just a second opinion you made up.

Run:  python modules/07-evals-safety/labs/02_llm_judge.py
"""

import json

from aikit import get_client
from aikit.evals import Case, llm_judge, max_words, run_eval

POLICY = "Monthly plans: full refund within 14 days of the charge. Refunds take 5-10 business days."

# Each case: a customer message + the reply our system produced.
# `human` is the label a person gave. We need these to validate the judge.
REPLIES = [
    {"id": "j1", "msg": "I was charged 3 days ago, can I get a refund?",
     "reply": "Yes. You are within the 14 day window, so you qualify for a full refund. It takes 5-10 business days to arrive.",
     "human": True},
    {"id": "j2", "msg": "I was charged 3 days ago, can I get a refund?",
     "reply": "Yes! Your refund will be in your account tomorrow.",
     "human": False},  # invents a timeline
    {"id": "j3", "msg": "I was charged 40 days ago, can I get a refund?",
     "reply": "Of course, I've approved your full refund.",
     "human": False},  # contradicts the policy
    {"id": "j4", "msg": "I was charged 40 days ago, can I get a refund?",
     "reply": "I'm sorry, refunds are only available within 14 days of the charge, so this one is outside the window.",
     "human": True},
    {"id": "j5", "msg": "Can I get a refund?",
     "reply": "Refunds are available within 14 days of a charge. When were you charged?",
     "human": True},
    {"id": "j6", "msg": "I was charged 10 days ago, refund please.",
     "reply": "You qualify for a full refund within 14 days. We also guarantee a 20% bonus credit for the trouble.",
     "human": False},  # invents a benefit
]

cases = [Case(r["id"], r["msg"], expected=POLICY, tags=["refund"]) for r in REPLIES]
reply_for = {r["id"]: r["reply"] for r in REPLIES}

# ONE criterion, stated precisely, with the reference material the judge needs.
CRITERION = ("Every factual claim in the response about refunds (eligibility, amounts, timing, "
             "extras) is supported by the reference policy. A response that asks a clarifying "
             "question without making unsupported claims passes.")

# Scripted judge: correct on five cases, wrongly lenient on j6 - so you see a disagreement.
verdicts = {"j1": "pass", "j2": "fail", "j3": "fail", "j4": "pass", "j5": "pass", "j6": "pass"}
script = [json.dumps({"reasoning": f"(scripted reasoning for {r['id']})", "verdict": verdicts[r["id"]]})
          for r in REPLIES]
client = get_client(script=script)

case_ids = iter(c.id for c in cases)
report = run_eval(
    "refund-replies",
    cases,
    system=lambda msg: reply_for[next(case_ids)],  # the "system under test" replays stored replies
    scorers=[llm_judge(client, CRITERION, name="faithful_to_policy"), max_words(40)],
)
report.print()

# VALIDATE THE JUDGE against the human labels.
print("\nJUDGE vs HUMAN")
agree = true_fail = caught = 0
for row, r in zip(report.rows, REPLIES):
    judge_pass = next(s for s in row.scores if s.name == "faithful_to_policy").passed
    agree += judge_pass == r["human"]
    if not r["human"]:
        true_fail += 1
        caught += not judge_pass
    mark = "  " if judge_pass == r["human"] else "<- DISAGREE"
    print(f"  {r['id']}: human={'pass' if r['human'] else 'fail'}  judge={'pass' if judge_pass else 'fail'} {mark}")
print(f"\nagreement: {agree}/{len(REPLIES)}   bad replies caught by judge: {caught}/{true_fail}")

# Reading this: 5/6 agreement sounds fine, but the judge MISSED one of three
# bad replies (j6). For a safety-type criterion, "share of bad outputs caught"
# matters more than overall agreement. Fix the judge prompt (add j6 as an
# example of a failing response), re-validate, and only then trust it at scale.
#
# Rules for judges:
# - One criterion per judge. "Rate overall quality 1-10" produces noise.
# - Binary pass/fail beats 1-5 scales: people and models cannot agree on a 3 vs 4.
# - Reasoning first, verdict second.
# - Give the judge the reference (policy, source documents, correct answer).
# - Keep 30-100 human-labelled examples as the judge's own test set.
# - Use a strong model for judging, and do not let the judge see which system
#   version produced the output.
#
# Try it:
# 1. Live mode: does the real judge catch j6? Run it 5 times - is it consistent?
# 2. Write a second judge for tone ("apologises when refusing"). Validate it.
# 3. Replace the judge with a code check where possible (e.g. regex for
#    "tomorrow|guarantee"). Cheaper checks first; judges for the rest.
