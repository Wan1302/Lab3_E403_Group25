import re
from typing import List, Dict, Any, Optional, Tuple
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

class ReActAgent:
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []
        self.last_run_details = {}

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['description']}" for t in self.tools]
        )
        return f"""
Bạn là trợ lý tối ưu mua sắm theo mô hình ReAct.
Nhiệm vụ của bạn là tìm phương án mua hàng hợp lệ có tổng chi phí rẻ nhất cho người dùng.

Các công cụ có thể dùng:
{tool_descriptions}

Quy tắc:
- Suy nghĩ từng bước.
- Dùng công cụ khi cần kiểm tra giá sản phẩm, khuyến mãi công khai, chi phí giao hàng hoặc so sánh nhiều lựa chọn.
- Tuyệt đối không tự bịa kết quả công cụ.
- Nếu có nhiều sản phẩm, người bán hoặc mức giảm giá, hãy so sánh và chọn phương án hợp lệ rẻ nhất.
- Nếu sản phẩm hoặc điểm đến không hợp lệ, hãy nói rõ trong câu trả lời cuối cùng.
- Tham số truyền vào công cụ phải đơn giản, ngăn cách bằng dấu phẩy, không dùng JSON.

Chỉ dùng đúng định dạng này:
Suy nghĩ: lập luận ngắn
Hành động: ten_cong_cu(tham_so_1, tham_so_2, ...)
Quan sát: kết quả từ công cụ
... lặp lại nếu cần ...
Câu trả lời cuối: câu trả lời hoàn chỉnh cho người dùng
        """

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        self.history = [f"Người dùng: {user_input}"]
        current_prompt = self._build_prompt(user_input)
        steps = 0
        final_answer = None
        llm_calls = []
        tool_calls = []

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            llm_calls.append(
                {
                    "provider": result.get("provider", "unknown"),
                    "usage": result.get("usage", {}),
                    "latency_ms": result.get("latency_ms", 0),
                    "content": (result.get("content") or "").strip(),
                }
            )
            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=result.get("latency_ms", 0),
            )

            content = (result.get("content") or "").strip()
            logger.log_event(
                "AGENT_STEP",
                {"step": steps + 1, "response": content},
            )

            self.history.append(content)

            final_answer = self._extract_final_answer(content)
            if final_answer:
                logger.log_event(
                    "AGENT_FINAL_ANSWER",
                    {"step": steps + 1, "final_answer": final_answer},
                )
                break

            action = self._extract_action(content)
            if not action:
                logger.log_event(
                    "AGENT_PARSER_ERROR",
                    {"step": steps + 1, "response": content},
                )
                final_answer = (
                    "Tôi không thể phân tích được hành động tiếp theo từ phản hồi của mô hình."
                )
                break

            tool_name, raw_args = action
            observation = self._execute_tool(tool_name, raw_args)
            self.history.append(f"Quan sát: {observation}")
            tool_calls.append(
                {
                    "step": steps + 1,
                    "tool_name": tool_name,
                    "args": raw_args,
                    "observation": observation,
                }
            )
            logger.log_event(
                "TOOL_EXECUTION",
                {
                    "step": steps + 1,
                    "tool_name": tool_name,
                    "args": raw_args,
                    "observation": observation,
                },
            )

            current_prompt = self._build_prompt(user_input)
            steps += 1

        if final_answer is None:
            final_answer = (
                "Tôi đã chạm tới số bước suy luận tối đa trước khi hoàn tất."
            )
            logger.log_event(
                "AGENT_TIMEOUT",
                {"steps": steps, "max_steps": self.max_steps},
            )

        total_prompt_tokens = sum(
            call["usage"].get("prompt_tokens", 0) for call in llm_calls
        )
        total_completion_tokens = sum(
            call["usage"].get("completion_tokens", 0) for call in llm_calls
        )
        total_tokens = sum(
            call["usage"].get("total_tokens", 0) for call in llm_calls
        )
        total_latency_ms = sum(call.get("latency_ms", 0) for call in llm_calls)
        self.last_run_details = {
            "model": self.llm.model_name,
            "steps": len(llm_calls),
            "tool_calls": tool_calls,
            "history": self.history[:],
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
            },
            "latency_ms": total_latency_ms,
            "response": final_answer,
            "llm_calls": llm_calls,
        }
        logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_answer})
        return final_answer

    def _execute_tool(self, tool_name: str, args: str) -> str:
        for tool in self.tools:
            if tool["name"] == tool_name:
                try:
                    parsed_args = self._split_args(args)
                    return str(tool["func"](*parsed_args))
                except TypeError as exc:
                    return f"Tham số không hợp lệ cho {tool_name}: {exc}"
                except Exception as exc:
                    return f"Công cụ {tool_name} bị lỗi: {exc}"
        return f"Không tìm thấy công cụ {tool_name}."

    def _build_prompt(self, user_input: str) -> str:
        scratchpad = "\n".join(self.history)
        return (
            f"Yêu cầu của người dùng: {user_input}\n\n"
            f"Ngữ cảnh trước đó:\n{scratchpad}\n\n"
            "Hãy tiếp tục từ trạng thái mới nhất. "
            "Nếu đã đủ thông tin, hãy trả lời bằng Câu trả lời cuối."
        )

    def _extract_final_answer(self, content: str) -> Optional[str]:
        match = re.search(
            r"(?:Câu trả lời cuối|Cau tra loi cuoi|Final Answer):\s*(.+)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return None

    def _extract_action(self, content: str) -> Optional[Tuple[str, str]]:
        match = re.search(
            r"(?:Hành động|Hanh dong|Action):\s*([a-zA-Z_][\w]*)\((.*)\)",
            content,
            re.DOTALL,
        )
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None

    def _split_args(self, raw_args: str) -> List[str]:
        if not raw_args:
            return []

        parts = [part.strip() for part in raw_args.split(",")]
        cleaned = []
        for part in parts:
            if "=" in part:
                _, part = part.split("=", 1)
                part = part.strip()
            if len(part) >= 2 and part[0] == part[-1] and part[0] in {"'", '"'}:
                cleaned.append(part[1:-1])
            else:
                cleaned.append(part)
        return cleaned
