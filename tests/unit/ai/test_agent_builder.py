from types import SimpleNamespace

from backend.ai.agents.builder import build_agent


def make_agent_model(**kwargs):
    # Provide defaults similar to DB model
    defaults = dict(
        name="generic_agent",
        model="phi3:mini",
        num_ctx=1024,
        tools=[],
        role="role",
        task="task",
        constraints=None,
        rules=None,
        output_schema=None,
        response_schema=None,
        examples=None,
        max_clarifications=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_builder_attaches_response_schema_and_examples():
    am = make_agent_model(response_schema={"foo": "bar"}, examples=[{"in": 1}], max_clarifications=2)
    agent = build_agent(am)
    assert hasattr(agent, "response_schema")
    assert agent.response_schema == {"foo": "bar"}
    assert hasattr(agent, "examples")
    assert agent.examples == [{"in": 1}]
    assert hasattr(agent, "max_clarifications")
    assert agent.max_clarifications == 2


def test_builder_parses_legacy_output_schema():
    am = make_agent_model(response_schema=None, output_schema='{"legacy": true}', examples=None)
    agent = build_agent(am)
    assert hasattr(agent, "response_schema")
    assert agent.response_schema == {"legacy": True}
