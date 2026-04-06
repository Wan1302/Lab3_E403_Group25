import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.tiki_tools import TikiClient, _best_matching_products


def test_extract_search_results_from_next_data_html():
    html = """
    <html>
      <body>
        <script id="__NEXT_DATA__" type="application/json">
          {
            "props": {
              "initialState": {
                "catalog": {
                  "data": [
                    {
                      "id": 1,
                      "name": "Test Product A",
                      "url_path": "test-a-p1.html",
                      "price": 100000,
                      "original_price": 120000,
                      "discount_rate": 17,
                      "seller_name": "Seller A",
                      "rating_average": 4.5,
                      "quantity_sold": {"text": "Da ban 10"}
                    },
                    {
                      "id": 2,
                      "name": "Test Product B",
                      "url_path": "test-b-p2.html",
                      "price": 90000,
                      "original_price": 90000,
                      "discount_rate": 0,
                      "seller_name": "Seller B",
                      "rating_average": 4.8,
                      "quantity_sold": {"text": "Da ban 20"}
                    }
                  ]
                }
              }
            }
          }
        </script>
      </body>
    </html>
    """

    client = TikiClient()
    data = client._extract_next_data(html)
    items = [client._normalize_search_item(item) for item in data["props"]["initialState"]["catalog"]["data"]]

    assert len(items) == 2
    assert items[0]["name"] == "Test Product A"
    assert items[1]["price"] == 90000
    assert items[0]["product_url"].endswith("test-a-p1.html")


def test_best_matching_products_prefers_query_match():
    products = [
        {"name": "Op lung danh cho iPhone 15", "price": 50},
        {"name": "Apple iPhone 15", "price": 200},
        {"name": "Apple iPhone 15 Plus", "price": 300},
    ]

    matches = _best_matching_products(products, "iphone 15")

    assert len(matches) == 1
    assert matches[0]["name"] == "Apple iPhone 15"


def test_best_matching_products_returns_empty_when_match_is_weak():
    products = [
        {"name": "Bluetooth Keyboard Generic", "price": 100},
        {"name": "Wireless Mouse Generic", "price": 200},
    ]

    matches = _best_matching_products(products, "keychron k2")

    assert matches == []
