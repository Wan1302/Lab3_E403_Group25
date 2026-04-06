# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyen Duy Hieu
- **Student ID**: 2A202600153
- **Date**: 06/04/2026

---

## I. Technical Contribution

Trong dự án này, tôi chịu trách nhiệm xây dựng cấu trúc điều phối cốt lõi của Agent và hệ thống kiểm thử luồng suy luận tự động.

* **Modules Implementated**:
    * `src/agent/agent.py`: Hiện thực hóa lớp `ReActAgent`, trực tiếp xử lý vòng lặp ReAct, quản lý `history` và các bộ trích xuất dữ liệu (`_extract_action`, `_extract_final_answer`).
    * `tests/test_agent_workflow.py`: Phát triển `MockProvider` và hệ thống `Mock Tools` để giả lập các kịch bản suy luận đa bước mà không phụ thuộc vào API thực tế, giúp tối ưu hóa quá trình phát triển.
* **Code Highlights**:
    * **Hàm `_split_args` thông minh**: Tôi đã viết logic để xử lý linh hoạt các tham số có tên (Named Arguments) như `product="iPhone 15"` và tự động làm sạch các dấu ngoặc đơn/kép dư thừa.
    * **Regex đa ngôn ngữ**: Bộ trích xuất được thiết kế để nhận diện linh hoạt các từ khóa điều hướng bằng cả tiếng Anh và tiếng Việt (`Hành động`, `Action`, `Câu trả lời cuối`), giúp Agent hoạt động ổn định với nhiều dòng Model LLM khác nhau.
* **Documentation**: Mã nguồn của tôi đóng vai trò là "trung tâm điều phối". Nó nhận đầu vào, xây dựng prompt động từ lịch sử hội thoại, gọi LLM, thực thi công cụ và nạp kết quả `Observation` ngược lại để Agent tiếp tục suy luận cho đến khi đạt được mục tiêu.

---

## II. Debugging Case Study

* **Problem Description**: Agent bị kẹt hoặc báo lỗi thực thi công cụ dù LLM đã đưa ra đúng tên hàm. Lỗi phổ biến nhất là: `TypeError: calculate_total() takes 1 positional argument but 3 were given`.
* **Log Source**: Dữ liệu được trích xuất từ các sự kiện `AGENT_STEP` và `TOOL_EXECUTION` trong hệ thống log session.
* **Diagnosis**: LLM thường sinh ra tham số theo dạng Keyword (ví dụ: `Action: calculate_total(price=20000000, discount=0)`). Bộ bóc tách ban đầu không xử lý dấu `=`, dẫn đến việc truyền cả chuỗi `"price=20000000"` vào hàm Python thay vì chỉ truyền giá trị.
* **Solution**: Tôi đã cập nhật hàm `_split_args` để tự động tách bỏ phần tên biến trước dấu `=`, chỉ giữ lại giá trị cốt lõi để truyền vào hàm công cụ. Đồng thời, tôi thêm các khối `try-except` trong `_execute_tool` để bắt lỗi tham số và phản hồi lại cho LLM tự điều chỉnh ở bước sau.

---

## III. Personal Insights: Chatbot vs ReAct

1.  **Reasoning**: Khối `Thought` giúp Agent có khả năng "lập kế hoạch" (Planning). Thay vì trả lời bừa bãi, Agent sử dụng bước này để phân rã yêu cầu mua sắm phức tạp thành các bước: kiểm tra kho -> tìm mã -> tính ship -> tổng kết.
2.  **Reliability**: Agent có thể hoạt động tệ hơn Chatbot nếu gặp lỗi định dạng (Parser Error) hoặc bị cạn kiệt tài nguyên (Rate Limit/Timeout). Tuy nhiên, Agent đáng tin cậy hơn về dữ liệu thực tế vì nó lấy giá từ Tool thay vì "ảo giác" như Chatbot baseline.
3.  **Observation**: Kết quả trả về từ công cụ (`Observation`) đóng vai trò là "điểm neo" thực tế. Nếu `Observation` báo lỗi, Agent dựa vào đó để giải thích cho người dùng hoặc thử lại với tham số khác, điều mà Chatbot thông thường không thể làm được.

---

## IV. Future Improvements

* **Scalability**: Nâng cấp lên kiến trúc **LangGraph** để thay thế vòng lặp `while` đơn giản, giúp quản lý các trạng thái phức tạp và các luồng rẽ nhánh chuyên sâu.
* **Safety**: Triển khai bộ kiểm duyệt để rà soát các tham số công cụ trước khi thực thi, tránh việc gọi nhầm các tác vụ tốn phí hoặc gây lỗi hệ thống.
* **Performance**: Áp dụng cơ chế **Asynchronous Tool Execution** để thực thi nhiều công cụ cùng lúc (ví dụ: vừa check kho vừa check ship) nhằm giảm thời gian chờ đợi cho người dùng.