from app.agent import SchedulingAgent
from app.llm import ModelTurn, ToolRequest
from app.tools import ClinicStore


class FakeProvider:
    def __init__(self):
        self.tool_result_seen = None

    def start(self, *, system_prompt, user_text, tools):
        return ModelTurn(
            interaction_id="i1",
            tool_requests=[ToolRequest("c1", "get_available_slots", {"specialty": "dermatology", "date": "2026-09-25"})],
        )

    def continue_with_user(self, *, previous_interaction_id, user_text, tools):
        return ModelTurn(text="Follow-up received", interaction_id="i3")

    def continue_with_tools(self, *, previous_interaction_id, tool_results, tools):
        self.tool_result_seen = tool_results[0]
        return ModelTurn(text="I found available dermatology slots.", interaction_id="i2")


def test_agent_executes_tool_and_logs_it():
    provider = FakeProvider()
    agent = SchedulingAgent(patient_id="p1", store=ClinicStore(), provider=provider)

    text = agent.send("I need a dermatologist on September 25")

    assert text == "I found available dermatology slots."
    assert agent.state.tool_calls[0]["name"] == "get_available_slots"
    assert '"ok": true' in provider.tool_result_seen["result_json"]
    assert agent.state.last_interaction_id == "i2"
