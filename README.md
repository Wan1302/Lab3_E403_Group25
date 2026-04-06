# Lab3_E403_25

## Tong quan

Project nay demo su khac nhau giua:

- `Chatbot baseline`: tra loi truc tiep bang LLM
- `ReAct v1`: suy nghi, goi tool, nhan observation, roi moi ket luan
- `LangGraph v2`: stateful graph agent voi node LLM va node tool

Phien ban hien tai tap trung vao bai toan mua sam bang du lieu cong khai tu `Tiki`.
Frontend web hien thi song song 3 ket qua, cung voi:

- prompt tokens
- completion tokens
- tong tokens
- do tre
- so buoc suy luan
- so lan goi tool

## Kien truc chinh

- `app.py`: Flask web app
- `src/runtime.py`: khoi tao provider, toolset, va chay so sanh 3 phien ban
- `src/chatbot/baseline.py`: chatbot baseline
- `src/agent/agent.py`: ReAct agent v1
- `src/agent/langgraph_agent.py`: LangGraph agent v2
- `src/tools/tiki_tools.py`: tool lay du lieu cong khai tu Tiki
- `src/telemetry/logger.py`: ghi log JSON
- `src/telemetry/metrics.py`: tong hop token, latency, cost estimate

## Tool hien tai

- `search_tiki_products(query, limit)`
- `find_cheapest_tiki_product(query, limit)`
- `calculate_tiki_total(query, quantity, limit)`
- `compare_tiki_options(query, quantity, limit)`

## Yeu cau

- Python 3.12 hoac Docker
- OpenAI Platform API key
- Ket noi Internet de truy van Tiki

## Chay bang Docker

1. Tao file `.env` tu `.env.example`
2. Dien API key that vao `OPENAI_API_KEY`
3. Chay:

```powershell
docker compose up --build
```

4. Mo trinh duyet:

```text
http://localhost:8000
```

## Mau file .env

```env
OPENAI_API_KEY=sk-your-real-key
GEMINI_API_KEY=

LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf

DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
SHOPPING_TOOLSET=tiki
LOG_LEVEL=INFO
```

## Chay local khong dung Docker

```powershell
pip install -r requirements.txt
python app.py
```

## Test

```powershell
pytest tests\test_agent_workflow.py tests\test_tiki_tools.py -q
```

## 5 use case demo

1. Hay tim tren Tiki va cho toi biet gia cong khai hien tai cua Apple iPhone 13.
2. Hay tim lua chon cong khai re nhat tren Tiki cho Apple iPhone 14.
3. Toi muon mua 2 chiec Apple iPhone 13. Hay dung ket qua tren Tiki va tinh tong tien cong khai re nhat.
4. Hay so sanh cac lua chon hang dau tren Tiki cho Sony WH-1000XM5 va cho toi biet nguoi ban nao dang co gia cong khai re nhat.
5. Toi can mua 2 tai nghe Sony WH-1000XM5. Hay dung du lieu cong khai tren Tiki, so sanh cac lua chon hien co va cho toi biet tong tien re nhat.

## Pipeline ngan gon

1. Nguoi dung nhap cau hoi tren frontend
2. Frontend goi `POST /api/compare`
3. Backend chay `Chatbot baseline`
4. Backend chay `ReAct v1`
5. Backend chay `LangGraph v2`
6. Hai agent co the goi tool Tiki
7. Telemetry ghi token, latency, so buoc
8. Frontend hien thi 3 ket qua song song

## Phan tich log

Co the dung script:

```powershell
python scripts/analyze_logs.py --log logs\2026-04-06.log
```

Hoac xuat markdown:

```powershell
python scripts/analyze_logs.py --log logs\2026-04-06.log --markdown report\group_report\METRICS_SUMMARY.md
```
