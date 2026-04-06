from src.core.llm_provider import LLMProvider
from src.chatbot.baseline import BaselineChatbot
from src.agent.agent import ReActAgent
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_mock_tools():
    return [
        {
            "name": "lay_tam_tinh",
            "description": "Tra ve gia tam tinh cho san pham. Tham so: ten_san_pham, so_luong",
            "func": lambda product_name, quantity: f"Tam tinh cho {quantity} x {product_name} la 44000000 VND.",
        },
        {
            "name": "tim_ma_tot_nhat",
            "description": "Tim ma giam gia tot nhat theo tam tinh. Tham so: subtotal",
            "func": lambda subtotal: f"Ma WINNER giam 5280000 VND tren muc tam tinh {subtotal} VND.",
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
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "total_tokens": 20,
            },
            "latency_ms": 5,
            "provider": "mock",
        }

    def stream(self, prompt: str, system_prompt=None):
        yield from []


def test_react_agent_can_use_tools_and_finish():
    provider = MockProvider(
        [
            "Suy nghi: Toi can tinh tam tinh truoc.\nHanh dong: lay_tam_tinh(iPhone 15, 2)",
            "Suy nghi: Toi can tim ma giam gia tot nhat.\nHanh dong: tim_ma_tot_nhat(44000000)",
            (
                "Suy nghi: Toi da co du thong tin.\n"
                "Cau tra loi cuoi: Phuong an tot nhat la mua 2 iPhone 15 voi ma WINNER. "
                "Tong tien truoc phi ship la 38720000 VND."
            ),
        ]
    )

    agent = ReActAgent(provider, build_mock_tools(), max_steps=5)
    result = agent.run(
        "Toi can mua 2 iPhone 15. Hay tim ma giam gia tot nhat va tong tien re nhat."
    )

    assert "WINNER" in result
    assert "38720000" in result


def test_baseline_chatbot_returns_direct_answer():
    provider = MockProvider(["Cau tra loi truc tiep khong dung cong cu."])
    chatbot = BaselineChatbot(provider)

    result = chatbot.run("Phuong an re nhat cho iPhone 15 la gi?")

    assert result == "Cau tra loi truc tiep khong dung cong cu."


def test_react_agent_split_args_supports_named_arguments():
    provider = MockProvider(["Cau tra loi cuoi: xong"])
    agent = ReActAgent(provider, build_mock_tools(), max_steps=1)

    parsed = agent._split_args('query="Apple iPhone 13", limit=1')

    assert parsed == ["Apple iPhone 13", "1"]
