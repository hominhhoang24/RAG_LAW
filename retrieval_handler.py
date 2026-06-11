import chromadb
import config

class RetrievalHandler:
    def __init__(self):
        # Kết nối tới ChromaDB (read-only)
        self.client = chromadb.PersistentClient(path=config.CHROMADB_PERSIST_DIRECTORY)
        self.collection = self.client.get_collection(name=config.COLLECTION_NAME)

    def retrieve_advanced(self, query_string: str, metadata_filter: dict = None, top_k: int = config.CHROMA_TOP_K) -> list[dict]:
        """
        Truy vấn ChromaDB lấy full-text chunks.
        Bao gồm cơ chế Fallback Query: nếu có where_clause nhưng không tìm thấy kết quả,
        sẽ tự động bỏ where_clause và query lại bằng vector thuần túy.
        
        Returns: Danh sách các dict, mỗi dict chứa text và metadata của chunk.
        """
        try:
            # Chuẩn hoá metadata_filter: loại bỏ các key có value rỗng/None
            valid_filters = {}
            if metadata_filter:
                for k, v in metadata_filter.items():
                    if isinstance(v, str) and v.strip():
                        valid_filters[k] = v.strip()
                    elif v and not isinstance(v, str):
                        valid_filters[k] = v
            
            # Format where_clause theo chuẩn ChromaDB
            where_clause = None
            if len(valid_filters) == 1:
                where_clause = valid_filters
            elif len(valid_filters) > 1:
                where_clause = {"$and": [{k: v} for k, v in valid_filters.items()]}
                
            # Lần 1: Thử với metadata_filter (nếu có)
            results = self.collection.query(
                query_texts=[query_string],
                n_results=top_k,
                where=where_clause if where_clause else None
            )
            
            raw_chunks = self._extract_docs_from_results(results)
            
            # Fallback Query: Nếu có filter mà kết quả rỗng
            if len(raw_chunks) == 0 and where_clause:
                print(f"[DEBUG] Empty result with filter {where_clause}. Running fallback query without filter.")
                results = self.collection.query(
                    query_texts=[query_string],
                    n_results=top_k
                )
                raw_chunks = self._extract_docs_from_results(results)
                
            return raw_chunks
        except Exception as e:
            print(f"Error querying ChromaDB in advanced mode: {e}")
            return []

    def retrieve_basic(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Dùng cho RAG thông thường (Think = False).
        Chỉ truyền user_query nguyên bản và lấy k=3.
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            return self._extract_docs_from_results(results)
        except Exception as e:
            print(f"Error querying ChromaDB in basic mode: {e}")
            return []

    def _extract_docs_from_results(self, results: dict) -> list[dict]:
        """
        Hàm phụ trợ để trích xuất text và metadata từ kết quả của ChromaDB.
        """
        docs = []
        if "documents" in results and results["documents"]:
            for i, doc_text in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else {}
                docs.append({
                    "chunk_id": results["ids"][0][i] if "ids" in results else str(i),
                    "text": doc_text,
                    "metadata": metadata
                })
        return docs

# Khởi tạo instance
retriever = RetrievalHandler()
