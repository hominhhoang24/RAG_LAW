import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ChromaDB Settings
CHROMADB_PERSIST_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "legal_documents"

# Reranker & Retrieval Settings
RERANKER_MODEL_PATH = "BAAI/bge-reranker-v2-m3"
CHROMA_TOP_K = 20 # Number of chunks to retrieve from ChromaDB (Think Mode)
RERANKER_THRESHOLD = 0.3 # Minimum score for a chunk to be kept
MAX_CHUNKS = 3 # Maximum chunks to keep after Token Budgeting
MAX_CONTEXT_TOKENS = 4000 # Maximum total tokens for the context window

# LLM Settings
# We can use llama3-70b-8192 or mixtral-8x7b-32768
GROQ_MODEL_NAME = "qwen/qwen3-32b"
