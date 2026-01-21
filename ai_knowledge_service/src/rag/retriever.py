from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parents[2]
VECTOR_DB_PATH = BASE_DIR / "data" / "vector_db"
COLLECTION_NAME = "fitness_docs"

# 🔥 CREATE ONCE (THIS IS THE SPEED FIX)
_embeddings = HuggingFaceEmbeddings(
    model_name="/app/models/all-MiniLM-L6-v2"
)

_vectordb = Chroma(
    persist_directory=str(VECTOR_DB_PATH),
    collection_name=COLLECTION_NAME,
    embedding_function=_embeddings,
)

_retriever = _vectordb.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3},
)


def get_retriever():
    # 🔥 REUSE, DO NOT RECREATE
    return _retriever
