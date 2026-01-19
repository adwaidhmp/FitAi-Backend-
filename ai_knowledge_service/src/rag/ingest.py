import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DOCS_PATH = os.path.join(BASE_DIR, "data", "docs")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "data", "vector_db")
COLLECTION_NAME = "fitness_docs"


def ingest_documents():
    # 🔥 SMALL OPTIMIZATION:
    # If vector DB already exists, don’t rebuild every time
    if os.path.exists(VECTOR_DB_PATH) and os.listdir(VECTOR_DB_PATH):
        print("⚠️ Vector DB already exists. Delete it if you want to re-ingest.")
        return

    documents = []

    for file in os.listdir(DOCS_PATH):
        if file.endswith(".txt"):
            loader = TextLoader(
                os.path.join(DOCS_PATH, file),
                encoding="utf-8"
            )
            documents.extend(loader.load())

    # 🔥 SMALL OPTIMIZATION:
    # Slightly smaller chunks = better retrieval + faster prompts
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
    )

    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(VECTOR_DB_PATH),
        collection_name=COLLECTION_NAME,
    )

    print("✅ Vector DB created successfully")


if __name__ == "__main__":
    ingest_documents()
