from pydantic import BaseModel

from aikit import CostMeter, FakeClient, fake_tool, text_of, tool_calls
from aikit.embed import HashEmbedder, cosine


def test_script_replays_in_order():
    c = FakeClient(script=["one", fake_tool("add", {"a": 1})])
    assert text_of(c.messages.create(model="m", messages=[])) == "one"
    r = c.messages.create(model="m", messages=[])
    assert r.stop_reason == "tool_use" and tool_calls(r)[0].input == {"a": 1}
    assert len(c.calls) == 2


def test_parse_validates():
    class P(BaseModel):
        name: str

    r = FakeClient(script=['{"name": "Asha"}']).messages.parse(output_format=P, messages=[])
    assert r.parsed_output.name == "Asha"


def test_cost_meter():
    m = CostMeter(model="claude-haiku-5-5")
    c = FakeClient(script=["hello world"])
    m.add(c.messages.create(messages=[]))
    assert m.calls == 1 and m.usd > 0


def test_hash_embedder_prefers_overlap():
    e = HashEmbedder()
    q, a, b = e.embed(["reset my password", "how to reset a password", "pizza dough recipe"])
    assert cosine(q, a) > cosine(q, b)
