# ⚖️ Law RAG Web Application

Đây là một ứng dụng tra cứu pháp luật thông minh (RAG - Retrieval-Augmented Generation) được xây dựng với kiến trúc Full-stack (Flask, LangGraph, Groq, ChromaDB). Hệ thống ứng dụng nhiều kỹ thuật RAG nâng cao để đảm bảo câu trả lời luôn chính xác, bám sát các văn bản pháp luật hiện hành và có trích dẫn nguồn rõ ràng.

## 🏗️ Kiến trúc Công nghệ

- **Backend:** Flask, Python 3.10+
- **Vector Database:** ChromaDB (Chỉ đọc, tên collection: `legal_documents`)
- **LLM Orchestration:** LangChain, LangGraph, ChatGroq
- **Reranking:** `BAAI/bge-reranker-v2-m3` (thông qua `sentence-transformers`)
- **Frontend:** HTML5, TailwindCSS (CDN), Vanilla JavaScript
- **Reasoning LLM:** Hỗ trợ mô hình có khả năng tư duy suy luận như `qwen/qwen3-32b` thông qua API Groq.

## ⚙️ Quy trình hoạt động (Step-by-Step Workflow)

Hệ thống hoạt động theo luồng xử lý nghiêm ngặt (được điều phối bởi **LangGraph**) với hai chế độ: **Basic Mode** (Truy xuất cơ bản, không xử lý sâu) và **Think Mode** (Xử lý chuyên sâu - Advanced Pipeline). Dưới đây là quy trình chi tiết của chế độ chuyên sâu:

### Bước 1: Trích xuất Metadata & Giả định văn bản (Metadata Extraction & HyDE)
- Hệ thống sử dụng một LLM chuyên biệt để đọc câu hỏi và trích xuất các siêu dữ liệu pháp lý (như số hiệu văn bản `sign_number`, loại văn bản `document_type`, cơ quan ban hành...).
- Đồng thời áp dụng kỹ thuật HyDE (Hypothetical Document Embeddings), yêu cầu LLM viết nhanh 2-3 câu trả lời giả định cho câu hỏi đó, giúp việc tìm kiếm không gian vector sau này đạt được độ tương đồng ngữ nghĩa cao hơn so với chỉ dùng câu hỏi gốc.

### Bước 2: Truy xuất Dữ liệu Toàn văn (Full-Text Retrieval & Fallback Query)
- Hệ thống ghép câu hỏi gốc và văn bản giả định (HyDE) thành một chuỗi truy vấn để lấy ra danh sách tài liệu (`CHROMA_TOP_K`) từ ChromaDB.
- Tính năng **Fallback Query** được thiết kế để khắc phục nhược điểm của Metadata filtering: Hệ thống sẽ thử lọc tài liệu khớp chính xác với Metadata ở Bước 1. Nếu bộ lọc quá khắt khe khiến không tìm thấy kết quả, hệ thống tự động bỏ qua Metadata Filter và fallback về truy vấn vector thuần tuý (Vector Search) để tránh sót dữ liệu.

### Bước 3: Chấm điểm và Lọc nâng cao (Full-Text Reranking)
- Câu hỏi gốc của người dùng sẽ được ghép cặp với phần nguyên bản của từng khối tài liệu lấy được từ Bước 2.
- Mô hình **Cross-Encoder Reranker** (`BAAI/bge-reranker-v2-m3`) chấm điểm mức độ liên quan cho từng khối tài liệu dựa trên ngữ cảnh thực tế (điểm từ 0 đến 1).
- Những khối văn bản (chunks) có điểm số dưới mức trần thiết lập sẵn (`RERANKER_THRESHOLD = 0.3`) sẽ bị loại bỏ hoàn toàn.

### Bước 4: Kiểm soát Độ dài Ngữ cảnh (Token Budgeting)
- Để đảm bảo mô hình sinh text không bị quá tải, các tài liệu đạt chuẩn sẽ trải qua bước cấp phát token (Token Budgeting) và cắt giảm số lượng khối (Hard Top-K).
- Hệ thống ưu tiên giữ các tài liệu có điểm số cao nhất cho đến khi tối đa số lượng (`MAX_CHUNKS = 3`) hoặc tổng số lượng token tiệm cận giới hạn cửa sổ ngữ cảnh (`MAX_CONTEXT_TOKENS = 4000`).

### Bước 5: Sắp xếp theo chiến lược "Lost-in-the-Middle"
- Các mô hình ngôn ngữ lớn (LLM) thường ghi nhớ rất tốt thông tin ở phần đầu và phần cuối của văn bản, nhưng dễ "quên" thông tin nằm ở phần giữa.
- Thuật toán **Lost-in-the-Middle Sort** được áp dụng: Đẩy các khối tài liệu quan trọng nhất (điểm cao nhất) ra sát phần đầu và phần cuối của chuỗi tài liệu tổng hợp, còn các tài liệu ít quan trọng hơn sẽ được đưa vào phần giữa.

### Bước 6: Tổng hợp và Trả lời Suy luận (Strict Generation with Reasoning)
- Các khối tài liệu sau khi được tinh chỉnh và sắp xếp sẽ được ghép lại thành một **văn bản tham khảo** hoàn chỉnh, kèm đánh dấu nguồn rõ ràng (VD: `[Tài liệu 1]: Tên Văn Bản (Số hiệu)`).
- Reasoning LLM được yêu cầu sử dụng thẻ tư duy `<think>...</think>` để lập luận và phân tích nội bộ các vấn đề pháp lý. Sau khi suy nghĩ xong, LLM mới tổng hợp câu trả lời cuối cùng cho người dùng bên ngoài thẻ `<think>`.
- Câu trả lời đảm bảo tính nghiêm ngặt (Strict Generation) dựa trên 100% tài liệu cung cấp; tuyệt đối không suy diễn thêm thông tin không có trong luật.

### Bước 7: Hiển thị kết quả trên Giao diện
- Dữ liệu trả về cho frontend bao gồm: Câu trả lời tinh gọn của AI và danh sách các đoạn tài liệu Nguồn tham khảo.
- Backend tự động bóc tách và ẩn phần `<think>`, chỉ giữ lại lời giải đáp rành mạch. Dưới phần trả lời, hệ thống liệt kê cụ thể các đoạn tài liệu tham chiếu (Context blocks) cho phép người dùng trực tiếp kiểm chứng nội dung luật gốc.

## 🚀 Hướng dẫn Cài đặt & Chạy ứng dụng

1. **Tải dữ liệu ChromaDB:**
   
   Do thư mục ChromaDB có dung lượng lớn, project không lưu trực tiếp thư mục `chroma_db/` trên GitHub.

   Người dùng cần tải ChromaDB đã được build sẵn tại Google Drive:

   [Link Google Drive ChromaDB](https://drive.google.com/drive/folders/17DTqTD4Kc3oAnldqdVo2Yyn8FuWGm9u9?usp=sharing)

   Sau khi tải về, giải nén và đặt thư mục `chroma_db/` vào thư mục gốc của project:

   ```text
   RAG-for-LAW/
   ├── app.py
   ├── config.py
   ├── requirements.txt
   ├── chroma_db/
   └── ...
   ```

2. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình biến môi trường:**
   Tạo một file `.env` ở thư mục gốc và thêm API Key của Groq:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Khởi chạy ứng dụng:**
   ```bash
   python app.py
   ```
   Truy cập `http://localhost:5000` trên trình duyệt để bắt đầu sử dụng hệ thống.