from src.rag.retriever import get_retriever

def main():
    retriever = get_retriever()

    query = "Is whey protein safe for lactose intolerance?"

    docs = retriever.invoke(query)

    print(f"\nRetrieved {len(docs)} documents\n")

    for i, doc in enumerate(docs, start=1):
        print(f"--- DOC {i} ---")
        print(doc.page_content[:400])
        print()

if __name__ == "__main__":
    main()
