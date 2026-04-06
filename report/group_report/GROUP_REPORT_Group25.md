# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: Group25
- **Team Members**: Ho Trong Duy Quang (2A202600081), Tran Dang Quang Huy (2A202600292), Ho Tran Dinh Nguyen (2A202600080), Ho Dac Toan (2A202600057), Nguyen Duy Hieu (2A202600253), Vu Duc Kien (2A202600338)
- **Deployment Date**: 2026-04-06

---

## 1. Executive Summary

This project implements and compares three shopping assistants for Vietnamese users: a direct baseline chatbot, a regex-based ReAct agent, and a LangGraph-based shopping agent. The shared task is to answer shopping questions, especially price-checking and cheapest-option queries, using grounded Tiki public data instead of unsupported LLM guesses.

- **Success Rate**: `6/6` executable tests passed in the current environment (`tests/test_agent_workflow.py` and `tests/test_tiki_tools.py`). One additional LangGraph test is present in the repo but is currently blocked by a missing `langgraph` dependency during test collection.
- **Key Outcome**: Compared with the baseline chatbot, the agent versions add real multi-step capability: they can parse tool actions, call the Tiki tool layer, use observations to continue reasoning, and produce grounded final answers for cheapest-price and quantity-based shopping tasks.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

The project contains two agentic execution styles:

1. **Baseline chatbot**
   Returns a direct text answer from the LLM with no external tools. It is intentionally lightweight and acts as the control condition.
2. **ReActAgent (v1)**
   Uses a prompt with the pattern `Suy nghi -> Hanh dong -> Quan sat -> Cau tra loi cuoi`. The agent:
   - builds a scratchpad from prior history,
   - asks the LLM for the next step,
   - extracts either a final answer or a tool call with regex,
   - executes the tool,
   - appends the observation back into history,
   - repeats until a final answer or `max_steps` is reached.
3. **LangGraphShoppingAgent (v2)**
   Wraps the same reasoning idea in a state graph with explicit `plan` and `tool` nodes. This separates planning from tool execution more cleanly and prepares the system for more structured branching in production.

High-level loop:

```text
User Query
  -> LLM Planning Step
  -> Tool Call (if needed)
  -> Observation added to history
  -> Next Planning Step
  -> Final Answer
```

### 2.2 Tool Definitions (Inventory)

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `search_tiki_products` | `query, limit` | Retrieve relevant public Tiki listings for a product keyword. |
| `find_cheapest_tiki_product` | `query, limit` | Return the cheapest reliable Tiki result for a target product. |
| `calculate_tiki_total` | `query, quantity, limit` | Compute the cheapest public total cost for a product and quantity. |
| `compare_tiki_options` | `query, quantity, limit` | Compare multiple validated Tiki options before choosing a best seller/price. |

The Tiki layer is implemented through `TikiClient`, which requests `https://tiki.vn/search`, extracts the `__NEXT_DATA__` JSON payload, normalizes item fields, and applies a relevance filter to reduce accessory noise.

### 2.3 LLM Providers Used

- **Primary**: `gpt-4o` via `OpenAIProvider` (default in `src/runtime.py`)
- **Secondary (Backup)**: Google Gemini via `GeminiProvider`
- **Local Option**: GGUF local model via `LocalProvider` using `llama-cpp-python`

---

## 3. Telemetry & Performance Dashboard

The codebase includes a reusable telemetry layer through `PerformanceTracker` and `IndustryLogger`. Every LLM request records:

- provider
- model
- prompt tokens
- completion tokens
- total tokens
- latency in milliseconds
- a mock cost estimate

From the checked-in runtime log available in the repo (`logs/2026-04-06.log`), we can confirm the following observed baseline latencies:

- **Average Latency (observed sample)**: `2409 ms`
- **Max Latency (observed sample)**: `2662 ms`
- **Average Tokens per Task**: tracked by the code, but not available in the committed production log sample
- **Total Cost of Test Suite**: the tracker computes a mock estimate at `$0.01 / 1K tokens`, but no committed end-to-end benchmark artifact includes the final suite total

