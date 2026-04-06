# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ho Dac Toan
- **Student ID**: 2A202600057
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

- **Modules Implemented**:
  - `app.py`: Flask web server + API `POST /api/compare` và trang `GET /`.
  - `templates/index.html`: UI dashboard so sánh 3 phiên bản (A/B/C), kèm “example prompts” render từ `TIKI_TEST_CASES`.
  - `static/styles.css`: UI/UX (grid 3 cột), metric cards, responsive breakpoints.
  - `static/app.js`: logic frontend (fetch API, render kết quả/metrics, xử lý lỗi).

- **Code Highlights (đối chiếu theo source)**:
  - **Orchestrate luồng so sánh 3 phiên bản**: Frontend gọi `POST /api/compare`, backend gọi `compare_versions()` (trong `src/runtime.py`) để chạy lần lượt `BaselineChatbot`, `ReActAgent` và `LangGraphShoppingAgent`, trả về một JSON thống nhất gồm `answer`, `metrics`, `details` cho từng phiên bản.
  - **UX khi chạy so sánh (`static/app.js`)**: `runComparison()` disable nút chạy, hiển thị status “Đang gọi mô hình…”, bắt lỗi trả về từ backend và luôn restore UI ở `finally` để tránh “kẹt trạng thái loading”.
  - **Render metrics rõ ràng, dễ so sánh**: `formatNumber()` + `formatLatency()` chuẩn hoá cách hiển thị tokens và độ trễ; đồng thời hiển thị “delta tokens”/“delta latency” giữa baseline vs v1 và v1 vs v2.
  - **Defensive rendering**: `buildAgentDetails()` dùng fallback `(data.details.tool_calls || [])` và `(data.details.history || [])` để đảm bảo luôn render được trong các trường hợp payload thiếu/khác cấu trúc.
  - **Routing + validate input (`app.py`)**: Validate `question` rỗng trả về HTTP 400 (message tiếng Việt), và bọc `compare_versions()` trong `try/except` để trả về JSON error với HTTP 500 khi phát sinh exception.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: UI bị crash khi render phần “chi tiết agent”, làm trang bị kẹt ở trạng thái “Đang gọi mô hình…”, không cập nhật kết quả.
- **Error Trace (Browser Console)**: `TypeError: Cannot read properties of undefined (reading 'map') at buildAgentDetails`
- **Diagnosis (đối chiếu API contract)**:
  - Trong payload, `chatbot.details` và `agent.details` có cấu trúc khác nhau. Agent mới có `tool_calls`/`history`, còn baseline thì không.
  - Ở phiên bản `app.js` ban đầu, code gọi trực tiếp `.map()` trên `data.details.tool_calls` (khi field này `undefined`) nên gây crash.
- **Solution**: Sửa `buildAgentDetails()` theo hướng defensive:
  - Fallback mảng rỗng: `(data.details.tool_calls || [])` và `(data.details.history || [])`.
  - Khi không có dữ liệu, hiển thị “Không có” thay vì lỗi runtime.

  *Đoạn code đã áp dụng (static/app.js):*
  ```js
  const toolCalls = (data.details.tool_calls || [])
    .map((tool, index) => `${index + 1}. ${tool.tool_name}(${tool.args})\n   => ${tool.observation}`)
    .join("\n");
  ```

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning (khả năng suy luận)**: Baseline chatbot chỉ gọi LLM 1 lần và trả lời trực tiếp, nên nhanh nhưng dễ “đoán”. ReAct v1 buộc mô hình đi theo chuỗi `Suy nghĩ → Hành động → Quan sát → ... → Câu trả lời cuối`, giúp chia bài toán mua sắm (tìm giá, so sánh người bán, tính tổng tiền theo số lượng) thành các bước kiểm chứng.
2. **Trade-off (độ tin cậy vs chi phí)**: ReAct/LangGraph grounded hơn vì có thể gọi tool Tiki, nhưng đổi lại tổng tokens và độ trễ tăng do phải chạy nhiều vòng (nhiều lần gọi LLM + tool). Với câu hỏi đơn giản, baseline có thể “đủ dùng” và tiết kiệm hơn.
3. **Observability (tính quan sát được)**: Telemetry (`src/telemetry/logger.py`, `src/telemetry/metrics.py`) giúp nhìn rõ số vòng lặp, số lần gọi tool, latency/tokens theo từng request. Khi agent bị parser error hoặc chạm `max_steps`, log và phần “dấu vết suy luận” giúp truy nguyên nhanh nguyên nhân.
4. **Kiến trúc v2 (LangGraph)**: LangGraph v2 chuyển loop sang state graph (node `plan`/`tool`, state có `pending_tool`, `pending_args`, `step_count`), nên dễ mở rộng rule routing và theo dõi trạng thái hơn ReAct v1 dạng while-loop.

---

## IV. Future Improvements (5 Points)

- **Scalability (Streaming UI/UX)**: Hiện tại frontend phải đợi cả 3 phiên bản chạy xong mới render. Có thể nâng cấp sang SSE/WebSocket để stream kết quả từng phiên bản (hoặc từng token) để giảm thời gian chờ cảm nhận.
- **Performance (Caching + reuse tool results)**: Cache kết quả search Tiki theo `query` (TTL ngắn) để giảm số lần gọi HTTP và giảm biến động latency khi demo nhiều lần.
- **Robustness (Structured output)**: Thay vì regex parser cho `Hành động: tool(args)`, có thể chuyển sang structured output / function calling để giảm lỗi parser và giảm “prompt brittleness”.
- **Data contract clarity**: Chuẩn hoá lại field `provider`/`model` trong JSON response (hiện đang có chỗ dùng như “model mặc định”), giúp dashboard hiển thị đúng nghĩa và dễ debug hơn.
- **I18N/Encoding hygiene**: Chuẩn hoá encoding UTF-8 cho toàn repo (đặc biệt các system prompt tiếng Việt ở backend) để tránh lỗi hiển thị và tránh prompt bị “méo chữ” khi gửi vào LLM.
