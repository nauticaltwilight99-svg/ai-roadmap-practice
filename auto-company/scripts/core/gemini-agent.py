#!/usr/bin/env python3
"""Headless Gemini adapter for Auto-Company."""

import os
import subprocess
import sys
from pathlib import Path

from google import genai
from google.genai import types

from approval_store import create_approval
from approval_store import decide
from action_executor import execute_approved_action
from calculator import calculate
from metrics_store import get_metrics, write_metric
from web_search import search_web


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(name, value)


def normalize_path(raw_path: str) -> Path:
    candidate = raw_path.strip()
    if not candidate:
        return Path(".")
    if candidate.startswith("/mnt/") and len(candidate) > 6:
        drive = candidate[5].upper()
        return Path(f"{drive}:{candidate[6:].replace('/', chr(92))}")
    if len(candidate) >= 3 and candidate[1] == ":" and candidate[2] in ("\\", "/"):
        return Path(candidate)
    return Path(candidate)


def project_root() -> Path:
    raw_root = os.environ.get(
        "GEMINI_PROJECT_DIR",
        r"C:\Users\Liza\Desktop\AIProjects\Auto-Company-main",
    )
    return normalize_path(raw_root).resolve()


def safe_path(root: Path, raw_path: str) -> Path:
    target = (root / raw_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("path must stay inside the Auto-Company project")
    return target


def read_file(root: Path, path: str) -> str:
    target = safe_path(root, path)
    return target.read_text(encoding="utf-8")


def write_file(root: Path, path: str, content: str) -> str:
    if os.environ.get("AUTO_APPROVE_SAFE", "0") == "1":
        normalized = path.replace("\\", "/").lower()
        if normalized == ".env" or normalized.startswith(".env."):
            return "blocked by AUTO_APPROVE_SAFE: secrets files require manual approval"
    target = safe_path(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {target.relative_to(root)}"


def run_command(root: Path, command: str, timeout_seconds: int = 120) -> str:
    if os.environ.get("AUTO_APPROVE_SAFE", "0") == "1":
        lowered = command.lower()
        blocked_patterns = (
            "rm -rf",
            "git reset --hard",
            "git clean -fd",
            "format ",
            "shutdown",
            "restart-computer",
            "stop-computer",
            "curl | sh",
            "wget | sh",
        )
        if any(pattern in lowered for pattern in blocked_patterns):
            return "blocked by AUTO_APPROVE_SAFE: command requires manual approval"
    completed = subprocess.run(
        command,
        cwd=root,
        shell=True,
        capture_output=True,
        text=True,
        timeout=max(1, min(timeout_seconds, 600)),
    )
    output = (completed.stdout + completed.stderr).strip()
    return f"exit_code={completed.returncode}\n{output}"[-12000:]


def tool_definitions() -> list[types.Tool]:
    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="read_file",
                    description="Read a UTF-8 text file inside the project.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                ),
                types.FunctionDeclaration(
                    name="write_file",
                    description="Create or replace a UTF-8 text file inside the project.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                ),
                types.FunctionDeclaration(
                    name="run_command",
                    description="Run a project maintenance or development command.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "timeout_seconds": {"type": "integer"},
                        },
                        "required": ["command"],
                    },
                ),
                types.FunctionDeclaration(
                    name="web_search",
                    description="Search public web pages and return concise titled results with URLs.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "max_results": {"type": "integer"},
                        },
                        "required": ["query"],
                    },
                ),
                types.FunctionDeclaration(
                    name="calculator",
                    description="Perform exact arithmetic. Pass only a numeric expression.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {"expression": {"type": "string"}},
                        "required": ["expression"],
                    },
                ),
                types.FunctionDeclaration(
                    name="log_metric",
                    description="Store a numeric personal metric such as health, finance, sport, work, mood, food, or learning.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "metric_name": {"type": "string"},
                            "value": {"type": "number"},
                            "unit": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["category", "metric_name", "value"],
                    },
                ),
                types.FunctionDeclaration(
                    name="get_metrics",
                    description="Read recent stored personal metrics, optionally filtered by category.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "limit": {"type": "integer"},
                        },
                        "required": [],
                    },
                ),
                types.FunctionDeclaration(
                    name="queue_external_action",
                    description="Create a draft external action for user approval before contacting a person, company, marketplace, or service.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {
                            "chat_id": {"type": "integer"},
                            "action_type": {"type": "string"},
                            "target": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["chat_id", "action_type", "target", "title", "content"],
                    },
                ),
            ]
        )
    ]