These limitations are important: the telemetry system exists and is wired into baseline, ReAct, and LangGraph execution paths, but the repository currently contains only a small log sample instead of a full exported benchmark dashboard.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study: Cheapest-Price Retrieval Returned Accessories Instead of the Target Product

- **Input**: queries in the style of `iphone 15` or `gia cua iphone 13 bao nhieu`
- **Observation**: raw Tiki marketplace results can include accessories such as phone cases, cables, or screen protectors mixed with the actual phone listing
- **Root Cause**: a naive "take the first result" or "take the cheapest result" strategy is unsafe for shopping agents because marketplace search pages are noisy by design. Without an additional ranking layer, the agent could ground itself on an irrelevant accessory price and still produce a fluent but wrong final answer.
- **Fix Implemented**:
  - normalize query and product text with `_normalize_text()`
  - compute token-overlap relevance in `_match_score()`
  - boost exact phrase containment
  - penalize accessory keywords when the user did not ask for accessories
  - reject weak matches below a score threshold in `_best_matching_products()`
- **Validation**:
  - `test_best_matching_products_prefers_query_match()` confirms that `Apple iPhone 15` outranks `Op lung danh cho iPhone 15`
  - `test_best_matching_products_returns_empty_when_match_is_weak()` confirms that the tool abstains on unrelated queries instead of fabricating confidence

This RCA shows that agent quality depends not only on prompt design, but also on retrieval hygiene. Better observations produce better reasoning.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Baseline Prompt v1 vs Prompt v2

- **Diff**: The original baseline prompt only said "answer directly and do not use tools." The revised prompt adds explicit identity, capabilities, instructions, constraints, output format, and few-shot examples for live-price and Tiki-related questions.
- **Result**: The new prompt is expected to reduce hallucinated real-time shopping facts by forcing the baseline to admit uncertainty instead of inventing prices, sellers, or promotions. This keeps the baseline faithful to its intended role as a no-tool control system.

### Experiment 2 (Bonus): Chatbot vs Agent

| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| General shopping advice | Can answer directly and quickly | Can answer, but tool usage may be unnecessary | **Chatbot** |
| Live Tiki price lookup | Cannot verify real-time data | Can call Tiki tools for grounded public results | **Agent** |
| Cheapest product selection | Likely gives a generic or uncertain answer | Can search, rank, and choose the best public option | **Agent** |
| Quantity-based total cost | Cannot reliably compute without live price input | Can retrieve price then calculate total | **Agent** |
| Out-of-domain questions (e.g. stock market) | Gives a generic answer without tool overhead | May over-reason or attempt irrelevant tool use | **Chatbot** |

The project therefore shows a clear tradeoff: the baseline is cheaper and simpler, while the agent is stronger on multi-step, data-grounded shopping tasks.

---

## 6. Production Readiness Review

- **Security**: Tool arguments are parsed from plain-text actions, so input validation should be tightened further to prevent malformed or adversarial tool calls.
- **Guardrails**: Both agents already enforce a max-step limit (`max_steps`) to cap runaway reasoning loops and token cost.
- **Scaling**: The LangGraph version is the right direction for production because it separates planning from execution and can be extended with branching, retries, and fallback logic.
- **Reliability Gaps**: The current environment cannot run `tests/test_langgraph_agent.py` because `langgraph` is not installed, so dependency locking and setup automation still need improvement.
- **Data Robustness**: The current Tiki integration scrapes public HTML and extracts `__NEXT_DATA__`; in production, this should be replaced or supplemented with a more stable API or caching layer.
- **Observability**: Telemetry exists, but the team should add a reproducible benchmark run that exports aggregated latency, token, and cost metrics for the full test suite rather than relying on ad hoc logs.

---
