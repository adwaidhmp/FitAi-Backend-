from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.langgraph.graph import build_graph

app = FastAPI(
    title="AI Fitness & Nutrition Knowledge Service",
    version="1.0.0",
)

@app.get("/")
def health_check():
    return {"status": "ok"}

# Build LangGraph ONCE at startup
graph = build_graph()


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    try:
        result = graph.invoke(
            {
                "question": question,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="AI processing failed",
        )

    return AskResponse(answer=result["answer"])
