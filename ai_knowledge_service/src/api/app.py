from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel

from src.langgraph.graph import build_graph #WITH ML MODEL TO PREDICT INTENT

#from src.langgraph.graph_clone import build_graph #WTHOUT ML MODEL TO PREDICT INTENT 

app = FastAPI(
    title="AI Fitness & Nutrition Knowledge Service",
    version="1.0.0",
)

# --------------------------------
# ROUTER WITH BASE URL
# --------------------------------

router = APIRouter(
    prefix="/api/v1/ai",   #base url
    tags=["AI"],
)

# Build LangGraph ONCE at startup
graph = build_graph()


# --------------------------------
# SCHEMAS
# --------------------------------

class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


# --------------------------------
# ROUTES
# --------------------------------

@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/ask", response_model=AskResponse)
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
        # 🔥 TEMP DEBUG
        print("🔥 AI ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    return AskResponse(answer=result["answer"])

# --------------------------------
# REGISTER ROUTER
# --------------------------------

app.include_router(router)
