from app.agent import SchedulingAgent
from app.llm import ModelTurn, ToolRequest
from app.tools import ClinicStore


class FakeProvider:
    def __init__(self):
        self.tool_result_seen = None
        self.continued_from = None
        self.user_follow_up = None

    def start(self, *, system_prompt, user_text, tools):
        return ModelTurn(
            interaction_id="i1",
            tool_requests=[
                ToolRequest(
                    "c1",
                    "get_available_slots",
                    {"specialty": "dermatology", "date": "2026-09-25"},
                )
            ],
        )

    def continue_with_user(self, *, previous_interaction_id, user_text, tools):
        self.continued_from = previous_interaction_id
        self.user_follow_up = user_text
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
    assert agent.state.tool_calls[0]["turn"] == 1
    assert '"ok": true' in provider.tool_result_seen["result_json"]
    assert agent.state.last_interaction_id == "i2"


def test_second_user_turn_continues_previous_interaction():
    provider = FakeProvider()
    agent = SchedulingAgent(patient_id="p1", store=ClinicStore(), provider=provider)

    agent.send("Show me dermatology appointments on September 25")
    response = agent.send("The afternoon works for me")

    assert response == "Follow-up received"
    assert provider.continued_from == "i2"
    assert provider.user_follow_up == "The afternoon works for me"
    assert agent.state.user_turns == 2
    assert [item["role"] for item in agent.state.transcript] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
