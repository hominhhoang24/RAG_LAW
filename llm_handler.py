import json
import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import config
from retrieval_handler import retriever
from algorithms import algorithms

# Định nghĩa State cho LangGraph
class WorkflowState(TypedDict):
    user_query: str
    use_think: bool
    extracted_metadata: dict
    hypothetical_doc: str
    final_chunks: List[dict]
    final_response: str

# Khởi tạo mô hình Groq
llm = ChatGroq(
    temperature=0, 
    model_name=config.GROQ_MODEL_NAME, 
    api_key=config.GROQ_API_KEY
)

def strip_think_tags(text: str) -> str:
    """Loại bỏ khối <think>...</think> thường xuất hiện trong các Reasoning LLM. Xử lý cả trường hợp thẻ chưa đóng."""
    return re.sub(r'<think>.*?(?:</think>|$)', '', text, flags=re.DOTALL).strip()

def extract_metadata_hyde(state: WorkflowState):
    """
    Node 1: Thay thế Query Expansion bằng Metadata Extraction & HyDE.
    Chỉ chạy khi use_think = True.
    """
    query = state["user_query"]
    
    prompt = f"""Bạn là một chuyên gia phân tích pháp lý. Dựa vào câu hỏi dưới đây, hãy thực hiện 2 nhiệm vụ:
1. Trích xuất metadata (nếu có, ví dụ: số hiệu văn bản "sign_number", hoặc loại văn bản "document_type"). Nếu không có thì để rỗng.
2. Viết 2-3 câu định nghĩa khái quát, giả thuyết trả lời cho câu hỏi đó (không bịa số liệu hay điều luật cụ thể).

Câu hỏi: {query}

Phải trả về ĐÚNG định dạng JSON sau, không kèm bất kỳ giải thích nào khác:
{{
    "extracted_metadata": {{
        "issuing_agency": "...",
        "promulgation_date": "...",
        "sign_number": "...",
        "signer": "...",
        "type": "..."
    }},
    "hypothetical_doc": "..."
}}"""
    
    sys_msg = SystemMessage(content="Bạn là một hệ thống trích xuất và tạo văn bản giả định (HyDE) trả về JSON chuẩn.")
    human_msg = HumanMessage(content=prompt)
    
    extracted_metadata = {}
    hypothetical_doc = ""
    
    try:
        response = llm.invoke([sys_msg, human_msg])
        content = strip_think_tags(response.content)
        print(f"[DEBUG] Raw LLM response for metadata extraction (cleaned): {content}")
        
        # Tìm phần JSON
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            parsed_json = json.loads(match.group(0))
            extracted_metadata = parsed_json.get("extracted_metadata", {})
            hypothetical_doc = parsed_json.get("hypothetical_doc", "")
        else:
            print("[DEBUG] No JSON found in response.")
            
    except Exception as e:
        print(f"Lỗi khi trích xuất metadata: {e}")
        
    return {
        "extracted_metadata": extracted_metadata,
        "hypothetical_doc": hypothetical_doc
    }

def retrieve_and_process_advanced(state: WorkflowState):
    """
    Node 2 -> Node 5 (Advanced Pipeline):
    - Pre-Filtering & Retrieval
    - Reranking
    - Token Budgeting
    - Lost-in-the-Middle
    Chỉ chạy khi use_think = True.
    """
    query = state["user_query"]
    hypothetical_doc = state.get("hypothetical_doc", "")
    metadata_filter = state.get("extracted_metadata", {})
    
    # Query string cho ChromaDB
    query_for_embedding = f"{query} {hypothetical_doc}".strip()
    
    # 2. Vector Retrieval (Full-Text, Fallback Query included in retriever)
    raw_chunks = retriever.retrieve_advanced(query_for_embedding, metadata_filter)
    
    # 3. Full-Text Reranking
    reranked_docs = algorithms.advanced_rerank(query, raw_chunks)
    
    if len(reranked_docs) == 0:
        print("[DEBUG] No chunks passed reranking threshold. Skipping to generation with empty context.")
        return {"final_chunks": []}
    
    # 4. Token Budgeting
    budgeted_docs = algorithms.apply_token_budget(reranked_docs)
    
    # 5. Lost-in-the-Middle Sorting
    final_context = algorithms.lost_in_the_middle_sort(budgeted_docs)
    
    return {"final_chunks": final_context}

