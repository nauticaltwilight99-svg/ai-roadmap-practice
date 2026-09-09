#!/usr/bin/env python3
"""Ollama-backed execution adapter for Auto-Company."""

from __future__ import annotations

import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
GEMINI_PATH = Path(__file__).with_name("gemini-agent.py")
spec = spec_from_file_location("auto_company_gemini", GEMINI_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load shared tool dispatcher")
shared = module_from_spec(spec)
spec.loader.exec_module(shared)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file inside the project.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or replace a UTF-8 text file inside the project.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a project maintenance or development command.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}, "timeout_seconds": {"type": "integer"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search public web pages.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}},
                "required": ["query"],
            },
        },
    },
]


def select_model(prompt: str) -> str:
    """Use the fast model for chat and the larger model for deliberate work."""
    default_model = os.environ.get("OLLAMA_MODEL", "qwen3:4b").strip()
    smart_model = os.environ.get("OLLAMA_SMART_MODEL", "").strip()
    if not smart_model:
        return default_model

    normalized = prompt.lower()
    smart_keywords = (
        "проанализируй", "сравни", "спланируй", "разработай", "архитектур",
        "стратег", "коммерческ", "исследован", "продаж", "воронк",
        "создай сайт", "напиши код", "исправь код", "проверь код",
        "analyze", "compare", "plan", "architecture", "strategy",
        "research", "write code", "fix code", "create a website",
    )
    if len(prompt) >= 700 or any(keyword in normalized for keyword in smart_keywords):
        return smart_model
    return default_model


def build_messages(prompt: str) -> list[dict[str, object]]:
    """Turn the Telegram context envelope into real chat roles."""
    system = {
        "role": "system",
        "content": (
            "Ты умный русскоязычный ассистент Auto-Company. "
            "Отвечай на последний запрос пользователя, не повторяй его и не выдумывай факты. "
            "Если данных недостаточно, прямо скажи, чего не хватает, или задай один уточняющий вопрос. "
            "Для простых вопросов отвечай кратко; для рабочих задач давай конкретный план и результат. "
            "Не начинай с приветствия без просьбы пользователя. "
            "Инструменты используй только когда без них нельзя выполнить задачу."
        ),
    }
    context_marker = "Контекст диалога:\n"
    request_marker = "\n\nНовый запрос пользователя:\n"
    if context_marker not in prompt or request_marker not in prompt:
        return [system, {"role": "user", "content": prompt}]

    context, request = prompt.split(context_marker, 1)[1].split(request_marker, 1)
    messages: list[dict[str, object]] = [system]
    for row in context.splitlines():
        role, separator, content = row.partition(": ")
        if separator and role in {"user", "assistant"} and content.strip():
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": request.strip()})
    return messages


def call_ollama(messages: list[dict[str, object]], model: str) -> dict[str, object]:
    use_tools = os.environ.get("OLLAMA_ENABLE_TOOLS", "0") == "1"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": "15m",
            "think": False,
            "options": {
                "num_predict": int(os.environ.get("OLLAMA_NUM_PREDICT", "128")),
                "temperature": float(os.environ.get("OLLAMA_TEMPERATURE", "0.2")),
                "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "4096")),
            },
            **({"tools": TOOLS} if use_tools else {}),
        }
    ).encode("utf-8")
    request = Request(
        os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=int(os.environ.get("OLLAMA_TIMEOUT", "300"))) as response:
        return json.loads(response.read().decode("utf-8"))


def dispatch(name: str, arguments: dict[str, object]) -> str:
    root = shared.project_root()
    return shared.dispatch_tool(root, name, arguments)


def main() -> int:
    prompt = sys.stdin.read().strip()
    if not prompt:
        print("Ollama prompt is empty", file=sys.stderr)
        return 1
    tool_keywords = (
        "найди", "создай", "измени", "исправь", "проверь", "прочитай",
        "запиши", "сохрани", "проанализируй", "сайт", "файл", "код",
        "search", "create", "write", "fix", "check", "file",
    )
    os.environ["OLLAMA_ENABLE_TOOLS"] = (
        "1" if any(keyword in prompt.lower() for keyword in tool_keywords) else "0"
    )
    messages = build_messages(prompt)
    model = select_model(prompt)
    for _ in range(12):
        response = call_ollama(messages, model)
        message = response.get("message", {})
        if not isinstance(message, dict):
            raise RuntimeError("Ollama returned an invalid message")
        messages.append(message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            print(str(message.get("content", "")).strip())
            return 0
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name")
            arguments = function.get("arguments", {})
            if not isinstance(name, str) or not isinstance(arguments, dict):
                result = "Invalid tool call"
            else:
                result = dispatch(name, arguments)
            messages.append(
                {"role": "tool", "content": result, "tool_name": name or "unknown"}
            )
    print("Ollama tool loop exceeded its safety limit", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
