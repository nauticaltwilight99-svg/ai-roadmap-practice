"""Direct Telegram transport for the Auto-Company agent."""

from __future__ import annotations

import json
import os
import sqlite3
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from action_executor import execute_approved_action
from approval_store import decide, pending_for_chat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEMORY_DB = PROJECT_ROOT / ".runtime" / "telegram_memory.sqlite3"
TELEGRAM_API = "https://api.telegram.org/bot{}/{}"
MAX_TELEGRAM_MESSAGE = 4096
TELEGRAM_COMMANDS = [
    {"command": "start", "description": "Открыть меню и справку"},
    {"command": "help", "description": "Показать все команды"},
    {"command": "menu", "description": "Показать меню команд"},
    {"command": "find_leads", "description": "Запустить поиск лидов"},
    {"command": "stop_find_leads", "description": "Остановить поиск лидов"},
    {"command": "status", "description": "Показать статус поиска"},
    {"command": "reset", "description": "Очистить память диалога"},
]


def _commercial_request(text: str) -> tuple[str, str, list[str]] | None:
    parts = text.split()
    if not parts or parts[0].lower() not in {"/find_leads", "/find"}:
        return None
    city = parts[1] if len(parts) > 1 else ""
    segment = parts[2].lower() if len(parts) > 2 else "all"
    segment_aliases = {
        "dentistry": "dentistry",
        "dental": "dentistry",
        "стоматология": "dentistry",
        "стоматологии": "dentistry",
        "клиника": "dentistry",
        "клиники": "dentistry",
        "horeca": "horeca",
        "хорека": "horeca",
        "ресторан": "horeca",
        "рестораны": "horeca",
        "кафе": "horeca",
        "отель": "horeca",
        "отели": "horeca",
        "гостиница": "horeca",
        "гостиницы": "horeca",
        "all": "all",
        "все": "all",
    }
    normalized_segment = segment_aliases.get(segment)
    if not city or normalized_segment is None:
        return None
    return city, normalized_segment, parts[3:]


def _commercial_help() -> str:
    from commercial_worker import load_config

    config = load_config()
    markets = config.get("target_markets", [])
    cities = [
        str(city)
        for market in markets
        if isinstance(market, dict)
        for city in market.get("cities", [])
    ]
    city_list = ", ".join(cities)
    return (
        "Я подключён к Auto-Company.\n\n"
        "Поиск лидов:\n"
        "/find_leads <город> <ниша>\n"
        "Если нишу не указать, будут запущены все приоритетные ниши.\n\n"
        "Ниши: стоматология, клиника, horeca, ресторан, кафе, отель, гостиница, все.\n"
        f"Города: {city_list}.\n\n"
        "Примеры:\n"
        "/find_leads Минск стоматология\n"
        "/find_leads Минск horeca\n"
        "/find_leads Минск все\n"
        "/find_leads Брест все\n"
        "/find_leads Гродно стоматология\n"
        "/find_leads Гомель кафе\n"
        "/find_leads Витебск ресторан\n"
        "/find_leads Могилёв все\n"
        "/find_leads Алматы стоматология\n"
        "/find_leads Алматы horeca\n"
        "/find_leads Алматы все\n"
        "/find_leads Астана все\n"
        "/find_leads Шымкент клиника\n"
        "/find_leads Караганда ресторан\n"
        "/find_leads Актобе все\n"
        "/find_leads Атырау отель\n\n"
        "Письма всегда ждут вашего подтверждения.\n\n"
        "Команды:\n"
        "/menu — открыть меню команд\n"
        "/status — статус поиска в этом чате\n"
        "/stop_find_leads — принудительно остановить поиск\n"
        "/reset — очистить память диалога"
    )


def _stop_requested_leads(chat_id: int) -> str:
    from task_store import cancel_for_chat

    counts = cancel_for_chat(chat_id)
    total = counts["queued"] + counts["running"]
    if not total:
        return "Активных задач поиска лидов для этого чата нет."
    return (
        f"⛔ Поиск остановлен. Отменено задач: {total} "
        f"(в очереди: {counts['queued']}, выполнялось: {counts['running']})."
    )


def _requested_leads_status(chat_id: int) -> str:
    from task_store import summary_for_chat

    counts = summary_for_chat(chat_id)
    if not counts:
        return "Для этого чата ещё нет задач поиска лидов."
    labels = {
        "queued": "в очереди",
        "running": "в работе",
        "completed": "завершено",
        "failed": "ошибок",
        "cancelled": "остановлено",
    }
    details = ", ".join(
        f"{labels.get(status, status)}: {amount}"
        for status, amount in sorted(counts.items())
    )
    return f"📊 Статус поиска: {details}."


