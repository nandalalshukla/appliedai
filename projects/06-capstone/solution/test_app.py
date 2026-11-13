"""Tests for the capstone API. Run: pytest projects/06-capstone/solution -q   (offline, mock mode)"""

import json
import os

os.environ["AIKIT_MOCK"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

import app as service  # noqa: E402

client = TestClient(service.app)
KEY = {"x-api-key": "demo-key"}


def events(response) -> list[tuple[str, dict]]:
    out = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        out.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return out


def ask(question: str, session: str = "s1", headers=KEY):
    return client.post("/ask", json={"question": question, "session_id": session}, headers=headers)


def test_requires_api_key():
    assert ask("hello", headers={}).status_code == 401


def test_streams_a_cited_answer():
    r = ask("What does error STG-507 mean?", session="a")
    assert r.status_code == 200
    ev = events(r)
    names = [n for n, _ in ev]
    assert names[0] == "status" and names[-1] == "done" and "token" in names
    text = "".join(d["text"] for n, d in ev if n == "token")
    assert "[1]" in text and "STG-507" in text
    assert ev[-1][1]["sources"][0]["source"] == "storage.md"


def test_unanswerable_question_is_refused_not_invented():
    text = "".join(d["text"] for n, d in events(ask("Do you offer a student discount?", "b")) if n == "token")
    assert text == service.NOT_FOUND


def test_bad_citation_is_retracted():
    ev = events(ask("Please invent a rate limit", session="c"))
    assert any(n == "retract" for n, _ in ev)
    assert ev[-1][1]["sources"] == []


def test_repeat_question_hits_the_cache():
    ask("How long is the password reset email valid?", session="d1")
    ev = events(ask("How long is the password reset email valid?", session="d2"))
    assert ev[-1][1]["cached"] is True


def test_input_guard_blocks_empty_and_redacts_pii():
    assert ask("   ", session="e").status_code == 422
    cleaned, _ = service.input_guard("my card is 4111 1111 1111 1111 and mail a@b.co")
    assert "4111" not in cleaned and "a@b.co" not in cleaned


def test_rate_limit_and_budget():
    service.API_KEYS["tiny"] = {"tenant": "t2", "daily_budget_usd": 5.0, "requests_per_minute": 1}
    assert ask("What is the API rate limit?", "f", {"x-api-key": "tiny"}).status_code == 200
    assert ask("What is the API rate limit?", "f", {"x-api-key": "tiny"}).status_code == 429
    service.API_KEYS["broke"] = {"tenant": "t3", "daily_budget_usd": 0.0, "requests_per_minute": 9}
    assert ask("hello there", "g", {"x-api-key": "broke"}).status_code == 402


def test_metrics_report_activity():
    m = client.get("/metrics").json()
    assert m["requests"] > 0 and "p95" in m["latency_ms"] and m["retracted"] >= 1
