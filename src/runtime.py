import os
from typing import Dict, Any

from dotenv import load_dotenv

from src.agent.agent import ReActAgent
from src.agent.langgraph_agent import LangGraphShoppingAgent
from src.chatbot.baseline import BaselineChatbot
from src.telemetry.metrics import tracker
from src.tools.tiki_tools import build_tiki_tools


TIKI_TEST_CASES = [
    "Hay tim tren Tiki va cho toi biet gia cong khai hien tai cua Apple iPhone 13.",
    "Hay tim lua chon cong khai re nhat tren Tiki cho Apple iPhone 14.",
    "Toi muon mua 2 chiec Apple iPhone 13. Hay dung ket qua tren Tiki va tinh tong tien cong khai re nhat.",
    "Hay so sanh cac lua chon hang dau tren Tiki cho Sony WH-1000XM5 va cho toi biet nguoi ban nao dang co gia cong khai re nhat.",
    "Toi can mua 2 tai nghe Sony WH-1000XM5. Hay dung du lieu cong khai tren Tiki, so sanh cac lua chon hien co va cho toi biet tong tien re nhat.",
]


def build_provider():
    load_dotenv()
    provider_name = os.getenv("DEFAULT_PROVIDER", "openai").strip().lower()
    model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")

    if provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError(
                "OPENAI_API_KEY dang thieu hoac van con la gia tri mau trong file .env."
            )
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(model_name=model_name, api_key=api_key)

    if provider_name == "google":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "your_gemini_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY dang thieu hoac van con la gia tri mau trong file .env."
            )
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(model_name=model_name, api_key=api_key)

    if provider_name == "local":
        from src.core.local_provider import LocalProvider

        return LocalProvider(model_path=os.getenv("LOCAL_MODEL_PATH", ""))

    raise ValueError(f"Provider khong duoc ho tro: {provider_name}")


def build_toolset():
    load_dotenv()
    toolset = os.getenv("SHOPPING_TOOLSET", "tiki").strip().lower()
    if toolset != "tiki":
        raise ValueError("Project demo hien tai chi ho tro SHOPPING_TOOLSET=tiki.")
    return build_tiki_tools(), TIKI_TEST_CASES, "Tiki cong khai"


def aggregate_run_metrics(start_index: int) -> Dict[str, Any]:
    metrics = tracker.metrics_since(start_index)
    summary = tracker.summarize_metrics(metrics)
    summary["items"] = metrics
    return summary


def compare_versions(user_input: str) -> Dict[str, Any]:
    provider = build_provider()
    tools, _, toolset_name = build_toolset()

    chatbot = BaselineChatbot(provider)
    chatbot_start = len(tracker.session_metrics)
    chatbot_answer = chatbot.run(user_input)
    chatbot_metrics = aggregate_run_metrics(chatbot_start)

    react_v1 = ReActAgent(provider, tools, max_steps=5)
    react_v1_start = len(tracker.session_metrics)
    react_v1_answer = react_v1.run(user_input)
    react_v1_metrics = aggregate_run_metrics(react_v1_start)

    langgraph_v2 = LangGraphShoppingAgent(provider, tools, max_steps=6)
    langgraph_v2_start = len(tracker.session_metrics)
    langgraph_v2_answer = langgraph_v2.run(user_input)
    langgraph_v2_metrics = aggregate_run_metrics(langgraph_v2_start)

    return {
        "question": user_input,
        "provider": provider.model_name,
        "toolset": toolset_name,
        "chatbot": {
            "answer": chatbot_answer,
            "metrics": chatbot_metrics,
            "details": chatbot.last_run_details,
        },
        "react_v1": {
            "answer": react_v1_answer,
            "metrics": react_v1_metrics,
            "details": react_v1.last_run_details,
        },
        "langgraph_v2": {
            "answer": langgraph_v2_answer,
            "metrics": langgraph_v2_metrics,
            "details": langgraph_v2.last_run_details,
        },
    }
