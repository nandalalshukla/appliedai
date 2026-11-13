"""aikit.evals - a small eval harness: cases in, scores out, regressions flagged.

    Case            one test input with what a good output looks like
    scorers         functions (case, output) -> Score      [code-graded or model-graded]
    run_eval(...)   run a system over cases, apply scorers -> Report
    compare(a, b)   which cases got better or worse between two reports
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .llm import MODEL, text_of


@dataclass
class Case:
    id: str
    input: Any
    expected: Any = None
    tags: list[str] = field(default_factory=list)  # e.g. ["billing", "hard", "adversarial"]


@dataclass
class Score:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Row:
    case_id: str
    tags: list[str]
    input: Any
    output: Any
    scores: list[Score]
    seconds: float
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.error and all(s.passed for s in self.scores)


Scorer = Callable[[Case, Any], Score]


# -- code-graded scorers: fast, free, deterministic. Prefer these. ------------

def exact_match(case: Case, output: Any) -> Score:
    return Score("exact_match", str(output).strip().lower() == str(case.expected).strip().lower(),
                 f"expected {case.expected!r}, got {output!r}")


def contains_all(case: Case, output: Any) -> Score:
    """case.expected is a list of substrings that must all appear."""
    missing = [s for s in case.expected if s.lower() not in str(output).lower()]
    return Score("contains_all", not missing, f"missing {missing}" if missing else "")


def contains_none(forbidden: list[str]) -> Scorer:
    def scorer(case: Case, output: Any) -> Score:
        found = [s for s in forbidden if s.lower() in str(output).lower()]
        return Score("contains_none", not found, f"found forbidden {found}" if found else "")

    return scorer


def max_words(limit: int) -> Scorer:
    def scorer(case: Case, output: Any) -> Score:
        n = len(str(output).split())
        return Score(f"max_words_{limit}", n <= limit, f"{n} words")

    return scorer


# -- model-graded scorer: for qualities code cannot check ---------------------

JUDGE_SYSTEM = """You are a strict grader. You are given a task input, a response, and ONE criterion.
Decide whether the response meets the criterion.

First write your reasoning in one or two sentences, quoting the response where relevant.
Then give the verdict. Return JSON: {"reasoning": "...", "verdict": "pass" | "fail"}
Judge only the stated criterion. If you cannot tell, the verdict is "fail"."""


def llm_judge(client, criterion: str, name: str = "judge", model: str = MODEL) -> Scorer:
    """One criterion per judge. Binary verdict. Reasoning before verdict."""

    def scorer(case: Case, output: Any) -> Score:
        prompt = (f"<input>\n{case.input}\n</input>\n\n<response>\n{output}\n</response>\n\n"
                  f"<reference>\n{case.expected}\n</reference>\n\n<criterion>\n{criterion}\n</criterion>")
        try:
            raw = text_of(client.messages.create(
                model=model, max_tokens=4000, system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": prompt}]))
            data = json.loads(raw)
            return Score(name, data["verdict"] == "pass", data.get("reasoning", ""))
        except Exception as e:  # a broken judge must not look like a passing case
            return Score(name, False, f"judge error: {e}")

    return scorer


# -- running and reporting ----------------------------------------------------

@dataclass
class Report:
    name: str
    rows: list[Row]

    @property
    def pass_rate(self) -> float:
        return sum(r.passed for r in self.rows) / max(1, len(self.rows))

    def by_tag(self) -> dict[str, tuple[int, int]]:
        out: dict[str, list[int]] = {}
        for r in self.rows:
            for tag in r.tags or ["untagged"]:
                bucket = out.setdefault(tag, [0, 0])
                bucket[0] += r.passed
                bucket[1] += 1
        return {t: (p, n) for t, (p, n) in sorted(out.items())}

    def failures(self) -> list[Row]:
        return [r for r in self.rows if not r.passed]

    def print(self, show_failures: int = 5) -> None:
        n = len(self.rows)
        print(f"\n== {self.name}: {sum(r.passed for r in self.rows)}/{n} passed ({self.pass_rate:.0%})")
        for tag, (p, total) in self.by_tag().items():
            print(f"   {tag:<14}{p}/{total}")
        for r in self.failures()[:show_failures]:
            why = r.error or "; ".join(f"{s.name}: {s.detail}" for s in r.scores if not s.passed)
            print(f"   FAIL {r.case_id}: {why[:150]}")

    def save(self, directory: str | Path = "runs/evals") -> Path:
        path = Path(directory) / f"{self.name}-{int(time.time())}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(asdict(r), default=str) for r in self.rows))
        return path


def run_eval(name: str, cases: list[Case], system: Callable[[Any], Any], scorers: list[Scorer]) -> Report:
    """`system` is the thing under test: a function from case.input to an output."""
    rows = []
    for case in cases:
        start = time.perf_counter()
        try:
            output, error = system(case.input), ""
        except Exception as e:  # a crash is a failed case, not a failed eval run
            output, error = None, f"{type(e).__name__}: {e}"
        scores = [] if error else [scorer(case, output) for scorer in scorers]
        rows.append(Row(case.id, case.tags, case.input, output, scores,
                        round(time.perf_counter() - start, 3), error))
    return Report(name, rows)


def compare(baseline: Report, candidate: Report) -> dict[str, list[str]]:
    """Case-level diff. The overall pass rate can hide a fix that broke something else."""
    before = {r.case_id: r.passed for r in baseline.rows}
    after = {r.case_id: r.passed for r in candidate.rows}
    shared = before.keys() & after.keys()
    return {
        "fixed": sorted(i for i in shared if not before[i] and after[i]),
        "regressed": sorted(i for i in shared if before[i] and not after[i]),
    }
