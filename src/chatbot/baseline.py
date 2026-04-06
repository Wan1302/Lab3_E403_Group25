from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class BaselineChatbot:
    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.last_run_details = {}

    def run(self, user_input: str) -> str:
        system_prompt = (
            "Bạn là trợ lý mua sắm hữu ích. "
            "Hãy trả lời trực tiếp, không dùng công cụ và không suy luận nhiều bước với công cụ."
        )
        result = self.llm.generate(user_input, system_prompt=system_prompt)
        tracker.track_request(
            provider=result.get("provider", "unknown"),
            model=self.llm.model_name,
            usage=result.get("usage", {}),
            latency_ms=result.get("latency_ms", 0),
        )
        logger.log_event(
            "CHATBOT_RESPONSE",
            {"input": user_input, "response": result.get("content", "")},
        )
        self.last_run_details = {
            "provider": result.get("provider", "unknown"),
            "model": self.llm.model_name,
            "usage": result.get("usage", {}),
            "latency_ms": result.get("latency_ms", 0),
            "response": result.get("content", "").strip(),
        }
        return result.get("content", "").strip()
