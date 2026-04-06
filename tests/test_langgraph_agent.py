from src.core.llm_provider import LLMProvider
from src.agent.langgraph_agent import LangGraphShoppingAgent
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_mock_tools():
    return [
        {
            "name": "tim_re_nhat",
            "description": "Tim lua chon re nhat. Tham so: query, quantity",
            "func": lambda query, quantity: f"Lua chon re nhat cho {quantity} x {query} la 11380000 VND.",
        },
    ]


class MockProvider(LLMProvider):
    def __init__(self, scripted_responses):
        super().__init__(model_name="mock-model")
        self.scripted_responses = scripted_responses
        self.index = 0

    def generate(self, prompt: str, system_prompt=None):
        content = self.scripted_responses[self.index]
        self.index += 1
        return {
            "content": content,
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 14,
                "total_tokens": 26,
            },
            "latency_ms": 6,
            "provider": "mock",
        }

    def stream(self, prompt: str, system_prompt=None):
        yield from []


def test_langgraph_agent_can_use_tool_and_finish():
    provider = MockProvider(
        [
            "Suy nghi: Toi can tim lua chon re nhat.\nHanh dong: tim_re_nhat(Sony WH-1000XM5, 2)",
            "Cau tra loi cuoi: Phuong an tot nhat la mua 2 Sony WH-1000XM5 voi tong gia 11380000 VND.",
        ]
    )

    agent = LangGraphShoppingAgent(provider, build_mock_tools(), max_steps=4)
    result = agent.run(
        "Toi can mua 2 Sony WH-1000XM5. Hay tim phuong an re nhat."
    )

    assert "11380000" in result
    assert agent.last_run_details["steps"] == 2
    assert len(agent.last_run_details["tool_calls"]) == 1
