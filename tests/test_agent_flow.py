import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.openai_provider import OpenAIProvider
from src.agent.agent import ReActAgent

def test_agent():
    load_dotenv()
    
    print("--- Testing ReAct Agent Core Workflows ---")
    provider = OpenAIProvider(model_name="gpt-4o-mini")
    
    mock_tools = [
        {
            "name": "search_products",
            "description": "Lấy thông tin giá, id và khối lượng (weight) của sản phẩm.",
            "parameters": '{"query": "tên sản phẩm"}'
        },
        {
            "name": "check_stock",
            "description": "Kiểm tra số lượng tồn kho.",
            "parameters": '{"product_id": "mã sản phẩm"}'
        },
        {
            "name": "calculate_shipping",
            "description": "Tính phí vận chuyển theo khối lượng và địa điểm.",
            "parameters": '{"destination": "địa chỉ", "weight_grams": "khối lượng"}'
        },
        {
            "name": "get_discount",
            "description": "Áp dụng và lấy giá trị tiền được giảm từ mã giảm giá.",
            "parameters": '{"code": "mã giảm giá", "order_value": "tổng giá trị đơn hàng"}'
        }
    ]
    
    agent = ReActAgent(llm=provider, tools=mock_tools)
    
    queries = [
        "Cảm ơn bạn nhé, tư vấn quá tuyệt vời!",
        "Cho hỏi trên sàn có tivi Samsung không? Dùng mã GIAM50 để thanh toán nha",
        "So sánh giá của iPhone 15 và iPhone 16 bản thường",
        "Máy vắt cam gửi đi TP Hồ Chí Minh thì phí ship tính sao?"
    ]
    
    for q in queries:
        print("\n" + "*"*60)
        agent.run(q)

if __name__ == "__main__":
    test_agent()
