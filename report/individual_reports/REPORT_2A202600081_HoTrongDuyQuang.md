# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ho Trong Duy Quang
- **Student ID**: 2A202600081
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implementated**: `src/tools/tiki_tools.py`, `tests/test_tiki_tools.py`, `test_cases.md`
- **Code Highlights**:
  I implemented the Tiki product-retrieval toolset so the agent can answer shopping questions with grounded public marketplace data instead of relying on unsupported guesses. My main contributions are:

  1. Building a `TikiClient` that sends search requests to Tiki and extracts structured product data from the `__NEXT_DATA__` script embedded in the HTML page.
  2. Normalizing raw search results into a consistent product schema containing price, original price, seller, rating, discount, and URL.
  3. Designing a product-matching heuristic that reduces noise from accessories such as phone cases when the user is actually asking for a phone.
  4. Exposing four tools for the ReAct agent:
    - `search_tiki_products`: Searches public Tiki listings based on a user keyword and returns the most relevant product results.
    - `find_cheapest_tiki_product`: Finds the cheapest reliable public Tiki result for a given product query.
    - `calculate_tiki_total`: Calculates the lowest public total cost on Tiki for a product query and a requested quantity.
    - `compare_tiki_options`: Compares multiple relevant public Tiki results for a product query and quantity.
    

  I also wrote unit tests that validate both parsing and ranking behavior. In `tests/test_tiki_tools.py`, I tested parsing mock `__NEXT_DATA__` HTML and confirmed that `_best_matching_products()` prefers `Apple iPhone 15` over `Op lung danh cho iPhone 15` when the query is `iphone 15`.
- **Documentation**:
  My code is integrated into the ReAct workflow through `build_tiki_tools()`, which publishes each tool's name, description, and callable function to the agent. This allows the agent to retrieve Tiki data, compare options, and compute grounded totals. I also contributed `test_cases.md` as a shared question set so both the baseline chatbot and the ReAct agent can be evaluated under the same prompts.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**:
  A key failure case in shopping queries is that Tiki search results can include accessories mixed with the actual target product. For example, a query like `iphone 15` may return phone cases, cables, or screen protectors. If the system simply chooses the cheapest item from raw search results, it can give a completely misleading answer by reporting an accessory price instead of the phone price.
- **Log Source**: `logs/2026-04-06.log`
  ```json
  {"timestamp": "2026-04-06T09:15:15.617606", "event": "CHATBOT_START", "data": {"input": "giá của iphone 13 bao nhiêu", "model": "gpt-4o", "mode": "json_chatbot"}}
  {"timestamp": "2026-04-06T09:15:17.774559", "event": "CHATBOT_END", "data": {"intent": "price_check", "needs_follow_up": false, "latency_ms": 2156}}
  ```
  This log confirms that price-checking is a real user scenario in the system, so noisy marketplace retrieval can directly cause wrong final answers.
- **Diagnosis**:
  The issue was mainly caused by retrieval quality rather than just prompt wording. Marketplace search pages are noisy by nature: they mix core products with related accessories. A naive strategy such as selecting the first item or the cheapest item is therefore unreliable. This is especially dangerous for phone queries because accessory prices are much lower and can dominate a naive ranking.
- **Solution**:
  I addressed this problem by adding `_normalize_text()`, `_match_score()`, and `_best_matching_products()` to filter candidates before price comparison. The heuristic:

  - normalizes Vietnamese/ASCII text for stable matching,
  - scores token overlap between the query and product name,
  - boosts exact phrase containment,
  - penalizes accessory keywords when the user did not ask for accessories,
  - rejects weak matches below a confidence threshold.

  I then wrote regression tests to lock this behavior:

  - `test_best_matching_products_prefers_query_match()` ensures the tool selects the actual phone over a cheaper accessory.
  - `test_best_matching_products_returns_empty_when_match_is_weak()` ensures the system abstains instead of pretending confidence for unrelated products.

  This fix improved the quality of the observation that is returned to the ReAct agent, which in turn improves the final answer quality.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1. **Reasoning**:
   The `Thought -> Action -> Observation` flow is much better than a direct chatbot response for marketplace tasks. A normal chatbot may try to answer immediately from prior knowledge, but the ReAct agent can decide to call the Tiki tool first, inspect the returned products, and then choose the most relevant answer. This is especially useful for questions such as finding the cheapest option or calculating a total cost for multiple items.
2. **Reliability**:
   The ReAct agent is not always better. It can be slower and more expensive for broad or vague questions like `Voi 20 trieu dong thi toi co the mua dien thoai gi`, because it may need multiple search and comparison steps. It can also perform worse on out-of-domain questions such as stock-market queries listed in `test_cases.md`, since the Tiki tools are not designed for that domain.
3. **Observation**:
   Observation quality strongly affects the next reasoning step. If the observation contains irrelevant accessories or weak matches, the agent may build a good reasoning chain on top of bad evidence. After improving the Tiki matching logic, the observations became more trustworthy, which makes the downstream reasoning step safer and more accurate.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Add caching and asynchronous execution for repeated marketplace queries, and replace HTML scraping with a more stable data source or official API if available.
- **Safety**: Add a validation layer before the final answer to confirm that the selected result is a main product rather than an accessory, and require the agent to abstain when confidence is too low.
- **Performance**: Improve ranking with richer signals such as product category, seller trust, and semantic similarity so the LLM only sees the most relevant validated candidates.

---