def _discover_requested_leads(chat_id: int, city: str, segment: str, extra: list[str]) -> str:
    from commercial_worker import discover_leads, load_config

    config = load_config()
    selected = [
        item for item in config["starting_niches"]
        if item.get("priority") and (segment == "all" or item.get("segment") == segment)
    ]
    if extra:
        city = " ".join([city, *extra])
    discovered = 0
    queued = 0
    for niche in selected:
        templates = niche.get("search_query_templates", [])
        for template in templates:
            results = discover_leads(
                str(niche["id"]),
                str(template).format(city=city),
                max_results=5,
                chat_id=chat_id,
            )
            discovered += len(results)
            queued += sum(1 for item in results if item.get("task", {}).get("created"))
    if not selected:
        return "Не удалось определить нишу. Используйте: /find_leads <город> <стоматология|horeca|все>"
    return (
        f"🔎 Запуск коммерческого поиска: {city}\n"
        f"Ниш: {len(selected)}; найдено: {discovered}; поставлено в исследование: {queued}.\n"
        "Письма не отправляются. После исследования готовые demo и письма придут сюда на подтверждение."
    )


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip().lstrip("\ufeff"), value.strip().strip('"').strip("'"))


def memory_db_path() -> Path:
    return Path(os.environ.get("TELEGRAM_MEMORY_DB", str(DEFAULT_MEMORY_DB))).expanduser()


def remember(chat_id: int, role: str, content: str) -> None:
    path = memory_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
            (str(chat_id), role, content[-12000:]),
        )
        connection.execute(
            "DELETE FROM messages WHERE chat_id = ? AND id NOT IN (SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT 20)",
            (str(chat_id), str(chat_id)),
        )
        connection.commit()
    finally:
        connection.close()


def recent_memory(chat_id: int) -> str:
    path = memory_db_path()
    if not path.exists():
        return ""
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT 10",
            (str(chat_id),),
        ).fetchall()
    finally:
        connection.close()
    rows.reverse()
    return "\n".join(f"{role}: {content}" for role, content in rows)


def clear_memory(chat_id: int) -> None:
    path = memory_db_path()
    if not path.exists():
        return
    connection = sqlite3.connect(path)
    try:
        connection.execute("DELETE FROM messages WHERE chat_id = ?", (str(chat_id),))
        connection.commit()
    finally:
        connection.close()


def telegram_request(token: str, method: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        TELEGRAM_API.format(token, method),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=40) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(str(result.get("description", "Telegram API error")))
    return result


def send_message(token: str, chat_id: int, text: str) -> None:
    clean_text = text.strip() or "Не удалось получить ответ от AI."
    for start in range(0, len(clean_text), MAX_TELEGRAM_MESSAGE):
        telegram_request(
            token,
            "sendMessage",
            {"chat_id": chat_id, "text": clean_text[start : start + MAX_TELEGRAM_MESSAGE]},
        )


