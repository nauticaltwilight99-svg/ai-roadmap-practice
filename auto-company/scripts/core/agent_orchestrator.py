"""Role-based orchestrator for the six-agent commercial team."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from task_store import enqueue


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEAM_CONFIG = PROJECT_ROOT / "config" / "agent_team.json"


def load_team() -> dict[str, object]:
    config = json.loads(TEAM_CONFIG.read_text(encoding="utf-8"))
    team_by_id = {role["id"]: role for role in config["team"]}
    order = config["execution"]["order"]
    if any(role_id not in team_by_id for role_id in order):
        raise ValueError("team execution order references an unknown role")
    if config["execution"]["telegram_gate"] != order[-1]:
        raise ValueError("Telegram gate must be the final role")
    return config


def create_run(request: str, chat_id: int) -> dict[str, object]:
    if not request.strip():
        raise ValueError("request is required")
    config = load_team()
    run_id = uuid.uuid4().hex
    first_role = config["execution"]["order"][0]
    payload = json.dumps(
        {
            "run_id": run_id,
            "chat_id": chat_id,
            "role": first_role,
            "request": request.strip(),
            "context": {},
            "quality_pass": False,
        },
        ensure_ascii=False,
    )
    task = enqueue(
        f"agent:{first_role}",
        payload,
        idempotency_key=f"run:{run_id}:{first_role}",
    )
    return {"run_id": run_id, "first_role": first_role, "task": task}


def next_role(current_role: str) -> str | None:
    order = load_team()["execution"]["order"]
    try:
        index = order.index(current_role)
    except ValueError as error:
        raise ValueError(f"unknown role: {current_role}") from error
    return order[index + 1] if index + 1 < len(order) else None


def advance_run(
    run_id: str,
    chat_id: int,
    request: str,
    current_role: str,
    context: dict[str, object],
) -> dict[str, object]:
    quality_round = int(context.get("quality_round", 0))
    if current_role == "quality_guardian" and context.get("quality_pass") is not True:
        if quality_round >= 2:
            raise ValueError("quality gate failed after maximum revision rounds")
        context = dict(context)
        context["quality_round"] = quality_round + 1
        context["revision_required"] = True
        following_role = "content_design"
        payload = json.dumps(
            {
                "run_id": run_id,
                "chat_id": chat_id,
                "role": following_role,
                "request": request,
                "context": context,
                "quality_pass": False,
            },
            ensure_ascii=False,
        )
        task = enqueue(
            f"agent:{following_role}",
            payload,
            idempotency_key=f"run:{run_id}:{following_role}:revision:{quality_round + 1}",
        )
        return {"completed": False, "revision": True, "next_role": following_role, "task": task}
    following_role = next_role(current_role)
    if following_role is None:
        if context.get("quality_pass") is not True:
            raise ValueError("workflow cannot reach Telegram without quality_pass=true")
        return {"completed": True, "run_id": run_id, "telegram_ready": True}
    payload = json.dumps(
        {
            "run_id": run_id,
            "chat_id": chat_id,
            "role": following_role,
            "request": request,
            "context": context,
            "quality_pass": context.get("quality_pass", False),
        },
        ensure_ascii=False,
    )
    task = enqueue(
        f"agent:{following_role}",
        payload,
        idempotency_key=f"run:{run_id}:{following_role}",
    )
    return {"completed": False, "next_role": following_role, "task": task}
