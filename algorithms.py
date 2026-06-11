import config
from sentence_transformers import CrossEncoder

class AdvancedRAGAlgorithms:
    def __init__(self):
        # Khởi tạo mô hình Reranker
        print("Loading Reranker Model...")
        self.reranker_model = CrossEncoder(config.RERANKER_MODEL_PATH)
        print("Reranker Model Loaded.")

    def advanced_rerank(self, original_query: str, retrieved_docs: list[dict]) -> list[dict]:
        """
        Ghép cặp query gốc với toàn bộ text của từng chunk: [[query, chunk_text], ...]
        Sử dụng BAAI/bge-reranker-v2-m3 để chấm điểm.
        Loại bỏ các chunk có điểm < config.RERANKER_THRESHOLD.
        """
        if not retrieved_docs:
            return []

        # Tạo cặp [query, chunk_text]
        pairs = [[original_query, doc["text"]] for doc in retrieved_docs]
        
        # Chấm điểm
        scores = self.reranker_model.predict(pairs)
        
        # Gán điểm và lọc
        passed_docs = []
        for i, doc in enumerate(retrieved_docs):
            doc["score"] = float(scores[i])
            if doc["score"] >= config.RERANKER_THRESHOLD:
                passed_docs.append(doc)
                
        print(f"[DEBUG] Passed chunks after reranking: {len(passed_docs)}")
                
        # Sắp xếp theo điểm giảm dần
        passed_docs.sort(key=lambda x: x["score"], reverse=True)
        return passed_docs

    def apply_token_budget(self, reranked_docs: list[dict]) -> list[dict]:
        """
        Áp dụng Token Budgeting và Hard Top-K.
        - Lấy tối đa config.MAX_CHUNKS.
        - Giới hạn tổng số token không vượt quá config.MAX_CONTEXT_TOKENS.
        """
        final_chunks = []
        current_tokens = 0
        
        for doc in reranked_docs:
            if len(final_chunks) >= config.MAX_CHUNKS:
                break
                
            # Ước lượng số token bằng số từ (word count) + một chút margin (thường 1 token ~ 0.75 words, ta lấy length split để tính xấp xỉ)
            # Nếu có thư viện tiktoken thì sẽ chính xác hơn, ở đây tạm tính 1 word ~ 1.3 tokens
            chunk_tokens = int(len(doc["text"].split()) * 1.3)
            
            if current_tokens + chunk_tokens <= config.MAX_CONTEXT_TOKENS:
                final_chunks.append(doc)
                current_tokens += chunk_tokens
            else:
                # Nếu vượt budget thì ngắt luôn
                break
                
        print(f"[DEBUG] Final chunks after token budgeting: {len(final_chunks)} (Estimated tokens: {current_tokens})")
        return final_chunks

    def lost_in_the_middle_sort(self, context_blocks: list[dict]) -> list[dict]:
        """
        Sắp xếp các blocks theo Lost-in-the-Middle.
        Block điểm cao nhất ở đầu, điểm cao thứ nhì ở cuối, ...
        """
        if not context_blocks:
            return []
            
        sorted_blocks = sorted(context_blocks, key=lambda x: x.get("score", 0), reverse=True)
        
        reordered = [None] * len(sorted_blocks)
        left = 0
        right = len(sorted_blocks) - 1
        
        for i, block in enumerate(sorted_blocks):
            if i % 2 == 0:
                reordered[left] = block
                left += 1
            else:
                reordered[right] = block
                right -= 1
                
        return reordered

# Khởi tạo instance
algorithms = AdvancedRAGAlgorithms()
