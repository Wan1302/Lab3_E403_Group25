import requests
from typing import Dict, Any
from src.telemetry.logger import logger

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_tiki_products(query: str) -> Dict[str, Any]:
    url = f"https://tiki.vn/api/v2/products?q={query}&limit=3"
    logger.log_event("API_CALL", {"service": "Tiki Search", "url_browsed": url})
    try:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        data = res.json().get("data", [])
        
        if not data:
            return {"error": "Không tìm thấy sản phẩm."}
            
        # Trả về kết quả đầu tiên (tìm kiếm chính xác nhất)
        item = data[0]
        return {
            "product_id": str(item.get("id")),
            "name": item.get("name"),
            "price": item.get("price"),
            "original_price": item.get("list_price"),
            "weight_grams": item.get("weight_grams", 500) # Fallback 500g nếu shop quên để
        }
    except Exception as e:
        return {"error": f"Lỗi kết nối Tiki Search: {str(e)}"}

def check_tiki_stock(product_id: str) -> Dict[str, Any]:
    url = f"https://tiki.vn/api/v2/products/{product_id}"
    logger.log_event("API_CALL", {"service": "Tiki Detail", "url_browsed": url})
    try:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        
        qty = data.get("stock_item", {}).get("qty", 0)
        status = "in_stock" if (qty > 0 or data.get("inventory_status") == "available") else "out_of_stock"
        
        return {
            "status": status,
            "quantity": qty if qty > 0 else (1 if status == "in_stock" else 0)
        }
    except Exception as e:
        return {"error": f"Lỗi kết nối Tiki Detail: {str(e)}"}

def calculate_shipping(destination: str, weight_grams: int) -> Dict[str, Any]:
    """Giả lập hàm tính phí ship nội địa"""
    dest = destination.lower()
    base_fee = 30000
    
    if "hà nội" in dest or "hn" in dest:
        base_fee = 15000
    elif "hcm" in dest or "hồ chí minh" in dest:
        base_fee = 20000
    
    # Phụ phụ 5,000đ mỗi 1kg (1000g)
    extra_fee = (weight_grams / 1000) * 5000
    total_fee = base_fee + extra_fee
    
    return {"fee": int(total_fee), "message": f"Ship {weight_grams}g đến {destination}"}

def apply_discount(code: str, order_value: float) -> Dict[str, Any]:
    """Giả lập hàm áp mã giảm giá"""
    code = str(code).upper()
    error_res = {"amount": 0}
    
    if code == "NEW10":
        # Giảm 10%, tối đa 50k
        discount = min(order_value * 0.1, 50000)
        return {"amount": int(discount), "message": "Áp dụng thành công mã NEW10 (Giảm 10% tối đa 50k)"}
    elif code == "GIAM50":
        error_res["error"] = "Expired"
        error_res["message"] = "Mã GIAM50 đã hết hạn sử dụng"
        return error_res
    elif code == "FREESHIP":
        return {"amount": 30000, "message": "Áp dụng mã FREESHIP (Giảm 30k phí vận chuyển)"}
    
    error_res["error"] = "Invalid"
    error_res["message"] = "Mã giảm giá không tồn tại"
    return error_res