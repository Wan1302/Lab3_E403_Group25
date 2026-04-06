from flask import Flask, jsonify, render_template, request

from src.runtime import TIKI_TEST_CASES, build_toolset, compare_versions


app = Flask(__name__)


@app.get("/")
def index():
    _, _, toolset_name = build_toolset()
    return render_template(
        "index.html",
        example_prompts=TIKI_TEST_CASES,
        toolset_name=toolset_name,
    )


@app.post("/api/compare")
def compare():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Vui long nhap cau hoi hoac yeu cau mua sam."}), 400

    try:
        result = compare_versions(question)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
