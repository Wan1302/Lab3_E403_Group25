import json
import re
import unicodedata
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests


TIKI_BASE_URL = "https://tiki.vn"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

ACCESSORY_KEYWORDS = {
    "op",
    "op lung",
    "case",
    "bao da",
    "cuong luc",
    "cap",
    "cable",
    "adapter",
    "sac",
    "charger",
    "feet",
    "skatez",
    "mieng dan",
    "dan man hinh",
    "cover",
}


class TikiClient:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def search_products(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        response = self.session.get(
            f"{TIKI_BASE_URL}/search",
            params={"q": query},
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = self._extract_next_data(response.text)
        products = (
            data.get("props", {})
            .get("initialState", {})
            .get("catalog", {})
            .get("data", [])
        )

        normalized = [self._normalize_search_item(item) for item in products]
        normalized = [item for item in normalized if item.get("price") is not None]
        return normalized[: max(1, limit)]

    def _extract_next_data(self, html: str) -> Dict[str, Any]:
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not match:
            raise ValueError("Không tìm thấy dữ liệu trang Tiki.")
        return json.loads(match.group(1))

    def _normalize_search_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        quantity_sold = item.get("quantity_sold") or {}
        if isinstance(quantity_sold, dict):
            quantity_sold_text = quantity_sold.get("text")
        else:
            quantity_sold_text = None

        url_path = item.get("url_path") or ""
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "price": item.get("price"),
            "original_price": item.get("original_price"),
            "discount_rate": item.get("discount_rate"),
            "seller_name": item.get("seller_name"),
            "rating_average": item.get("rating_average"),
            "quantity_sold_text": quantity_sold_text,
            "is_authentic": item.get("is_authentic"),
            "is_official_store": item.get("is_from_official_store"),
            "product_url": urljoin(f"{TIKI_BASE_URL}/", url_path),
        }


_client = TikiClient()


def _load_products(query: str, limit: str) -> List[Dict[str, Any]]:
    return _client.search_products(query, _parse_limit(limit))


def _load_products_or_message(query: str, limit: str):
    try:
        return _load_products(query, limit), None
    except requests.RequestException as exc:
        return None, f"Không thể kết nối tới dữ liệu Tiki trực tiếp: {exc.__class__.__name__}."
    except Exception as exc:
        return None, f"Không thể phân tích dữ liệu Tiki trực tiếp: {exc}."


def _normalize_text(value: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def _match_score(query: str, product_name: str) -> float:
    normalized_query = _normalize_text(query)
    normalized_name = _normalize_text(product_name)
    query_tokens = [token for token in normalized_query.split() if len(token) >= 2]
    name_tokens = set(normalized_name.split())
    if not query_tokens:
        return 0.0

    matched = sum(1 for token in query_tokens if token in name_tokens)
    score = matched / len(query_tokens)

    if normalized_query in normalized_name:
        score += 0.25

    query_mentions_accessory = any(keyword in normalized_query for keyword in ACCESSORY_KEYWORDS)
    name_mentions_accessory = any(keyword in normalized_name for keyword in ACCESSORY_KEYWORDS)
    if name_mentions_accessory and not query_mentions_accessory:
        score *= 0.15

    return score


def _best_matching_products(products: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    if not products:
        return []

    scored = []
    best_score = 0.0
    for product in products:
        score = _match_score(query, product["name"])
        if score > best_score:
            best_score = score
        scored.append((score, product))

    if best_score < 0.6:
        return []

    filtered = [product for score, product in scored if score == best_score]

    deduped = []
    seen_urls = set()
    for product in filtered:
        product_url = product.get("product_url")
        if product_url in seen_urls:
            continue
        seen_urls.add(product_url)
        deduped.append(product)

    return deduped


def _parse_limit(limit: str) -> int:
    parsed = int(limit)
    if parsed <= 0:
        raise ValueError("limit phải lớn hơn 0")
    return min(parsed, 20)


def _parse_quantity(quantity: str) -> int:
    parsed = int(quantity)
    if parsed <= 0:
        raise ValueError("quantity phải lớn hơn 0")
    return parsed


def _format_product_line(index: int, product: Dict[str, Any]) -> str:
    original_price = product.get("original_price") or product["price"]
    savings = max(0, original_price - product["price"])
    return (
        f"{index}. {product['name']} | gia_hien_tai={product['price']} VND | "
        f"gia_goc={original_price} VND | tiet_kiem={savings} VND | "
        f"phan_tram_giam={product.get('discount_rate', 0)}% | "
        f"nguoi_ban={product.get('seller_name', 'khong_ro')} | "
        f"danh_gia={product.get('rating_average', 'khong_ro')} | "
        f"url={product['product_url']}"
    )


def search_tiki_products(query: str, limit: str = "5") -> str:
    products, error = _load_products_or_message(query, limit)
    if error:
        return error
    if not products:
        return f"Không tìm thấy sản phẩm nào trên Tiki cho từ khóa '{query}'."

    lines = [f"Các kết quả nổi bật trên Tiki cho '{query}':"]
    lines.extend(_format_product_line(index, product) for index, product in enumerate(products, start=1))
    return "\n".join(lines)


def find_cheapest_tiki_product(query: str, limit: str = "10") -> str:
    products, error = _load_products_or_message(query, limit)
    if error:
        return error
    if not products:
        return f"Không tìm thấy sản phẩm nào trên Tiki cho từ khóa '{query}'."

    candidates = _best_matching_products(products, query)
    if not candidates:
        return f"Không tìm thấy kết quả Tiki đủ tin cậy cho từ khóa '{query}'."
    cheapest = min(candidates, key=lambda item: item["price"])
    original_price = cheapest.get("original_price") or cheapest["price"]
    savings = max(0, original_price - cheapest["price"])

    return (
        f"Kết quả Tiki công khai rẻ nhất cho '{query}' là {cheapest['name']} với giá "
        f"{cheapest['price']} VND từ người bán {cheapest.get('seller_name', 'không rõ')}. "
        f"Mức tiết kiệm so với giá gốc là {savings} VND. "
        f"URL: {cheapest['product_url']}"
    )


def calculate_tiki_total(query: str, quantity: str, limit: str = "10") -> str:
    products, error = _load_products_or_message(query, limit)
    if error:
        return error
    if not products:
        return f"Không tìm thấy sản phẩm nào trên Tiki cho từ khóa '{query}'."

    qty = _parse_quantity(quantity)
    candidates = _best_matching_products(products, query)
    if not candidates:
        return f"Không tìm thấy kết quả Tiki đủ tin cậy cho từ khóa '{query}'."
    cheapest = min(candidates, key=lambda item: item["price"])
    original_price = cheapest.get("original_price") or cheapest["price"]

    subtotal = cheapest["price"] * qty
    original_total = original_price * qty
    total_savings = max(0, original_total - subtotal)

    return (
        f"Tổng chi phí công khai tốt nhất trên Tiki cho {qty} x '{query}' là {subtotal} VND, dùng "
        f"{cheapest['name']} từ người bán {cheapest.get('seller_name', 'không rõ')}. "
        f"Tổng số tiền tiết kiệm so với giá gốc là {total_savings} VND. "
        f"Đơn giá: {cheapest['price']} VND. URL: {cheapest['product_url']}"
    )


def compare_tiki_options(query: str, quantity: str, limit: str = "5") -> str:
    products, error = _load_products_or_message(query, limit)
    if error:
        return error
    if not products:
        return f"Không tìm thấy sản phẩm nào trên Tiki cho từ khóa '{query}'."

    qty = _parse_quantity(quantity)
    candidates = _best_matching_products(products, query)
    if not candidates:
        return f"Không tìm thấy kết quả Tiki đủ tin cậy cho từ khóa '{query}'."
    lines = [f"So sánh các lựa chọn Tiki cho '{query}' với số lượng {qty}:"]
    for index, product in enumerate(candidates, start=1):
        total = product["price"] * qty
        original_price = product.get("original_price") or product["price"]
        savings = max(0, (original_price * qty) - total)
        lines.append(
            f"{index}. {product['name']} | tong_tien={total} VND | "
            f"nguoi_ban={product.get('seller_name', 'không rõ')} | "
            f"tiet_kiem={savings} VND | url={product['product_url']}"
        )
    return "\n".join(lines)


def build_tiki_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "search_tiki_products",
            "description": (
                "Tìm kiếm kết quả sản phẩm công khai trực tiếp trên Tiki theo từ khóa người dùng. "
                "Tham số: query, limit"
            ),
            "func": search_tiki_products,
        },
        {
            "name": "find_cheapest_tiki_product",
            "description": (
                "Tìm kết quả công khai rẻ nhất trên Tiki cho một từ khóa sản phẩm. "
                "Tham số: query, limit"
            ),
            "func": find_cheapest_tiki_product,
        },
        {
            "name": "calculate_tiki_total",
            "description": (
                "Tính tổng tiền công khai rẻ nhất trên Tiki cho từ khóa sản phẩm và số lượng. "
                "Tham số: query, quantity, limit"
            ),
            "func": calculate_tiki_total,
        },
        {
            "name": "compare_tiki_options",
            "description": (
                "So sánh nhiều kết quả công khai trực tiếp trên Tiki cho một từ khóa sản phẩm và số lượng. "
                "Tham số: query, quantity, limit"
            ),
            "func": compare_tiki_options,
        },
    ]