def dispatch_tool(root: Path, name: str, args: dict[str, object]) -> str:
    try:
        if name == "read_file":
            return read_file(root, str(args["path"]))
        if name == "write_file":
            return write_file(root, str(args["path"]), str(args["content"]))
        if name == "run_command":
            return run_command(root, str(args["command"]), int(args.get("timeout_seconds", 120)))
        if name == "web_search":
            return search_web(str(args["query"]), int(args.get("max_results", 5)))
        if name == "calculator":
            return calculate(str(args["expression"]))
        if name == "log_metric":
            return write_metric(
                str(args["category"]),
                str(args["metric_name"]),
                float(args["value"]),
                str(args.get("unit", "")),
                str(args.get("note", "")),
            )
        if name == "get_metrics":
            return get_metrics(str(args.get("category", "")), int(args.get("limit", 20)))
        if name == "queue_external_action":
            action = {
                "chat_id": int(args["chat_id"]),
                "action_type": str(args["action_type"]),
                "target": str(args["target"]),
                "title": str(args["title"]),
                "content": str(args["content"]),
            }
            approval_id = create_approval(**action)
            if action["action_type"] == "crm" and os.environ.get("AUTO_APPROVE_CRM", "0") == "1":
                approved = decide(approval_id, "approved")
                if approved is None:
                    return "CRM approval could not be completed"
                return f"CRM action auto-approved: {execute_approved_action(approved)}"
            return f"Черновик поставлен в очередь согласования: {approval_id}"
        return f"unknown tool: {name}"
    except Exception as error:
        return f"tool error: {type(error).__name__}: {error}"


def main() -> int:
    env_file = os.environ.get(
        "GEMINI_ENV_FILE",
        "/mnt/c/Users/Liza/Desktop/AIProjects/ai-roadmap-practice/.env",
    )
    load_env_file(normalize_path(env_file))

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY or GOOGLE_API_KEY is required", file=sys.stderr)
        return 1
    if os.environ.get("GEMINI_API_KEY"):
        os.environ.pop("GOOGLE_API_KEY", None)

    prompt = sys.stdin.read()
    if not prompt.strip():
        print("Gemini prompt is empty", file=sys.stderr)
        return 1

    model = os.environ.get("MODEL") or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
    root = project_root()
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        tools=tool_definitions(),
        system_instruction=(
            "You are the execution engine for Auto-Company. Work decisively. "
            "Use the provided tools to inspect and change files inside the project. "
            "Use log_metric and get_metrics for the life_metrics data contract imported from n8n. "
            "Use calculator for exact arithmetic instead of estimating. "
            "Never contact external parties directly. For any external action, use queue_external_action and wait for user approval. "
            "Automatic safe mode is enabled: do not attempt blocked destructive commands or secret-file writes. "
            "Keep memories/consensus.md updated and report completed work."
        ),
    )
    contents: list[object] = [prompt]
    text = ""
    for _ in range(20):
        try:
            response = client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except Exception as error:
            print(f"Gemini API error: {type(error).__name__}: {error}", file=sys.stderr)
            return 1
        if response.candidates:
            contents.append(response.candidates[0].content)
        function_calls = []
        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                if part.function_call:
                    function_calls.append(part.function_call)
                if part.text:
                    text += part.text
        if not function_calls:
            break
        response_parts = []
        for call in function_calls:
            result = dispatch_tool(root, call.name, dict(call.args or {}))
            response_parts.append(
                types.Part.from_function_response(
                    name=call.name,
                    response={"result": result},
                )
            )
        contents.append(types.Content(role="user", parts=response_parts))
    sys.stdout.write(text)
    if text and not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())