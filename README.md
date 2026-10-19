# AI Support Assistant (FastAPI + ChromaDB + Ollama + OpenRouter + MCP)

Минимальный рабочий прототип AI-ассистента службы технической поддержки для SaaS-платформы CloudDesk.

---

## 🌟 Возможности и архитектура

- **База знаний (Markdown)**: Документация (`docs/product_guide.md`) и FAQ (`docs/faq.md`) с описанием ошибок авторизации (`ERR_ACCOUNT_LOCKED`, `ERR_2FA_FAILED`), политик безопасности и разблокировки.
- **RAG на ChromaDB + Ollama**: Векторизация документов локальной моделью `nomic-embed-text:latest` через Ollama API и семантический поиск чанков под каждый входящий запрос.
- **Настоящий MCP-сервер (`mcp_server/server.py`)**: Отдельный процесс на базе официального SDK `mcp` (`FastMCP`/`MCPServer`), предоставляющий инструменты `get_ticket_by_id`, `get_user_by_id`, `get_user_tickets` по протоколу JSON-RPC (stdio transport). Никакого прямого чтения JSON в основном приложении!
- **Генерация ответов**: Модель `nvidia/nemotron-3-ultra-550b-a55b:free` через OpenRouter API (`https://openrouter.ai/api/v1`).
- **Веб-интерфейс**: Простой и адаптивный UI на FastAPI (`static/index.html`) с кнопками быстрого тестирования сценариев и просмотром использованного RAG/MCP контекста.

---

## 📋 Требования

- Python 3.10+
- Запущенный локальный сервис [Ollama](https://ollama.com/) с моделью `nomic-embed-text:latest`:
  ```bash
  ollama pull nomic-embed-text:latest
  ```
- Бесплатный API-ключ OpenRouter (получить на [openrouter.ai](https://openrouter.ai/keys)).

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Скопируйте шаблон `.env.example` в `.env` (или отредактируйте созданный `.env`):

```bash
cp .env.example .env
```

В файле `.env` укажите ваш ключ OpenRouter:

```env
OPENROUTER_API_KEY=sk-or-v1-ваш_настоящий_ключ
LLM_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text:latest
CHROMA_PERSIST_DIR=./chroma_data
```

### 3. Автоматическая проверка компонентов

Запустите скрипт сквозной проверки RAG и MCP:

```bash
python verify_scenario.py
```

### 4. Запуск веб-сервера

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

После запуска откройте в браузере: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🧪 Проверка основного сценария

1. В веб-интерфейсе нажмите кнопку:
   **«🎯 Основной сценарий (Ошибка авторизации TCK-1042)»**
2. Поля автоматически заполнятся:
   - **Вопрос**: `Почему не работает авторизация?`
   - **ID тикета**: `TCK-1042`
   - **ID пользователя**: `USR-001`
3. Нажмите кнопку **«Сгенерировать ответ ассистента»**.
4. **Результат**:
   - Ассистент через **MCP** получит данные тикета `TCK-1042` (ошибка `ERR_ACCOUNT_LOCKED`, статус `locked` у пользователя Ивана Смирнова).
   - Через **RAG** найдет статью FAQ с причинами 5 неудачных попыток ввода пароля.
   - Выдаст понятный персонализированный ответ со способами решения (подождать 15 минут, восстановить пароль по ссылке или запросить разблокировку администратором).
   - В блоках внизу можно развернуть и посмотреть точные фрагменты документов ChromaDB и сырые данные ответа MCP.
