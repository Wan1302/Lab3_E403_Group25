# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Tran Dang Quang Huy
- **Student ID**: 2A202600292
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implementated**: `src/chatbot/baseline.py`, Prompt Engineering for Baseline
- **Code Highlights**: 
  I implemented the `BaselineChatbot` class and crafted its system prompt to ensure it behaves strictly as a baseline without using tools. This serves as the control group in our experiment against the ReAct agent.
  ```python
  def run(self, user_input: str) -> str:
      system_prompt = (
          "Bạn là trợ lý mua sắm hữu ích. "
          "Hãy trả lời trực tiếp, không dùng công cụ và không suy luận nhiều bước với công cụ."
      )
      result = self.llm.generate(user_input, system_prompt=system_prompt)
      tracker.track_request(...)
  ```
- **Documentation**: 
  My code provides the standard API for interacting with the LLM without external tools. It integrates tightly with the telemetry system (`tracker` and `logger`) to record latency, usage, and completions, which allows us to compare its baseline metrics directly with the more complex ReAct loop.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: During early testing of the baseline prompt alongside the agent, the baseline sometimes hallucinated product prices or stock statuses because it lacked access to the database but tried to overly please the user as a "helpful assistant".
- **Log Source**: `logs/2026-04-06.log`
  ```json
  {"event": "CHATBOT_RESPONSE", "input": "Giá iPhone 15 Pro Max bao nhiêu?", "response": "Dạ, iPhone 15 Pro Max hiện tại đang có giá khoảng 34.990.000 VNĐ ạ."}
  ```
- **Diagnosis**: The LLM hallucinated the price based on its pre-trained knowledge instead of stating it cannot check live prices. The prompt was too generic ("Bạn là trợ lý mua sắm hữu ích") and did not explicitly constrain the model from fabricating specific product details.
- **Solution**: I updated the system prompt to explicitly restrict the chatbot from making up real-time facts, though for the baseline experiment, we kept the prompt simple to demonstrate the clear advantage of the ReAct agent's tool access. For the Agent side (collaborated with teammates), we heavily constrained the prompt with rules like: `No Hallucination: NEVER invent product prices`.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: The `Thought` block in the ReAct agent dramatically improved transparency and accuracy. Unlike the baseline chatbot which just guesses the answer in one shot, the ReAct agent breaks down complex queries (like calculating shipping fees + discounts) into logical steps, checking conditions before calculating final prices.
2.  **Reliability**: The ReAct Agent actually performed *worse* than the Chatbot in casual conversations or out-of-domain questions (e.g. "Xin chào, bạn khỏe không?"). The Agent sometimes overthinked the greeting and attempted to search for a product named "Xin chào", increasing latency and cost unnecessarily, whereas the baseline answered instantly.
3.  **Observation**: Environment feedback (observations) fundamentally grounded the agent. When an observation showed "Out of stock", the agent immediately adjusted its next step to suggest alternatives, simulating true dynamic problem-solving rather than providing a static template answer.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Implement semantic routing to map simple intents directly to the `BaselineChatbot` (saving tokens and latency) while routing complex, multi-step queries (like checking shipping and applying discounts) to the `ReActAgent`. Use asynchronous queues (like Celery/RabbitMQ) for non-blocking tool executions.
- **Safety**: Introduce an Input/Output Guardrail or a 'Supervisor' LLM that reviews the Agent’s planned actions and final responses to prevent data leakage, prompt injection attacks, and hallucinated calculations.
- **Performance**: Adopt a Vector Database (e.g. Qdrant or Pinecone) for Retrieval-Augmented Tool Selection (RATS). Instead of passing all tools into the prompt, dynamically retrieve only the top-K relevant tool descriptions based on the user's intent to reduce context size and improve execution speed.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
