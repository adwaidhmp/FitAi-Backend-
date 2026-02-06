from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END


# =================================================
# GRAPH STATE
# =================================================

class GraphState(TypedDict):
    question: str
    intent: Optional[str]
    confidence: Optional[float]

    risk: Optional[str]                 # low | medium | high
    documents: Optional[List[str]]

    safety_notice: Optional[str]
    answer: Optional[str]


# =================================================
# NODE 1 — INTENT CLASSIFICATION (ML MODEL)
# =================================================

def classify_node(state: GraphState) -> GraphState:
    """
    Uses your trained ML intent classifier + risk evaluator.
    """

    from src.intent.predictor import predict_intent
    from src.risk.evaluator import evaluate_risk

    question = state["question"].strip()

    intent, confidence = predict_intent(question)

    # ✅ Smart fallback:
    # If model is unsure, do NOT answer random topics.
    if confidence < 0.35:
        if len(question.split()) <= 3:
            intent = "chitchat"
        else:
            intent = "out_of_scope"

    risk = evaluate_risk(intent, question)

    return {
        **state,
        "intent": intent,
        "confidence": confidence,
        "risk": risk,
    }


# =================================================
# NODE 2 — SAFETY NOTICE (SOFT)
# =================================================

def safety_node(state: GraphState) -> GraphState:
    """
    Adds soft disclaimers only.
    Does NOT block answers.
    """

    if state["risk"] == "high":
        return {
            **state,
            "safety_notice": (
                "This involves a medical condition. "
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


# =================================================
# NODE 3 — CHITCHAT (LLM BASED)
# =================================================

def chitchat_node(state: GraphState) -> GraphState:
    """
    Handles greetings, thanks, casual messages.
    Uses LLM for natural responses.
    Must NOT answer unrelated questions.
    """

    from src.llm.client import get_llm

    llm = get_llm()
    question = state["question"].strip()

    prompt = f"""
You are a friendly Fitness & Nutrition assistant.

TASK:
- Reply naturally ONLY to greetings or casual conversation.
- Keep it short (1–2 lines).
- Do NOT answer unrelated or technical questions.
- If user asks something outside fitness/nutrition, politely redirect.

Examples:
User: Good morning
Assistant: Good morning ☀️ How can I help with fitness or nutrition today?

User: Thanks
Assistant: You're welcome 😊

User: What is Python?
Assistant: I focus on fitness and nutrition. Ask me about workouts or diet 💪🥗

User message: "{question}"

Assistant response:
"""

    response = llm.invoke(prompt)

    return {
        **state,
        "answer": response.content.strip()
    }


# =================================================
# NODE 4 — OUT OF SCOPE (HARD BLOCK)
# =================================================

def out_of_scope_node(state: GraphState) -> GraphState:
    """
    Blocks all non-fitness/nutrition questions.
    No LLM allowed here.
    """

    return {
        **state,
        "answer": (
            "I’m a Fitness & Nutrition assistant 💪🥗\n\n"
            "I can help with:\n"
            "• Workouts & gym plans\n"
            "• Weight loss & muscle gain\n"
            "• Protein, calories, healthy diet\n"
            "• Sustainable fitness habits\n\n"
            "Please ask something related to fitness or nutrition."
        )
    }


# =================================================
# NODE 5 — RETRIEVAL (RAG)
# =================================================

def retrieve_node(state: GraphState) -> GraphState:
    """
    Retrieves relevant docs ONLY for fitness/nutrition intents.
    """

    allowed_intents = ["fitness", "nutrition", "medical"]

    if state["intent"] not in allowed_intents:
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


# =================================================
# NODE 6 — FINAL ANSWER (LLM GROUNDED)
# =================================================

def answer_node(state: GraphState) -> GraphState:
    """
    Generates final answer using LLM + retrieved context.
    Prevents hallucination when docs are missing.
    """

    docs = state.get("documents", [])

    # ✅ Stop hallucinations
    if not docs:
        return {
            **state,
            "answer": (
                "I couldn’t find reliable fitness/nutrition context for that.\n"
                "Try asking about workouts, diet, protein, calories, or muscle gain."
            )
        }

    from src.llm.client import get_llm

    llm = get_llm()

    context = "\n\n".join(doc[:400] for doc in docs[:4])
    question = state["question"]

    prompt = f"""
You are a professional fitness and nutrition assistant.

RULES:
- Use ONLY the context below
- Give a direct practical answer first
- Keep it short and clear
- Do NOT diagnose or prescribe

Context:
{context}

Question:
{question}

Answer:
"""

    response = llm.invoke(prompt)
    final_answer = response.content.strip()[:900]

    # Merge safety notice if present
    if state.get("safety_notice"):
        final_answer = (
            f"⚠️ Note:\n{state['safety_notice']}\n\n{final_answer}"
        )

    return {
        **state,
        "answer": final_answer,
    }


# =================================================
# ROUTER — MAIN CONTROL
# =================================================

def main_router(state: GraphState) -> str:
    """
    Controls routing based on intent.
    """

    if state["intent"] == "chitchat":
        return "chitchat"

    if state["intent"] == "out_of_scope":
        return "out_of_scope"

    return "retrieve"


# =================================================
# GRAPH BUILDER
# =================================================

def build_graph():
    graph = StateGraph(GraphState)

    # Nodes
    graph.add_node("classify", classify_node)
    graph.add_node("safety", safety_node)

    graph.add_node("chitchat", chitchat_node)
    graph.add_node("out_of_scope", out_of_scope_node)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("answer", answer_node)

    # Entry point
    graph.set_entry_point("classify")

    # Flow
    graph.add_edge("classify", "safety")

    graph.add_conditional_edges(
        "safety",
        main_router,
        {
            "chitchat": "chitchat",
            "out_of_scope": "out_of_scope",
            "retrieve": "retrieve",
        },
    )

    graph.add_edge("chitchat", END)
    graph.add_edge("out_of_scope", END)

    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


# =================================================
# LOCAL TEST
# =================================================

if __name__ == "__main__":
    app = build_graph()

    tests = [
        "good morning",
        "thanks",
        "what is python",
        "how much protein should I eat daily?",
        "best workout for fat loss",
        "i have diabetes can i take whey protein?",
    ]

    for q in tests:
        result = app.invoke({"question": q})
        print("\nQUESTION:", q)
        print("INTENT:", result["intent"], "| CONF:", result["confidence"])
        print("ANSWER:\n", result["answer"])
