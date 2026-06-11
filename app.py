from flask import Flask, render_template, request, jsonify
from llm_handler import app_graph

app = Flask(__name__)

@app.route("/")
def index():
    """Render the main UI."""
    return render_template("index.html")

@app.route("/api/query", methods=["POST"])
def query_api():
    """
    Nhận câu hỏi từ frontend, chạy qua LangGraph và trả về phản hồi cùng với metadata (context blocks, điểm số).
    """
    data = request.json
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' field"}), 400
        
    user_query = data["query"]
    use_think = data.get("use_think", False) # Mặc định bật Think
    
    try:
        # Khởi tạo state ban đầu cho graph
        initial_state = {"user_query": user_query, "use_think": use_think}
        
        # Thực thi workflow
        result_state = app_graph.invoke(initial_state)
        
        # Trả về kết quả và metadata cho UI
        return jsonify({
            "response": result_state.get("final_response", ""),
            "metadata": {
                "context_blocks": result_state.get("final_chunks", [])
            }
        })
    except Exception as e:
        print(f"Error executing LangGraph: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
