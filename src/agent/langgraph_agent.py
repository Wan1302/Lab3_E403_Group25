from typing import Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class LangGraphState(TypedDict, total=False):
    user_input: str
    history: List[str]
    llm_calls: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    final_answer: str
    pending_tool: str
    pending_args: str
    done: bool
    parse_error: bool
    step_count: int


class LangGraphShoppingAgent:
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 6):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.last_run_details: Dict[str, Any] = {}
        self._react_helper = ReActAgent(llm, tools, max_steps=max_steps)
        self._tool_map = {tool["name"]: tool for tool in tools}
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(LangGraphState)
        graph.add_node("plan", self._plan_node)
        graph.add_node("tool", self._tool_node)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges(
            "plan",
            self._route_after_plan,
            {
                "tool": "tool",
                "end": END,
            },
        )
        graph.add_edge("tool", "plan")
        return graph.compile()

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [f"- {tool['name']}: {tool['description']}" for tool in self.tools]
        )
        return f"""
Ban la agent mua sam v2 duoc dieu phoi bang LangGraph.
Nhiem vu cua ban la tim phuong an mua hang hop le re nhat tu du lieu cong khai.

Cong cu hien co:
{tool_descriptions}

Nguyen tac:
- Nghi tung buoc.
- Neu can du lieu gia, tong tien, so sanh lua chon hoac chon nguoi ban re nhat, hay goi cong cu.
- Khong tu suy dien ket qua cong cu.
- Chi ket thuc khi da co du observation de tra loi.
- Neu khong phan tich duoc hanh dong, hay ket thuc bang Cau tra loi cuoi.

Chi dung mot trong hai mau:
Suy nghi: ...
Hanh dong: ten_cong_cu(tham_so_1, tham_so_2)

hoac:

Cau tra loi cuoi: ...
        """.strip()

    def run(self, user_input: str) -> str:
        logger.log_event(
            "LANGGRAPH_AGENT_START",
            {"input": user_input, "model": self.llm.model_name},
        )

        initial_state: LangGraphState = {
            "user_input": user_input,
            "history": [f"Nguoi dung: {user_input}"],
            "llm_calls": [],
            "tool_calls": [],
            "done": False,
            "parse_error": False,
            "step_count": 0,
        }

        final_state = self.graph.invoke(initial_state)
        final_answer = final_state.get(
            "final_answer",
            "Khong the tao cau tra loi cuoi tu LangGraph agent.",
        )

        total_prompt_tokens = sum(
            call["usage"].get("prompt_tokens", 0)
            for call in final_state.get("llm_calls", [])
        )
        total_completion_tokens = sum(
            call["usage"].get("completion_tokens", 0)
            for call in final_state.get("llm_calls", [])
        )
        total_tokens = sum(
            call["usage"].get("total_tokens", 0)
            for call in final_state.get("llm_calls", [])
        )
        total_latency_ms = sum(
            call.get("latency_ms", 0) for call in final_state.get("llm_calls", [])
        )

        self.last_run_details = {
            "model": self.llm.model_name,
            "steps": final_state.get("step_count", 0),
            "tool_calls": final_state.get("tool_calls", []),
            "history": final_state.get("history", []),
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
            },
            "latency_ms": total_latency_ms,
            "response": final_answer,
            "llm_calls": final_state.get("llm_calls", []),
            "done": final_state.get("done", False),
            "parse_error": final_state.get("parse_error", False),
        }

        logger.log_event(
            "LANGGRAPH_AGENT_END",
            {
                "steps": final_state.get("step_count", 0),
                "final_answer": final_answer,
                "parse_error": final_state.get("parse_error", False),
            },
        )
        return final_answer

    def _plan_node(self, state: LangGraphState) -> Dict[str, Any]:
        step_count = state.get("step_count", 0)
        if state.get("done"):
            return {}

        if step_count >= self.max_steps:
            timeout_answer = (
                "LangGraph agent da cham toi so buoc suy luan toi da truoc khi hoan tat."
            )
            return {
                "done": True,
                "final_answer": timeout_answer,
                "history": state.get("history", []) + [f"Cau tra loi cuoi: {timeout_answer}"],
            }

        prompt = self._build_prompt(
            state["user_input"], state.get("history", []))
        result = self.llm.generate(
            prompt, system_prompt=self.get_system_prompt())
        tracker.track_request(
            provider=result.get("provider", "unknown"),
            model=self.llm.model_name,
            usage=result.get("usage", {}),
            latency_ms=result.get("latency_ms", 0),
        )

        content = (result.get("content") or "").strip()
        logger.log_event(
            "LANGGRAPH_AGENT_STEP",
            {"step": step_count + 1, "response": content},
        )

        llm_call = {
            "provider": result.get("provider", "unknown"),
            "usage": result.get("usage", {}),
            "latency_ms": result.get("latency_ms", 0),
            "content": content,
        }
        next_history = state.get("history", []) + [content]

        final_answer = self._react_helper._extract_final_answer(content)
        if final_answer:
            return {
                "llm_calls": state.get("llm_calls", []) + [llm_call],
                "history": next_history,
                "step_count": step_count + 1,
                "final_answer": final_answer,
                "done": True,
            }

        action = self._react_helper._extract_action(content)
        if not action:
            parse_error_answer = (
                "LangGraph agent khong the phan tich duoc hanh dong tiep theo tu phan hoi cua mo hinh."
            )
            logger.log_event(
                "LANGGRAPH_AGENT_PARSER_ERROR",
                {"step": step_count + 1, "response": content},
            )
            return {
                "llm_calls": state.get("llm_calls", []) + [llm_call],
                "history": next_history + [f"Cau tra loi cuoi: {parse_error_answer}"],
                "step_count": step_count + 1,
                "final_answer": parse_error_answer,
                "done": True,
                "parse_error": True,
            }

        tool_name, raw_args = action
        return {
            "llm_calls": state.get("llm_calls", []) + [llm_call],
            "history": next_history,
            "step_count": step_count + 1,
            "pending_tool": tool_name,
            "pending_args": raw_args,
            "done": False,
        }

    def _tool_node(self, state: LangGraphState) -> Dict[str, Any]:
        tool_name = state.get("pending_tool", "")
        raw_args = state.get("pending_args", "")
        observation = self._execute_tool(tool_name, raw_args)
        tool_call = {
            "step": state.get("step_count", 0),
            "tool_name": tool_name,
            "args": raw_args,
            "observation": observation,
        }
        logger.log_event("LANGGRAPH_TOOL_EXECUTION", tool_call)
        return {
            "tool_calls": state.get("tool_calls", []) + [tool_call],
            "history": state.get("history", []) + [f"Quan sat: {observation}"],
            "pending_tool": "",
            "pending_args": "",
        }

    def _route_after_plan(self, state: LangGraphState) -> Literal["tool", "end"]:
        if state.get("done"):
            return "end"
        if state.get("pending_tool"):
            return "tool"
        return "end"

    def _build_prompt(self, user_input: str, history: List[str]) -> str:
        scratchpad = "\n".join(history)
        return (
            f"Yeu cau cua nguoi dung: {user_input}\n\n"
            f"Trang thai hien tai:\n{scratchpad}\n\n"
            "Neu da du thong tin thi ket thuc bang Cau tra loi cuoi. "
            "Neu chua du, hay dua ra Hanh dong tiep theo."
        )

    def _execute_tool(self, tool_name: str, raw_args: str) -> str:
        tool = self._tool_map.get(tool_name)
        if not tool:
            return f"Khong tim thay cong cu {tool_name}."
        try:
            parsed_args = self._react_helper._split_args(raw_args)
            return str(tool["func"](*parsed_args))
        except TypeError as exc:
            return f"Tham so khong hop le cho {tool_name}: {exc}"
        except Exception as exc:
            return f"Cong cu {tool_name} bi loi: {exc}"
