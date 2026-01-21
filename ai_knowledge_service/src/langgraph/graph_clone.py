from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END


# -------------------------------------------------
# GRAPH STATE
# -------------------------------------------------

class GraphState(TypedDict):
    question: str
    intent: Optional[str]
    risk: Optional[str]                 # low | medium | high
    documents: Optional[List[str]]
    safety_notice: Optional[str]
    answer: Optional[str]


# -------------------------------------------------
# NODES
# -------------------------------------------------

def classify_node(state: GraphState):
    from src.intent.classifier import classify_intent
    from src.risk.evaluator_clone import evaluate_risk

    question = state["question"]
    intent = classify_intent(question)
    risk = evaluate_risk(intent, question)

    return {
        **state,
        "intent": intent,
        "risk": risk,
    }


def safety_node(state: GraphState):
    """
    Adds soft safety notices.
    Does NOT generate final answers.
    """

    if state["risk"] == "high":
        return {
            **state,
            "safety_notice": (
                "This question involves a medical condition. "
                "The information below is general and not a substitute "
                "for professional medical advice."
            )
        }

    if state["risk"] == "medium":
        return {
            **state,
            "safety_notice": (
                "There are no safe shortcuts. "
                "The guidance below focuses on healthy, sustainable practices."
            )
        }

    return state


def retrieve_node(state: GraphState) -> GraphState:
    # 🔥 PERFORMANCE OPTIMIZATION:
    # Skip vector retrieval for general questions
    if state["intent"] == "general":
        return {
            **state,
            "documents": [],
        }

    from src.rag.retriever import get_retriever

    retriever = get_retriever()
    docs = retriever.invoke(state["question"])

    return {
        **state,
        "documents": [doc.page_content for doc in docs],
    }


def answer_node(state: GraphState) -> GraphState:
    from src.llm.client import get_llm

    llm = get_llm()

    # 🔥 PERFORMANCE OPTIMIZATION:
    # Limit number of docs + characters sent to LLM
    docs = state.get("documents", [])[:4]
    context = "\n\n".join(doc[:400] for doc in docs)

    question = state["question"]

    prompt = f"""
You are a fitness and nutrition assistant.

RULES:
- Use ONLY the information from the context
- Do NOT copy or repeat the context word-for-word
- Give a direct answer first, then a short explanation if needed
- Keep answers concise, practical, and easy to understand
- Do NOT give medical diagnosis or treatment
- If the question suggests unsafe or extreme practices, gently correct it
- Avoid long paragraphs or unnecessary details

Context:
{context}

Question:
{question}

Answer:
"""

    response = llm.invoke(prompt)

    # 🔥 PERFORMANCE OPTIMIZATION:
    # Hard cap answer length immediately
    final_answer = response.content.strip()[:900]

    # -----------------------------
    # OUTPUT CLEANUP
    # -----------------------------

    final_answer = "\n".join(
        line.strip() for line in final_answer.splitlines() if line.strip()
    )

    # -----------------------------
    # FAIL-SAFES
    # -----------------------------

    if state["risk"] == "medium" and "i don't have enough information" in final_answer.lower():
        final_answer = (
            "There are no safe shortcuts for this goal. "
            "Sustainable results come from consistent, healthy habits "
            "such as balanced nutrition, regular physical activity, "
            "and proper recovery."
        )

    if state["risk"] == "high" and "i don't have enough information" in final_answer.lower():
        final_answer = (
            "General nutrition and lifestyle guidance can be followed safely, "
            "but individual medical conditions require personalized advice "
            "from a qualified healthcare professional."
        )

    # -----------------------------
    # SAFETY NOTICE MERGE
    # -----------------------------

    if state.get("safety_notice"):
        final_answer = (
            f"⚠️ Note:\n{state['safety_notice']}\n\n{final_answer}"
        )

    return {
        **state,
        "answer": final_answer,
    }


# -------------------------------------------------
# ROUTING LOGIC
# -------------------------------------------------

def safety_router(state: GraphState):
    """
    Currently we do not block any questions.
    All continue to retrieval.
    """
    return "retrieve"


# -------------------------------------------------
# GRAPH BUILDER
# -------------------------------------------------

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("classify", classify_node)
    graph.add_node("safety", safety_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("classify")

    graph.add_edge("classify", "safety")

    graph.add_conditional_edges(
        "safety",
        safety_router,
        {
            "retrieve": "retrieve",
        },
    )

    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


# -------------------------------------------------
# LOCAL TEST
# -------------------------------------------------

if __name__ == "__main__":
    app = build_graph()

    tests = [
        "hi",
        "how to reduce weight fast",
        "protein powder daily safe?",
        "gym daily ok or not",
        "i have diabetes can i take protein powder",
    ]

    for q in tests:
        result = app.invoke({"question": q})
        print("\nQUESTION:", q)
        print("ANSWER:\n", result["answer"])
