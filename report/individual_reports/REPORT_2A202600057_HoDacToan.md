# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ho Dac Toan
- **Student ID**: 2A202600057
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

- **Modules Implemented**:
  - `app.py` (Flask Web Server & API Route)
  - `templates/index.html` (Giao diện cấu trúc HTML)
  - `static/styles.css` (Hệ thống CSS/UI Design)
  - `static/app.js` (Logic Frontend & Tích hợp API)
- **Code Highlights**:
  - **Tích hợp API và xử lý bất đồng bộ (`app.js`)**: Cài đặt hàm `runComparison()` sử dụng fetch API để gọi endpoint `/api/compare`, xử lý trạng thái UI (loading/disabled) và cập nhật dữ liệu động vào DOM.
  - **Xử lý dữ liệu an toàn (Defensive Programming trong `app.js`)**: Xử lý các trường hợp null/undefined khi render chi tiết Agent để tránh crash UI khi phiên bản Chatbot không có dữ liệu gọi tool.
  - **Thiết kế UI/UX & Responsive (`styles.css` & `index.html`)**: Xây dựng bố cục dạng lưới 3 cột (3-column grid) để so sánh trực quan Chatbot, ReAct v1, và LangGraph v2. Sử dụng biến CSS để quản lý màu sắc và đảm bảo giao diện responsive.
  - **Routing Backend (`app.py`)**: Viết endpoint `@app.post("/api/compare")` tiếp nhận payload từ người dùng, gọi hàm `compare_versions()` và trả về JSON thống nhất kèm cơ chế xử lý lỗi HTTP.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Lỗi hiển thị UI (Frontend Crash) khi chạy thử nghiệm phiên bản Chatbot Baseline. Giao diện bị kẹt ở trạng thái "Dang goi mo hinh..." và không render được kết quả.
- **Log Source/Error Trace**: 
  Lỗi hiển thị trên Console của trình duyệt: `TypeError: Cannot read properties of undefined (reading 'map') at buildAgentDetails`
- **Diagnosis**: Phiên bản Chatbot Baseline hoạt động độc lập và không có cơ chế gọi công cụ (tool calling). Do đó, API backend trả về object `chatbot.details` không chứa key `tool_calls` (hoặc trả về null). Trong file `app.js` ban đầu, hàm map được gọi trực tiếp trên `data.details.tool_calls`, dẫn đến lỗi TypeError và làm gián đoạn toàn bộ luồng Javascript.
- **Solution**: Cập nhật lại logic trong `app.js` bằng cách thêm toán tử fallback `|| []` để đảm bảo luôn có một mảng rỗng nếu dữ liệu bị thiếu.

  *Đoạn code đã sửa (app.js):*

      const toolCalls = (data.details.tool_calls || [])
        .map((tool, index) => `${index + 1}. ${tool.tool_name}(${tool.args})\n   => ${tool.observation}`)
        .join("\n");

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning (Khả năng suy luận)**: Thông qua phần "Dấu vết suy luận" trên UI, có thể thấy rõ khối Thought giúp ReAct Agent chia nhỏ bài toán phức tạp (như so sánh giá 2 mặt hàng) thành các bước tuần tự. Chatbot thường cố gắng đoán câu trả lời ngay lập tức, trong khi ReAct có tư duy "Tìm kiếm -> Đọc kết quả -> Đưa ra quyết định".
2. **Reliability (Độ tin cậy & Đánh đổi)**: Nhìn vào bảng Metric Grid đã xây dựng, ReAct Agent tốn nhiều Tổng tokens và Độ trễ (Latency) cao hơn gấp nhiều lần so với Chatbot. Mặc dù ReAct đưa ra dữ liệu thực tế (grounded data), nhưng trong các câu hỏi giao tiếp thông thường hoặc câu hỏi quá đơn giản, việc kích hoạt ReAct trở nên cồng kềnh và lãng phí.
3. **Observation (Quan sát môi trường)**: Nhờ có phần log hiển thị kết quả quan sát trên UI, tôi nhận thấy Agent phụ thuộc rất nhiều vào format của dữ liệu công cụ trả về. Nếu API trả về chuỗi JSON quá dài hoặc lộn xộn, LLM đôi khi bị "bối rối" và phải mất thêm 1-2 bước suy luận để trích xuất đúng trường giá tiền.

---

## IV. Future Improvements (5 Points)


- **Scalability (Real-time Streaming - UI/UX)**: Hiện tại hệ thống phải đợi toàn bộ 3 phiên bản chạy xong mới hiển thị kết quả (gây ra thời gian chờ rất lâu). Cần thay thế fetch API bằng Server-Sent Events (SSE) hoặc WebSockets ở cả Backend và Frontend để stream từng token câu trả lời ra màn hình ngay lập tức.
- **Performance (Caching)**: Cần triển khai cơ chế Caching (ví dụ: Redis) tại lớp Backend. Nếu một người dùng nhập lại đúng câu lệnh đã có trên giao diện, hệ thống nên trả về kết quả ngay lập tức thay vì bắt LLM chạy lại luồng ReAct từ đầu.
- **Safety & Error Recovery**: Bổ sung cơ chế Timeout cho các requests. Đối với LangGraph v2, nếu đồ thị rơi vào vòng lặp vô hạn (Infinite Loop), giao diện cần nhận được tín hiệu cảnh báo từ backend và hiển thị nút "Force Stop" (Dừng ép buộc) cho người dùng.