def run_agent(prompt: str, chat_id: int) -> tuple[bool, str]:
    python_executable = os.environ.get("GEMINI_PYTHON_BIN", "python")
    agent_script = os.environ.get(
        "AI_AGENT_SCRIPT", str(PROJECT_ROOT / "scripts" / "core" / "provider-agent.py")
    )
    env = os.environ.copy()
    env["CURRENT_USER_ID"] = str(chat_id)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.setdefault("GEMINI_PROJECT_DIR", str(PROJECT_ROOT))
    env.setdefault("GEMINI_ENV_FILE", str(PROJECT_ROOT / ".env"))
    try:
        process = subprocess.run(
            [python_executable, agent_script],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=PROJECT_ROOT,
            env=env,
            timeout=int(os.environ.get("AI_REQUEST_TIMEOUT", "300")),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"AI-сервис временно недоступен: {type(error).__name__}."
    output = (process.stdout or "").strip()
    error = (process.stderr or "").strip()
    if process.returncode == 0 and output:
        return True, output
    lowered = error.lower()
    if "resource_exhausted" in lowered or "quota exceeded" in lowered:
        return False, "Лимит модели исчерпан. Попробуйте позже или подключите платную модель."
    return False, "AI-сервис не смог обработать запрос."


def allowed_chat(chat_id: int) -> bool:
    configured = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
    if not configured:
        return True
    return str(chat_id) in {item.strip() for item in configured.split(",") if item.strip()}


def handle_update(token: str, update: dict[str, object]) -> None:
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        data = callback.get("data")
        callback_id = callback.get("id")
        message = callback.get("message")
        chat = message.get("chat") if isinstance(message, dict) else None
        chat_id = chat.get("id") if isinstance(chat, dict) else None
        if isinstance(data, str) and isinstance(callback_id, str) and isinstance(chat_id, int):
            parts = data.split(":", 1)
            if len(parts) == 2 and parts[0] in {"approve", "reject"}:
                decision = decide(parts[1], "approved" if parts[0] == "approve" else "rejected")
                telegram_request(token, "answerCallbackQuery", {"callback_query_id": callback_id})
                if decision is None:
                    send_message(token, chat_id, "Это согласование уже обработано или не найдено.")
                elif decision["status"] == "approved":
                    result = execute_approved_action(decision)
                    send_message(token, chat_id, f"✅ Одобрено: {decision['title']}\n{result}")
                else:
                    send_message(token, chat_id, f"❌ Отклонено: {decision['title']}")
        return

    message = update.get("message")
    if not isinstance(message, dict):
        return
    chat = message.get("chat")
    text = message.get("text")
    if not isinstance(chat, dict) or not isinstance(text, str):
        return
    chat_id = chat.get("id")
    if not isinstance(chat_id, int) or not allowed_chat(chat_id):
        return
    text = text.strip()
    command = text.split(maxsplit=1)[0].lower()
    if command == "/reset" and text == command:
        clear_memory(chat_id)
        send_message(token, chat_id, "Память диалога очищена.")
        return
    if command in {"/start", "/help", "/menu"} and text == command:
        send_message(token, chat_id, _commercial_help())
        return
    if command in {"/stop_find_leads", "/stop_find", "/cancel_find_leads"} and text == command:
        send_message(token, chat_id, _stop_requested_leads(chat_id))
        return
    if command == "/status" and text == command:
        send_message(token, chat_id, _requested_leads_status(chat_id))
        return
    request = _commercial_request(text)
    if request is not None:
        city, segment, extra = request
        try:
            send_message(token, chat_id, _discover_requested_leads(chat_id, city, segment, extra))
        except Exception as error:
            send_message(token, chat_id, f"Не удалось запустить поиск: {type(error).__name__}.")
            print(f"[telegram] commercial discovery error for chat {chat_id}: {error}", flush=True)
        return
    if text.startswith(("/find_leads", "/find")):
        send_message(token, chat_id, "Формат: /find_leads <город> <стоматология|horeca|все>")
        return
    if not text:
        return

    history = recent_memory(chat_id)
    prompt_context = f"Telegram chat_id: {chat_id}\n"
    prompt = prompt_context + (f"Контекст диалога:\n{history}\n\nНовый запрос пользователя:\n{text}" if history else text)
    remember(chat_id, "user", text)
    ok, response = run_agent(prompt, chat_id)
    remember(chat_id, "assistant", response)
    send_message(token, chat_id, response)
    for approval in pending_for_chat(chat_id):
        send_message_with_actions(token, chat_id, approval)
    if not ok:
        print(f"[telegram] agent error for chat {chat_id}: {response}", flush=True)


def send_message_with_actions(token: str, chat_id: int, approval: dict[str, str]) -> None:
    text = f"🔎 Проверка действия\n\n{approval['title']}\nТип: {approval['action_type']}\nКому: {approval['target']}\n\n{approval['content']}"
    buttons: list[dict[str, str]] = []
    demo_marker = "Демо доступно в dashboard:"
    if demo_marker in approval["content"]:
        demo_path = approval["content"].split(demo_marker, 1)[1].splitlines()[0].strip()
        public_url = os.environ.get("PUBLIC_DASHBOARD_URL", "").strip()
        parsed_public = urlparse(public_url)
        if public_url and demo_path.startswith("/demo/") and parsed_public.scheme == "https" and parsed_public.netloc:
            buttons.append({"text": "🖥 Открыть демо", "url": urljoin(public_url.rstrip("/") + "/", demo_path.lstrip("/"))})
    target = approval["target"].strip()
    if urlparse(target).scheme in {"http", "https"}:
        buttons.append({"text": "🔗 Исходный сайт", "url": target})
    inline_keyboard: list[list[dict[str, str]]] = []
    if buttons:
        inline_keyboard.append(buttons)
    inline_keyboard.append([
        {"text": "✅ Подтвердить", "callback_data": f"approve:{approval['id']}"},
        {"text": "❌ Отклонить", "callback_data": f"reject:{approval['id']}"},
    ])
    telegram_request(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text[:MAX_TELEGRAM_MESSAGE],
            "reply_markup": {"inline_keyboard": inline_keyboard},
        },
    )


def main() -> int:
    singleton = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        singleton.bind(("127.0.0.1", 48765))
        singleton.listen(1)
    except OSError:
        print("[telegram] another polling instance is already running", flush=True)
        return 0
    load_env_file(Path(os.environ.get("TELEGRAM_ENV_FILE", str(PROJECT_ROOT / ".env"))))
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN is required", flush=True)
        return 1
    try:
        telegram_request(token, "setMyCommands", {"commands": TELEGRAM_COMMANDS})
    except (HTTPError, URLError, OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"[telegram] could not configure command menu: {type(error).__name__}: {error}", flush=True)

    offset = 0
    delay = 1
    print("[telegram] direct bot polling started", flush=True)
    while True:
        try:
            result = telegram_request(
                token,
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 25,
                    "allowed_updates": ["message", "callback_query"],
                },
            )
            delay = 1
            updates = result.get("result", [])
            if not isinstance(updates, list):
                continue
            for update in updates:
                if isinstance(update, dict):
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        offset = update_id + 1
                    handle_update(token, update)
        except (HTTPError, URLError, OSError, RuntimeError, json.JSONDecodeError) as error:
            print(f"[telegram] polling error: {type(error).__name__}: {error}", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60)


if __name__ == "__main__":
    raise SystemExit(main())
