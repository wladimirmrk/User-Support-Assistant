import json
from pathlib import Path
from typing import Dict, Any, List

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

mcp = MCPServer("SupportDataService")

def _load_users() -> List[Dict[str, Any]]:
    users_file = DATA_DIR / "users.json"
    if not users_file.exists():
        return []
    with open(users_file, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_tickets() -> List[Dict[str, Any]]:
    tickets_file = DATA_DIR / "tickets.json"
    if not tickets_file.exists():
        return []
    with open(tickets_file, "r", encoding="utf-8") as f:
        return json.load(f)

@mcp.tool()
def get_user_by_id(user_id: str) -> str:
    """Возвращает информацию о пользователе из базы данных по его ID."""
    users = _load_users()
    for user in users:
        if user.get("id", "").strip().lower() == user_id.strip().lower():
            return json.dumps(user, ensure_ascii=False, indent=2)
    return json.dumps({"error": f"Пользователь с ID '{user_id}' не найден"}, ensure_ascii=False)

@mcp.tool()
def get_ticket_by_id(ticket_id: str) -> str:
    """Возвращает информацию о тикете поддержки по его ID."""
    tickets = _load_tickets()
    for ticket in tickets:
        if ticket.get("id", "").strip().lower() == ticket_id.strip().lower():
            return json.dumps(ticket, ensure_ascii=False, indent=2)
    return json.dumps({"error": f"Тикет с ID '{ticket_id}' не найден"}, ensure_ascii=False)

@mcp.tool()
def get_user_tickets(user_id: str) -> str:
    """Возвращает список всех тикетов, созданных указанным пользователем."""
    tickets = _load_tickets()
    user_tickets = [
        t for t in tickets if t.get("user_id", "").strip().lower() == user_id.strip().lower()
    ]
    return json.dumps(user_tickets, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
