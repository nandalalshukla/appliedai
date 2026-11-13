"""Unit tests for the parts of aikit that later modules depend on."""

from pathlib import Path

from aikit import FakeClient, fake_tool
from aikit.agent import Agent
from aikit.evals import Case, compare, exact_match, run_eval
from aikit.memory import compact, estimate_tokens, safe_cut
from aikit.rag import BM25, Chunk, HybridRetriever, chunk_markdown, load_corpus, rrf
from aikit.tools import ToolRegistry

ROOT = Path(__file__).resolve().parent.parent


def make_registry() -> ToolRegistry:
    registry = ToolRegistry(max_result_chars=50)

    @registry.tool()
    def add(a: int, b: int = 1) -> int:
        """Add two integers."""
        return a + b

    @registry.tool()
    def boom() -> str:
        """Always fails."""
        raise RuntimeError("kaput")

    @registry.tool()
    def big() -> str:
        """Returns a long string."""
        return "x" * 500

    return registry


def test_registry_validates_and_never_raises():
    r = make_registry()
    assert r.execute("add", {"a": 2, "b": 3}).content == "5"
    assert r.execute("add", {"a": "two"}).is_error
    assert r.execute("add", {}).is_error
    assert r.execute("nope", {}).is_error
    assert "kaput" in r.execute("boom", {}).content
    assert "truncated" in r.execute("big", {}).content


def test_schemas_are_sorted_and_strict():
    schemas = make_registry().schemas()
    assert [s["name"] for s in schemas] == ["add", "big", "boom"]
    assert schemas[0]["input_schema"]["required"] == ["a"]
    assert schemas[0]["input_schema"]["additionalProperties"] is False


def test_agent_runs_tools_then_finishes():
    client = FakeClient(script=[fake_tool("add", {"a": 2, "b": 2}), "The answer is 4."])
    result = Agent(client, make_registry(), "You add.").run("2+2?")
    assert result.stopped == "done" and result.text == "The answer is 4." and result.steps == 2
    tool_result = client.calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["content"] == "4"


def test_agent_stops_on_step_limit_and_repeated_calls():
    forever = FakeClient(responder=lambda kw: fake_tool("add", {"a": 1}))
    assert Agent(forever, make_registry(), "s", max_steps=10).run("go").stopped == "loop"
    counter = iter(range(100))
    varied = FakeClient(responder=lambda kw: fake_tool("add", {"a": next(counter)}))
    assert Agent(varied, make_registry(), "s", max_steps=4).run("go").stopped == "max_steps"


def test_agent_approval_denial_reaches_the_model():
    registry = ToolRegistry()
    fired = []

    @registry.tool(needs_approval=True, read_only=False)
    def launch() -> str:
        """Do something irreversible."""
        fired.append(1)
        return "launched"

    client = FakeClient(script=[fake_tool("launch", {}), "Not launched."])
    Agent(client, registry, "s", approve=lambda tool, args: False).run("launch it")
    assert not fired
    assert client.calls[1]["messages"][-1]["content"][0]["is_error"] is True


def test_checkpoint_and_resume(tmp_path):
    path = tmp_path / "run.json"
    first = FakeClient(script=[fake_tool("add", {"a": 1})])  # script runs out after one step
    Agent(first, make_registry(), "s", max_steps=1, checkpoint=path).run("go")
    assert path.exists()
    second = FakeClient(script=["done"])
    result = Agent(second, make_registry(), "s", checkpoint=path).resume()
    assert result.text == "done" and result.steps == 2
    assert len(second.calls[0]["messages"]) == 3  # task, tool call, tool result were restored


def test_chunking_and_search():
    chunks = chunk_markdown("# Doc\n## A\n" + "alpha " * 50 + "\n## B\nbeta gamma", "d.md", max_words=20, overlap=5)
    assert len(chunks) > 3 and chunks[0].text.startswith("Doc > A")
    assert BM25(chunks).search("gamma", 1)[0][0].text.startswith("Doc > B")


def test_hybrid_filter_excludes_stale_documents():
    retriever = HybridRetriever(load_corpus(ROOT / "data/handbook"))
    unfiltered = [c.source for c, _ in retriever.search("refund window for monthly plans", 3)]
    filtered = [c.source for c, _ in retriever.search("refund window for monthly plans", 3, {"updated": "2026"})]
    assert "legacy-billing-2023.md" in unfiltered and "legacy-billing-2023.md" not in filtered


def test_rrf_rewards_agreement():
    a, b, c = (Chunk(x, x, "s") for x in "abc")
    assert rrf([[a, b, c], [b, a, c]])[-1][0].id == "c"


def test_compaction_keeps_tool_pairs_together():
    messages = [
        {"role": "user", "content": "task with id ACC-1"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "add", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "2"}]},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "next"},
        {"role": "assistant", "content": "sure"},
    ]
    assert safe_cut(messages, keep_last=4) == 0  # would split the tool pair -> moves back to a plain user turn
    assert safe_cut(messages, keep_last=2) == 4
    out = compact(FakeClient(script=["Summary: task ACC-1."]), messages, keep_last=2)
    assert len(out) == 2 and "ACC-1" in out[0]["content"] and out[0]["content"].endswith("next")
    assert estimate_tokens(out) > 0


def test_eval_compare_finds_regressions():
    cases = [Case("a", "x", "x"), Case("b", "y", "y")]
    before = run_eval("v1", cases, lambda i: i if i == "x" else "wrong", [exact_match])
    after = run_eval("v2", cases, lambda i: i if i == "y" else "wrong", [exact_match])
    assert compare(before, after) == {"fixed": ["b"], "regressed": ["a"]}
