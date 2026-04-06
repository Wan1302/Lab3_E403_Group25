# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ho Tran Dinh Nguyen
- **Student ID**: 2A202600080
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

- **Modules Implemented**:
  - `src/agent/langgraph_agent.py` (xây dựng tác tử mua sắm theo mô hình LangGraph)
  - `tests/test_langgraph_agent.py` (kiểm thử luồng hoạt động của LangGraph agent)
- **Code Highlights**:
  - **Thiết kế state machine bằng LangGraph (`src/agent/langgraph_agent.py`)**: Tôi cài đặt `LangGraphShoppingAgent` với `LangGraphState` để quản lý các trường trạng thái như `history`, `llm_calls`, `tool_calls`, `pending_tool`, `final_answer`, `parse_error`, và `step_count`. Đồ thị được tổ chức theo vòng lặp `plan -> tool -> plan`, giúp agent suy luận nhiều bước nhưng vẫn có điểm dừng rõ ràng.
  - **Điều phối node và routing có kiểm soát (`src/agent/langgraph_agent.py`)**: Tôi viết các node `_plan_node()` và `_tool_node()`, cùng hàm `_route_after_plan()` để quyết định khi nào agent cần gọi tool, khi nào kết thúc. Cách làm này giúp tách biệt rõ phần suy luận của LLM với phần thực thi công cụ.
  - **Telemetry và tổng hợp kết quả chạy (`src/agent/langgraph_agent.py`)**: Trong hàm `run()`, tôi thu thập log theo từng bước (`LANGGRAPH_AGENT_START`, `LANGGRAPH_AGENT_STEP`, `LANGGRAPH_TOOL_EXECUTION`, `LANGGRAPH_AGENT_END`) và cộng dồn `prompt_tokens`, `completion_tokens`, `total_tokens`, `latency_ms` vào `last_run_details`. Điều này hỗ trợ so sánh trực tiếp LangGraph v2 với các phiên bản khác.
  - **Tái sử dụng parser của ReAct để đảm bảo nhất quán (`src/agent/langgraph_agent.py`)**: Tôi sử dụng `ReActAgent` như một helper để tái dùng các hàm `_extract_action()`, `_extract_final_answer()`, và `_split_args()`. Nhờ đó, định dạng đầu ra của LangGraph agent vẫn thống nhất với agent ReAct v1.
  - **Kiểm thử đơn vị với mock provider (`tests/test_langgraph_agent.py`)**: Tôi xây dựng `MockProvider` và `build_mock_tools()` để mô phỏng một phiên làm việc gồm 2 bước: bước đầu gọi tool, bước sau trả về đáp án cuối. Test xác nhận agent thật sự gọi tool, hoàn tất đúng sau 2 bước, và lưu lại `tool_calls` trong `last_run_details`.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Trong giai đoạn kiểm thử ban đầu, LangGraph agent đôi khi dừng bất thường vì mô hình trả lời tự do theo ngôn ngữ tự nhiên, không đúng định dạng `Hanh dong: ten_cong_cu(...)` hoặc `Cau tra loi cuoi: ...`. Khi đó agent không thể xác định bước tiếp theo để route trong graph.
- **Log Source/Error Trace**:
  Hệ thống telemetry ghi nhận sự kiện `LANGGRAPH_AGENT_PARSER_ERROR` tại `_plan_node()` khi phản hồi của mô hình không parse được bằng `_extract_action()`.
- **Diagnosis**: Kiến trúc LangGraph trong bài lab phụ thuộc vào việc tách rõ 2 trường hợp: hoặc mô hình sinh ra hành động để gọi tool, hoặc mô hình sinh ra câu trả lời cuối. Nếu phản hồi nằm ngoài hai mẫu này, node `plan` sẽ không thể sinh `pending_tool` và workflow trở nên mong manh. Đây là khác biệt quan trọng giữa chatbot thông thường và agent có điều phối trạng thái: chỉ cần đầu ra lệch format là toàn bộ luồng suy luận có thể thất bại.
- **Solution**: Tôi bổ sung nhánh xử lý parser error trong `_plan_node()` để agent:
  1. Ghi log lỗi bằng `LANGGRAPH_AGENT_PARSER_ERROR`
  2. Gắn cờ `parse_error = True`
  3. Sinh một `final_answer` dự phòng
  4. Kết thúc an toàn thay vì lặp vô hạn hoặc crash

  Ngoài ra, tôi siết lại `system prompt` trong `get_system_prompt()` để mô hình chỉ dùng đúng hai mẫu đầu ra đã định nghĩa, giúp giảm đáng kể lỗi parse trong thực nghiệm.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning (Khả năng suy luận)**: Khi làm với `LangGraphShoppingAgent`, tôi thấy điểm mạnh của agent không chỉ nằm ở prompt kiểu ReAct mà còn ở cấu trúc điều phối bên ngoài mô hình. Luồng `plan -> tool -> plan` khiến quá trình suy luận trở nên minh bạch hơn chatbot baseline, vì mỗi bước đều có trạng thái, quan sát, và điều kiện chuyển tiếp rõ ràng.
2. **Reliability (Độ tin cậy và đánh đổi)**: LangGraph agent đáng tin cậy hơn chatbot trong các bài toán cần dữ liệu thật vì nó buộc phải đi qua bước gọi tool. Tuy nhiên, đổi lại là chi phí triển khai cao hơn: phải quản lý state, parse output, giới hạn số bước, và xử lý nhiều tình huống lỗi hơn chatbot một lượt.
3. **Observation (Quan sát từ kiểm thử)**: Qua file test, tôi nhận ra độ ổn định của agent phụ thuộc rất nhiều vào khả năng test từng bước một cách xác định. Việc dùng `MockProvider` giúp kiểm chứng rằng agent không chỉ “trả lời đúng” mà còn “đi đúng quy trình”, ví dụ có gọi tool trước khi kết luận và có lưu dấu vết chạy vào `last_run_details`.

---

## IV. Future Improvements (5 Points)

- **Test Coverage**: Mở rộng `tests/test_langgraph_agent.py` để kiểm tra thêm các trường hợp parser error, tool không tồn tại, tham số sai kiểu, và vượt `max_steps`. Điều này sẽ giúp agent bền vững hơn trước các phản hồi khó đoán từ LLM.
- **Structured Tool Arguments**: Hiện tại agent vẫn tách tham số công cụ bằng chuỗi thô thông qua `_split_args()`. Trong tương lai, nên chuyển sang schema chặt chẽ hơn hoặc native tool-calling để giảm lỗi parse tham số.
- **Graph Robustness**: Có thể bổ sung các node chuyên biệt như `validate_action`, `retry_plan`, hoặc `summarize_answer` để đồ thị linh hoạt hơn. Ví dụ, khi parse lỗi ở bước đầu, agent có thể thử yêu cầu mô hình format lại thay vì kết thúc ngay.
