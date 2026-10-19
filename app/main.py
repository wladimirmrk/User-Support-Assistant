from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.rag import rag_service
from app.assistant import answer_user_query

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При запуске приложения индексируем базу знаний в ChromaDB
    try:
        count = rag_service.index_documents(force=False)
        print(f"[RAG] База знаний ChromaDB готова. Загружено чанков: {count}")
    except Exception as e:
        print(f"[RAG] Внимание: ошибка индексации при старте: {e}")
    yield


app = FastAPI(
    title="AI Support Assistant",
    description="Минимальный прототип AI-ассистента поддержки (FastAPI + ChromaDB + Ollama + OpenRouter + MCP)",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class QueryRequest(BaseModel):
    question: str = Field(..., description="Вопрос пользователя")
    user_id: Optional[str] = Field(None, description="ID пользователя (например, USR-001)")
    ticket_id: Optional[str] = Field(None, description="ID тикета (например, TCK-1042)")


class QueryResponse(BaseModel):
    answer: str
    rag_chunks: list
    mcp_data: dict
    model: str


@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "AI Support Assistant API is running. Open /docs for Swagger."}


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "rag_chunks_count": rag_service.collection.count() if hasattr(rag_service, "collection") else 0
    }


@app.post("/api/ask", response_model=QueryResponse)
async def ask_assistant(req: QueryRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Вопрос не может быть пустым.")
    
    result = await answer_user_query(
        question=req.question,
        user_id=req.user_id,
        ticket_id=req.ticket_id
    )
    return result
