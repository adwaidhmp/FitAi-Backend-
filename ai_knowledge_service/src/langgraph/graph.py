from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END


# -------------------------------------------------
# GRAPH STATE
# -------------------------------------------------

class GraphState(TypedDict):
    question: str
    intent: Optional[str]
    confidence: Optional[float]
    risk: Optional[str]                 # low | medium | high
    documents: Optional[List[str]]
    safety_notice: Optional[str]
    answer: Optional[str]


# -------------------------------------------------
# NODES
# -------------------------------------------------

def classify_node(state: GraphState) -> GraphState:
    """
    Uses the trained ML intent classifier + risk evaluator.
    """

    from src.intent.predictor import predict_intent
    from src.risk.evaluator import evaluate_risk

    question = state["question"]

    intent, confidence = predict_intent(question)

    # 🔥 Confidence fallback
    if confidence < 0.3:
        intent = "general"

    risk = evaluate_risk(intent, question)

    return {
        **state,
        "intent": intent,
        "confidence": confidence,
        "risk": risk,
    }


def safety_node(state: GraphState) -> GraphState:
    """
    Adds soft safety notices only.
    Does NOT block or answer.
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


def chitchat_node(state: GraphState) -> GraphState:
    """
    Fast exit for casual conversation.
    No RAG. No LLM.
    """

    return {
        **state,
        "answer": "Hey 👋 How can I help you with fitness or nutrition today?"
    }


def retrieve_node(state: GraphState) -> GraphState:
    """
    Retrieves relevant documents for RAG.
    Skips retrieval for general questions.
    """

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
    """
    Generates the final grounded answer using the LLM.
    """

    from src.llm.client import get_llm

    llm = get_llm()

    docs = state.get("documents", [])[:4]
    context = "\n\n".join(doc[:400] for doc in docs)

    question = state["question"]

    prompt = f"""
You are a fitness and nutrition assistant.

RULES:
- Use ONLY the information from the context
- Do NOT copy or repeat the context word-for-word
- Give a direct answer first
- Keep answers concise and practical
- Do NOT diagnose or prescribe
- Gently correct unsafe or extreme ideas
- Avoid long paragraphs

Context:
{context}

Question:
{question}

Answer:
"""

    response = llm.invoke(prompt)

    final_answer = response.content.strip()[:900]

    # Cleanup formatting
    final_answer = "\n".join(
        line.strip() for line in final_answer.splitlines() if line.strip()
    )

    # Fail-safes
    if state["risk"] == "medium" and "don't have enough" in final_answer.lower():
        final_answer = (
            "There are no safe shortcuts. Sustainable results come from "
            "balanced nutrition, regular physical activity, and proper recovery."
        )

    if state["risk"] == "high" and "don't have enough" in final_answer.lower():
        final_answer = (
            "General lifestyle guidance can be followed safely, "
            "but medical conditions require personalized advice "
            "from a qualified healthcare professional."
        )

    # Merge safety notice
    if state.get("safety_notice"):
        final_answer = (
            f"⚠️ Note:\n{state['safety_notice']}\n\n{final_answer}"
        )

    return {
        **state,
        "answer": final_answer,
    }


# -------------------------------------------------
# ROUTER
# -------------------------------------------------

def safety_router(state: GraphState) -> str:
    """
    Routes chitchat away from RAG + LLM.
    """

    if state["intent"] == "chitchat":
        return "chitchat"

    return "retrieve"


# -------------------------------------------------
# GRAPH BUILDER
# -------------------------------------------------

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("classify", classify_node)
    graph.add_node("safety", safety_node)
    graph.add_node("chitchat", chitchat_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("classify")

    graph.add_edge("classify", "safety")

    graph.add_conditional_edges(
        "safety",
        safety_router,
        {
            "chitchat": "chitchat",
            "retrieve": "retrieve",
        },
    )

    graph.add_edge("chitchat", END)
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
        print("INTENT:", result["intent"], "| CONF:", result["confidence"])
        print("ANSWER:\n", result["answer"])
