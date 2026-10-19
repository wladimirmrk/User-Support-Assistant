from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI

from app.config import settings
from app.rag import rag_service
from app.mcp_client import fetch_mcp_context

SYSTEM_PROMPT = """Ты — вежливый и профессиональный AI-ассистент службы технической поддержки сервиса CloudDesk.
Твоя задача — предоставить точный, исчерпывающий и персонализированный ответ пользователю на основе официальной документации и контекста его тикета/профиля.

ПРАВИЛА:
1. Отвечай строго на основе предоставленных фрагментов документации (RAG) и данных тикета/пользователя (MCP).
2. Если в тикете или профиле пользователя указан код ошибки или статус (например, ERR_ACCOUNT_LOCKED, статус locked), обязательно свяжи причину проблемы с этими данными и дай четкие пошаговые инструкции решения.
3. ВАЖНО: Если в предоставленной документации и контексте нет необходимой информации для ответа на вопрос пользователя, ЧЕСТНО СООБЩИ ОБ ЭТОМ. Не выдумывай факты и процедуры, которых нет в документации.
4. Отвечай на русском языке, структурированно и доброжелательно.
"""


def _get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY or "missing_key",
    )


async def answer_user_query(
    question: str,
    user_id: Optional[str] = None,
    ticket_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Основной пайплайн обработки запроса:
    1. Получение контекста тикета и пользователя через настоящий MCP-сервер.
    2. Поиск релевантных чанков документации в ChromaDB (RAG).
    3. Генерация ответа через LLM OpenRouter на основе RAG и MCP данных.
    """
    # 1. MCP Context
    mcp_data = await fetch_mcp_context(user_id=user_id, ticket_id=ticket_id)
    mcp_text = mcp_data.get("context_text", "").strip()

    # 2. RAG Search
    # Формируем расширенный поисковый запрос, если в тикете есть код ошибки
    search_query = question.strip()
    ticket_obj = mcp_data.get("ticket")
    if ticket_obj and ticket_obj.get("error_code"):
        search_query = f"{search_query} {ticket_obj.get('error_code')}"
    elif ticket_obj and ticket_obj.get("title"):
        search_query = f"{search_query} {ticket_obj.get('title')}"

    rag_chunks = rag_service.search(query=search_query, top_k=3)

    # Собираем текстовый блок RAG
    rag_text_parts = []
    for idx, chunk in enumerate(rag_chunks, 1):
        rag_text_parts.append(
            f"--- Документ {idx} ({chunk.get('source')} / {chunk.get('header')}):\n{chunk.get('content')}"
        )
    rag_text = "\n\n".join(rag_text_parts) if rag_text_parts else "Релевантных документов не найдено."

    # Проверяем наличие ключа API
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        return {
            "answer": (
                "⚠️ Ошибка конфигурации: в файле `.env` не указан действующий `OPENROUTER_API_KEY`.\n\n"
                "Пожалуйста, добавьте ваш ключ OpenRouter в файл `.env`:\n"
                "```env\nOPENROUTER_API_KEY=sk-or-v1-...\n```\n"
                "Контекст MCP и чанки RAG успешно получены и готовы к обработке."
            ),
            "rag_chunks": rag_chunks,
            "mcp_data": mcp_data,
            "model": settings.LLM_MODEL
        }

    # 3. Формируем контекст для LLM
    user_prompt = f"""КОНТЕКСТ ИЗ СИСТЕМЫ ТИКЕТОВ И ПОЛЬЗОВАТЕЛЕЙ (MCP):
{mcp_text if mcp_text else "Данные тикета/пользователя не указаны."}

ФРАГМЕНТЫ ДОКУМЕНТАЦИИ И FAQ (RAG):
{rag_text}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}
"""

    client = _get_openai_client()

    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
        )
        answer = response.choices[0].message.content or "Ответ пуст."
    except Exception as e:
        answer = f"Ошибка при обращении к OpenRouter API ({settings.LLM_MODEL}): {e}"

    return {
        "answer": answer,
        "rag_chunks": rag_chunks,
        "mcp_data": mcp_data,
        "model": settings.LLM_MODEL
    }
