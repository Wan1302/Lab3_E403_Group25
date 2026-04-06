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
import json
import os
import re
import sys
from textwrap import dedent
from typing import Any, Dict

from dotenv import load_dotenv


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider
from src.telemetry.logger import logger


class EcommerceJsonChatbot:
    """
    E-commerce chatbot configured to work with chat-style providers such as OpenAI.
    The model is instructed to return a strict JSON object for every request.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def get_system_prompt(self) -> str:
        return dedent(
            """
            You are a smart Vietnamese e-commerce assistant running on OpenAI chat models.

            Your job is to help users with shopping-related requests and ALWAYS return exactly one valid JSON object.
            Do not output markdown.
            Do not wrap the JSON in code fences.
            Do not add any text before or after the JSON.


            ## TASKS
            Follow these tasks internally:
            Task 1. Read the user request carefully and identify the shopping goal.
            Task 2. Extract useful shopping details when available, such as product name, category, budget, quantity, brand, color, size, use case, and urgency.
            Task 3. Classify the request into one of these labels:
            - product_search
            - recommendation
            - comparison
            - price_check
            - shipping_info
            - return_policy
            - order_support
            - other
            Task 4. Write a helpful answer in Vietnamese unless the user explicitly requests another language.
            Task 5. If the user asks for product suggestions, recommend options based on the stated needs and explain the trade-offs briefly.
            Task 6. If the request is ambiguous or missing critical shopping information, set needs_follow_up=true and ask exactly one short follow-up question.
            Task 7. If the request is answerable, set needs_follow_up=false and provide a direct answer.
            Task 8. Estimate confidence from 0.0 to 1.0.
            Task 9. Return the final result using the JSON schema below.

            Rules:
            - Keep the answer concise, clear, practical, and sales-assistant-like.
            - Prioritize helping the user choose, compare, or clarify products and shopping policies.
            - If exact product inventory, price, shipping time, or policy details are not provided in the user message or system context, do not invent them.
            - If you are uncertain, say so briefly in the answer.
            - Escape double quotes inside JSON strings properly.
            - The output must be parseable by json.loads().
            - If the user asks something outside e-commerce, still answer briefly and set intent to other.

            ## OUTPUT FORMAT
            Output JSON schema:
            {
              "intent": "product_search | recommendation | comparison | price_check | shipping_info | return_policy | order_support | other",
              "language": "vi",
              "answer": "final answer for the user",
              "needs_follow_up": false,
              "follow_up_question": null,
              "confidence": 0.92
            }


            ## EXAMPLES
            Example 1
            User: Toi can tai nghe bluetooth duoi 1 trieu de hoc online.
            Output:
            {
              "intent": "recommendation",
              "language": "vi",
              "answer": "Ban nen uu tien tai nghe co microphone ro, deo em tai va pin tot. Trong tam gia duoi 1 trieu, hay tim cac mau tai nghe bluetooth over-ear hoac in-ear co chong on vua phai va do tre thap de hoc online on dinh.",
              "needs_follow_up": false,
              "follow_up_question": null,
              "confidence": 0.93
            }

            Example 2
            User: So sanh chuot Logitech M331 va M185.
            Output:
            {
              "intent": "comparison",
              "language": "vi",
              "answer": "Logitech M331 thuong em hon va tap trung vao su yen tinh khi su dung, phu hop cho van phong hoac hoc tap. M185 don gian hon, gon nhe va phu hop neu ban can chuot co ban voi chi phi tiet kiem.",
              "needs_follow_up": false,
              "follow_up_question": null,
              "confidence": 0.9
            }

            Example 3
            User: Phi ship don hang nay bao nhieu?
            Output:
            {
              "intent": "shipping_info",
              "language": "vi",
              "answer": "Minh chua du thong tin de bao phi van chuyen.",
              "needs_follow_up": true,
              "follow_up_question": "Ban vui long cho biet dia chi giao hang hoac khu vuc nhan hang?",
              "confidence": 0.66
            }
            """
        ).strip()

    def chat(self, user_input: str) -> Dict[str, Any]:
        logger.log_event(
            "CHATBOT_START",
            {
                "input": user_input,
                "model": self.llm.model_name,
                "mode": "json_chatbot",
            },
        )

        raw_result = self.llm.generate(
            prompt=user_input,
            system_prompt=self.get_system_prompt(),
        )
        parsed_content = self._parse_json_response(raw_result["content"])

        result = {
            "content": parsed_content,
            "raw_content": raw_result["content"],
            "usage": raw_result["usage"],
            "latency_ms": raw_result["latency_ms"],
            "provider": raw_result["provider"],
        }

        logger.log_event(
            "CHATBOT_END",
            {
                "intent": parsed_content.get("intent"),
                "needs_follow_up": parsed_content.get("needs_follow_up"),
                "latency_ms": raw_result["latency_ms"],
            },
        )
        return result

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        cleaned = content.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.log_event(
            "CHATBOT_PARSE_FALLBACK",
            {
                "raw_content": cleaned,
            },
        )
        return {
            "intent": "other",
            "language": "vi",
            "answer": cleaned,
            "needs_follow_up": False,
            "follow_up_question": None,
            "confidence": 0.3,
        }


def create_provider() -> LLMProvider:
    return OpenAIProvider(
        model_name=os.getenv("DEFAULT_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def main() -> None:
    load_dotenv()
    chatbot = EcommerceJsonChatbot(create_provider())

    print("OpenAI E-commerce JSON Chatbot. Type 'exit' to quit.")
    while True:
        user_input = input("\nUser: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        result = chatbot.chat(user_input)
        print("\nAssistant JSON:")
        print(json.dumps(result["content"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
