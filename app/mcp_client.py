import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = str(BASE_DIR / "mcp_server" / "server.py")


async def fetch_mcp_context(user_id: Optional[str] = None, ticket_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Выполняет реальный RPC-запрос к MCP-серверу через stdio и получает данные
    о пользователе и/или тикете.
    """
    result_context = {
        "user": None,
        "ticket": None,
        "user_tickets": [],
        "context_text": ""
    }

    if not user_id and not ticket_id:
        return result_context

    params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Если передан ticket_id, запрашиваем тикет
                if ticket_id:
                    ticket_res = await session.call_tool("get_ticket_by_id", {"ticket_id": ticket_id.strip()})
                    if ticket_res.content and len(ticket_res.content) > 0:
                        raw_ticket = ticket_res.content[0].text
                        try:
                            t_data = json.loads(raw_ticket)
                            if "error" not in t_data:
                                result_context["ticket"] = t_data
                                # Если в тикете есть user_id, а user_id не был передан явно — подтягиваем его
                                if not user_id and t_data.get("user_id"):
                                    user_id = t_data.get("user_id")
                        except Exception:
                            pass

                # Если есть user_id, запрашиваем пользователя и его тикеты
                if user_id:
                    user_res = await session.call_tool("get_user_by_id", {"user_id": user_id.strip()})
                    if user_res.content and len(user_res.content) > 0:
                        raw_user = user_res.content[0].text
                        try:
                            u_data = json.loads(raw_user)
                            if "error" not in u_data:
                                result_context["user"] = u_data
                        except Exception:
                            pass

                    # Также запросим список всех тикетов пользователя
                    if not result_context["ticket"]:
                        user_tickets_res = await session.call_tool("get_user_tickets", {"user_id": user_id.strip()})
                        if user_tickets_res.content and len(user_tickets_res.content) > 0:
                            try:
                                ut_data = json.loads(user_tickets_res.content[0].text)
                                if isinstance(ut_data, list):
                                    result_context["user_tickets"] = ut_data
                            except Exception:
                                pass

    except Exception as e:
        result_context["error"] = f"Ошибка связи с MCP-сервером: {e}"

    # Формируем читаемый блок контекста для LLM
    parts = []
    if result_context["ticket"]:
        t = result_context["ticket"]
        parts.append(
            f"Данные тикета [{t.get('id')}]:\n"
            f"- Тема: {t.get('title')}\n"
            f"- Описание: {t.get('description')}\n"
            f"- Код ошибки: {t.get('error_code') or 'Не указан'}\n"
            f"- Статус тикета: {t.get('status')}\n"
            f"- Приоритет: {t.get('priority')}"
        )
    if result_context["user"]:
        u = result_context["user"]
        parts.append(
            f"Данные пользователя [{u.get('id')}]:\n"
            f"- ФИО: {u.get('name')}\n"
            f"- Email: {u.get('email')}\n"
            f"- Компания: {u.get('company')}\n"
            f"- Статус аккаунта: {u.get('status')}\n"
            f"- Неудачных попыток входа: {u.get('failed_login_attempts')}\n"
            f"- 2FA включена: {'Да' if u.get('2fa_enabled') else 'Нет'}"
        )

    result_context["context_text"] = "\n\n".join(parts)
    return result_context
