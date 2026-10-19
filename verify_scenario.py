"""
Скрипт проверки основного сценария:
1. Индексация документов и RAG семантический поиск через Ollama + ChromaDB
2. Получение данных тикета и пользователя через настоящий MCP-сервер
3. Проверка генерации ответа на вопрос: "Почему не работает авторизация?" (тикет TCK-1042)
"""

import asyncio
import sys
from pathlib import Path

# Обеспечиваем корректный вывод UTF-8 в консоли Windows
sys.stdout.reconfigure(encoding="utf-8")

from app.config import settings
from app.rag import rag_service
from app.mcp_client import fetch_mcp_context
from app.assistant import answer_user_query


async def main():
    print("=" * 60)
    print("🚀 НАЧАЛО ВЕРИФИКАЦИИ СИСТЕМЫ AI SUPPORT ASSISTANT")
    print("=" * 60)

    # 1. Проверка RAG
    print("\n[1/3] Проверка RAG-слоя (ChromaDB + Ollama nomic-embed-text):")
    chunk_count = rag_service.index_documents(force=True)
    print(f"  ✓ Документы успешно проиндексированы. Загружено чанков: {chunk_count}")

    search_query = "Почему не работает авторизация? ERR_ACCOUNT_LOCKED"
    chunks = rag_service.search(query=search_query, top_k=2)
    print(f"  ✓ Найдено релевантных чанков: {len(chunks)}")
    for i, ch in enumerate(chunks, 1):
        print(f"    - Чанк #{i} ({ch['source']} / {ch['header']}): {ch['content'][:90]}...")

    # 2. Проверка MCP
    print("\n[2/3] Проверка настоящего MCP-сервера (FastMCP stdio):")
    mcp_data = await fetch_mcp_context(ticket_id="TCK-1042")
    if mcp_data.get("ticket"):
        t = mcp_data["ticket"]
        print(f"  ✓ Тикет получен через MCP: ID={t.get('id')}, Код ошибки={t.get('error_code')}, Статус={t.get('status')}")
    else:
        print(f"  ✗ Ошибка получения тикета через MCP: {mcp_data}")

    if mcp_data.get("user"):
        u = mcp_data["user"]
        print(f"  ✓ Пользователь получен через MCP: ID={u.get('id')}, ФИО={u.get('name')}, Статус={u.get('status')}")
    else:
        print("  ✗ Пользователь не найден")

    # 3. Проверка пайплайна ассистента
    print("\n[3/3] Проверка генерации ответа:")
    print("  Вопрос: «Почему не работает авторизация?»")
    print("  Ticket ID: TCK-1042")

    result = await answer_user_query(
        question="Почему не работает авторизация?",
        ticket_id="TCK-1042",
        user_id="USR-001"
    )

    print("\n--- ОТВЕТ АССИСТЕНТА ---")
    print(result["answer"])
    print("------------------------")
    print(f"Использовано RAG чанков: {len(result.get('rag_chunks', []))}")
    print(f"Получены данные MCP: {'Да' if result.get('mcp_data', {}).get('ticket') else 'Нет'}")

    print("\n" + "=" * 60)
    print("✅ ВЕРИФИКАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