def retrieve_basic(state: WorkflowState):
    """
    Basic Retrieval Pipeline:
    Chỉ lấy top 3 chunks từ ChromaDB, không rerank, không budget.
    Chỉ chạy khi use_think = False.
    """
    query = state["user_query"]
    raw_chunks = retriever.retrieve_basic(query, top_k=3)
    return {"final_chunks": raw_chunks}

def generate_response(state: WorkflowState):
    """
    Node 6: Strict Generation
    Trả lời người dùng chặt chẽ dựa trên ngữ cảnh toàn văn.
    """
    query = state["user_query"]
    context_blocks = state.get("final_chunks", [])
    
    # Ghép context lại thành văn bản
    # Format: [Tài liệu i]: Điều X - Tên Văn Bản \n Nội dung: ...
    formatted_context = []
    for i, block in enumerate(context_blocks):
        meta = block.get("metadata", {})
        doc_name = meta.get("document_name", "Không rõ tên VB")
        sign_number = meta.get("sign_number", "Không rõ số hiệu")
        text = block.get("text", "")
        formatted_context.append(f"[Tài liệu {i+1}]: {doc_name} ({sign_number})\nNội dung: {text}")
        
    context_text = "\n\n".join(formatted_context)
    
    if not context_text:
        context_text = "Không tìm thấy tài liệu phù hợp trong cơ sở dữ liệu."
    
    sys_msg = SystemMessage(
        content="""Bạn là trợ lý pháp lý chuyên nghiệp. Hãy trả lời câu hỏi dựa TRÊN CƠ SỞ các tài liệu được cung cấp.
Tuyệt đối không suy diễn bịa đặt. 
Yêu cầu bắt buộc: Phải trích dẫn rõ nguồn theo định dạng "Theo Điều... Thông tư..." hoặc "[Tài liệu i]".
Nếu cơ sở dữ liệu (tài liệu tham khảo) không chứa thông tin hoặc trả về rỗng, hãy trả lời chính xác: "Dựa trên cơ sở dữ liệu hiện tại, hệ thống không tìm thấy quy định pháp luật liên quan đến vấn đề này." """
    )
    
    human_msg = HumanMessage(
        content=f"Tài liệu tham khảo:\n{context_text}\n\nCâu hỏi: {query}"
    )
    
    response = llm.invoke([sys_msg, human_msg])
    
    return {"final_response": strip_think_tags(response.content)}


# ---------------------------------------------------------
# COMPILE GRAPH
# ---------------------------------------------------------

def router(state: WorkflowState):
    """Định tuyến dựa trên cờ use_think"""
    if state.get("use_think", True):
        return "extract_metadata_hyde"
    return "retrieve_basic"

workflow = StateGraph(WorkflowState)

workflow.add_node("extract_metadata_hyde", extract_metadata_hyde)
workflow.add_node("retrieve_and_process_advanced", retrieve_and_process_advanced)
workflow.add_node("retrieve_basic", retrieve_basic)
workflow.add_node("generate_response", generate_response)

workflow.set_conditional_entry_point(
    router,
    {
        "extract_metadata_hyde": "extract_metadata_hyde",
        "retrieve_basic": "retrieve_basic"
    }
)

workflow.add_edge("extract_metadata_hyde", "retrieve_and_process_advanced")
workflow.add_edge("retrieve_and_process_advanced", "generate_response")
workflow.add_edge("retrieve_basic", "generate_response")
workflow.add_edge("generate_response", END)

app_graph = workflow.compile()
