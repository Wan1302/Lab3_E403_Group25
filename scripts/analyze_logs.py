import argparse
import json
from pathlib import Path
from statistics import median


def load_events(log_path: Path):
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def percentile_99(values):
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.99) - 1))
    return ordered[index]


def summarize(events):
    llm_metrics = [event["data"] for event in events if event.get("event") == "LLM_METRIC"]
    react_tool_execs = [event["data"] for event in events if event.get("event") == "TOOL_EXECUTION"]
    langgraph_tool_execs = [
        event["data"] for event in events if event.get("event") == "LANGGRAPH_TOOL_EXECUTION"
    ]
    react_parser_errors = [
        event["data"] for event in events if event.get("event") == "AGENT_PARSER_ERROR"
    ]
    langgraph_parser_errors = [
        event["data"] for event in events if event.get("event") == "LANGGRAPH_AGENT_PARSER_ERROR"
    ]
    react_timeouts = [event["data"] for event in events if event.get("event") == "AGENT_TIMEOUT"]
    react_final_answers = [
        event["data"] for event in events if event.get("event") == "AGENT_FINAL_ANSWER"
    ]
    langgraph_runs = [
        event["data"] for event in events if event.get("event") == "LANGGRAPH_AGENT_END"
    ]
    chatbot_responses = [event["data"] for event in events if event.get("event") == "CHATBOT_RESPONSE"]
    react_steps = [event["data"]["step"] for event in events if event.get("event") == "AGENT_STEP"]
    langgraph_steps = [
        event["data"]["step"] for event in events if event.get("event") == "LANGGRAPH_AGENT_STEP"
    ]

    total_prompt_tokens = sum(item.get("prompt_tokens", 0) for item in llm_metrics)
    total_completion_tokens = sum(item.get("completion_tokens", 0) for item in llm_metrics)
    total_tokens = sum(item.get("total_tokens", 0) for item in llm_metrics)
    latencies = [item.get("latency_ms", 0) for item in llm_metrics]
    costs = [item.get("cost_estimate", 0.0) for item in llm_metrics]
    langgraph_timeouts = [
        item
        for item in langgraph_runs
        if "so buoc suy luan toi da" in str(item.get("final_answer", "")).lower()
    ]

    return {
        "events": len(events),
        "llm_requests": len(llm_metrics),
        "chatbot_responses": len(chatbot_responses),
        "react_final_answers": len(react_final_answers),
        "langgraph_final_answers": len(langgraph_runs),
        "total_agent_final_answers": len(react_final_answers) + len(langgraph_runs),
        "react_tool_executions": len(react_tool_execs),
        "langgraph_tool_executions": len(langgraph_tool_execs),
        "total_tool_executions": len(react_tool_execs) + len(langgraph_tool_execs),
        "react_parser_errors": len(react_parser_errors),
        "langgraph_parser_errors": len(langgraph_parser_errors),
        "total_parser_errors": len(react_parser_errors) + len(langgraph_parser_errors),
        "react_timeouts": len(react_timeouts),
        "langgraph_timeouts": len(langgraph_timeouts),
        "total_timeouts": len(react_timeouts) + len(langgraph_timeouts),
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "avg_tokens_per_request": round(total_tokens / len(llm_metrics), 2) if llm_metrics else 0,
        "p50_latency_ms": round(median(latencies), 2) if latencies else 0,
        "p99_latency_ms": percentile_99(latencies),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "max_react_step": max(react_steps) if react_steps else 0,
        "max_langgraph_step": max(langgraph_steps) if langgraph_steps else 0,
        "total_cost_estimate": round(sum(costs), 6),
    }


def to_markdown(summary):
    return "\n".join(
        [
            "# Metrics Summary",
            "",
            f"- Total events: {summary['events']}",
            f"- LLM requests: {summary['llm_requests']}",
            f"- Chatbot responses: {summary['chatbot_responses']}",
            f"- ReAct v1 final answers: {summary['react_final_answers']}",
            f"- LangGraph v2 final answers: {summary['langgraph_final_answers']}",
            f"- Total agent final answers: {summary['total_agent_final_answers']}",
            f"- ReAct v1 tool executions: {summary['react_tool_executions']}",
            f"- LangGraph v2 tool executions: {summary['langgraph_tool_executions']}",
            f"- Total tool executions: {summary['total_tool_executions']}",
            f"- ReAct v1 parser errors: {summary['react_parser_errors']}",
            f"- LangGraph v2 parser errors: {summary['langgraph_parser_errors']}",
            f"- Total parser errors: {summary['total_parser_errors']}",
            f"- ReAct v1 timeouts: {summary['react_timeouts']}",
            f"- LangGraph v2 inferred timeouts: {summary['langgraph_timeouts']}",
            f"- Total timeouts: {summary['total_timeouts']}",
            f"- Prompt tokens: {summary['prompt_tokens']}",
            f"- Completion tokens: {summary['completion_tokens']}",
            f"- Total tokens: {summary['total_tokens']}",
            f"- Average tokens per request: {summary['avg_tokens_per_request']}",
            f"- Average latency: {summary['avg_latency_ms']} ms",
            f"- P50 latency: {summary['p50_latency_ms']} ms",
            f"- P99 latency: {summary['p99_latency_ms']} ms",
            f"- Max ReAct v1 step: {summary['max_react_step']}",
            f"- Max LangGraph v2 step: {summary['max_langgraph_step']}",
            f"- Total cost estimate: ${summary['total_cost_estimate']}",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="Path to JSON lines log file")
    parser.add_argument("--markdown", help="Optional markdown output path")
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        raise FileNotFoundError(
            f"Khong tim thay file log: {log_path}. Hay chay ung dung truoc de tao log."
        )

    events = load_events(log_path)
    summary = summarize(events)

    print(json.dumps(summary, indent=2))

    if args.markdown:
        output_path = Path(args.markdown)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(to_markdown(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
