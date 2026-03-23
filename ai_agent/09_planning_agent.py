"""
Day 9: Planning Agent
- 큰 목표를 작은 단계로 나누고, 현재 단계를 저장하며 실행하는 Agent 예제
- "계획 세우기 -> 진행 -> 완료 처리 -> 다음 단계 추천" 흐름에 집중
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

import anthropic
from dotenv import load_dotenv


load_dotenv(override=True)
client = anthropic.Anthropic()

MODEL_NAME = "claude-haiku-4-5-20251001"
BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"

SYSTEM_PROMPT = """
너는 초심자용 계획형 공부 도우미 AI Agent다.
사용자의 큰 목표를 작은 단계로 나누고, 현재 무엇을 해야 하는지 정리하는 것이 목표다.

규칙:
- 사용자가 큰 목표를 말하면 create_plan을 사용하라.
- 현재 계획을 보고 싶으면 get_plan을 사용하라.
- 특정 단계를 끝냈다고 하면 complete_plan_step을 사용하라.
- 다음에 무엇을 해야 할지 묻는다면 recommend_next_plan_step을 사용하라.
- 공부 할 일을 추가해야 하면 add_task를 사용하라.
- 답변은 짧고 쉬운 한국어로 하라.
""".strip()

tools = [
    {
        "name": "create_plan",
        "description": "큰 목표를 3~5개의 작은 단계로 나눠 계획을 저장합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "사용자의 큰 목표"},
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "작은 단계 목록",
                },
            },
            "required": ["goal", "steps"],
        },
    },
    {
        "name": "get_plan",
        "description": "현재 저장된 계획을 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "complete_plan_step",
        "description": "특정 계획 단계를 완료 처리합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "step_number": {"type": "integer", "description": "완료할 단계 번호"},
            },
            "required": ["step_number"],
        },
    },
    {
        "name": "recommend_next_plan_step",
        "description": "현재 계획을 기준으로 다음 단계를 추천합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_task",
        "description": "계획과 별도로 일반 공부 할 일을 추가합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
            },
            "required": ["task"],
        },
    },
]


def memory_path(session_id: str) -> Path:
    return MEMORY_DIR / f"{session_id}.json"


def default_state() -> dict:
    return {
        "messages": [],
        "tasks": [],
        "plan": None,
    }


def load_state(session_id: str) -> dict:
    path = memory_path(session_id)
    if not path.exists():
        return default_state()
    with path.open("r", encoding="utf-8") as file:
        state = json.load(file)
    state.setdefault("messages", [])
    state.setdefault("tasks", [])
    state.setdefault("plan", None)
    return state


def save_state(session_id: str, state: dict) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with memory_path(session_id).open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def append_message(state: dict, role: str, content: str) -> None:
    state["messages"].append(
        {"role": role, "content": content, "timestamp": datetime.now().isoformat(timespec="seconds")}
    )
    state["messages"] = state["messages"][-8:]


def tool_create_plan(state: dict, goal: str, steps: list[str]) -> str:
    cleaned_steps = [step.strip() for step in steps if step.strip()][:5]
    state["plan"] = {
        "goal": goal,
        "steps": [{"step": step, "done": False} for step in cleaned_steps],
        "current_step": 1 if cleaned_steps else None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return f"계획 저장 완료: {goal}"


def tool_get_plan(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "아직 저장된 계획이 없습니다."

    lines = [f"목표: {plan['goal']}"]
    for index, item in enumerate(plan["steps"], start=1):
        status = "완료" if item["done"] else "진행 전"
        marker = " <== 현재 단계" if plan.get("current_step") == index else ""
        lines.append(f"{index}. {item['step']} [{status}]{marker}")
    return "\n".join(lines)


def tool_complete_plan_step(state: dict, step_number: int) -> str:
    plan = state.get("plan")
    if not plan:
        return "완료 처리할 계획이 없습니다."
    if step_number < 1 or step_number > len(plan["steps"]):
        return f"{step_number}번 단계는 계획에 없습니다."

    plan["steps"][step_number - 1]["done"] = True
    next_step = None
    for index, item in enumerate(plan["steps"], start=1):
        if not item["done"]:
            next_step = index
            break
    plan["current_step"] = next_step

    if next_step is None:
        return f"{step_number}번 단계 완료. 계획의 모든 단계를 끝냈습니다."
    return f"{step_number}번 단계 완료. 다음은 {next_step}번 단계입니다."


def tool_recommend_next_plan_step(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "아직 계획이 없으니 먼저 목표를 정하고 계획을 만들어보세요."

    current_step = plan.get("current_step")
    if current_step is None:
        return "현재 계획은 모두 완료되었습니다. 새 목표를 세워도 좋습니다."

    next_step = plan["steps"][current_step - 1]["step"]
    return (
        "추천 다음 단계\n"
        f"- 현재 목표: {plan['goal']}\n"
        f"- 지금 할 일: {next_step}"
    )


def tool_add_task(state: dict, task: str) -> str:
    if any(item["task"] == task for item in state["tasks"]):
        return f"이미 존재하는 할 일입니다: {task}"
    state["tasks"].append({"task": task, "done": False})
    return f"할 일 추가 완료: {task}"


def execute_tool(state: dict, name: str, inputs: dict) -> str:
    if name == "create_plan":
        return tool_create_plan(state, inputs["goal"], inputs["steps"])
    if name == "get_plan":
        return tool_get_plan(state)
    if name == "complete_plan_step":
        return tool_complete_plan_step(state, inputs["step_number"])
    if name == "recommend_next_plan_step":
        return tool_recommend_next_plan_step(state)
    if name == "add_task":
        return tool_add_task(state, inputs["task"])
    return f"알 수 없는 tool입니다: {name}"


def build_context_message(state: dict) -> str:
    plan_summary = json.dumps(state["plan"], ensure_ascii=False)
    tasks_summary = json.dumps(state["tasks"], ensure_ascii=False)
    return (
        "현재 계획 상태 요약입니다.\n"
        f"- plan: {plan_summary}\n"
        f"- tasks: {tasks_summary}\n"
    )


def run_agent(user_message: str, session_id: str = "student_planning") -> None:
    state = load_state(session_id)

    print(f"\n세션: {session_id}")
    print(f"사용자: {user_message}")
    print("=" * 60)

    append_message(state, "user", user_message)
    save_state(session_id, state)

    messages = [
        {"role": "user", "content": build_context_message(state)},
        {"role": "user", "content": user_message},
    ]

    step = 0
    while True:
        step += 1
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        print(f"[Step {step}] stop_reason: {response.stop_reason}")

        if response.stop_reason == "end_turn":
            final_text = "\n".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            ).strip()
            print(f"Claude: {final_text}")
            append_message(state, "assistant", final_text)
            save_state(session_id, state)
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                print(f"  Tool 호출: {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                result = execute_tool(state, block.name, block.input)
                save_state(session_id, state)
                print(f"  Tool 결과: {result[:140]}{'...' if len(result) > 140 else ''}")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
            messages.append({"role": "user", "content": tool_results})
            continue

        print("예상하지 못한 stop_reason입니다.")
        break


if __name__ == "__main__":
    print("=== Day 9: Planning Agent ===")
    print("큰 목표를 작은 단계로 나누고 순서대로 진행하는 예제입니다.")

    run_agent("2주 안에 파이썬 함수 기초를 익히는 계획을 세워줘.")
    run_agent("현재 계획 보여줘.")
    run_agent("1번 단계는 끝났어.")
    run_agent("지금 다음에 뭘 하면 좋을지 알려줘.")
