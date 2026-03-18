"""
Day 5: Memory / State
- Agent는 한 번 답하고 끝나는 프로그램이 아니라, 이전 정보를 기억하며 이어서 일할 수 있어야 합니다.
- 이번 예제에서는 메모리를 세 가지로 나눕니다.
  1. messages: 최근 대화 기록
  2. facts: 사용자의 취향이나 중요한 사실
  3. tasks: 해야 할 일 목록

이 파일의 목표:
- "기억"이 왜 필요한지 이해한다.
- JSON 파일에 상태를 저장해서, 프로그램을 다시 실행해도 기억이 남는 것을 확인한다.
- LLM이 memory tool을 선택하고, Python 코드가 실제 저장/조회 작업을 수행하는 구조를 본다.

이전 단계와의 차이:
- 04_practical_tools.py는 외부 도구를 쓰는 법에 집중했다.
- 05_memory_state.py는 "이전 대화와 작업 상태를 어떻게 보관할까?"에 집중한다.
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
너는 초심자용 AI Agent 데모다.
사용자의 요청을 해결할 때 필요하면 memory tool을 사용하라.

memory 사용 원칙:
- 사용자의 취향, 선호, 반복해서 쓸 사실은 facts에 저장하라.
- 할 일이나 진행 상황은 tasks에 저장하라.
- 메모리 내용을 확인해야 할 때는 get_memory를 호출하라.
- 메모리에 없는 내용은 아는 척하지 말고 없다고 말하라.
- 답변은 짧고 쉬운 한국어로 하라.
""".strip()

tools = [
    {
        "name": "save_fact",
        "description": "사용자에 대한 중요한 사실을 저장합니다. 예: 좋아하는 도시, 관심 분야",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "사실을 구분하는 짧은 이름"},
                "value": {"type": "string", "description": "저장할 실제 내용"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "add_task",
        "description": "사용자의 할 일을 추가합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "추가할 할 일"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "complete_task",
        "description": "기존 할 일을 완료 처리합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "완료할 할 일 이름"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "get_memory",
        "description": "현재 세션의 메모리 전체를 확인합니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


def memory_path(session_id: str) -> Path:
    return MEMORY_DIR / f"{session_id}.json"


def default_state() -> dict:
    return {
        "messages": [],
        "facts": {},
        "tasks": [],
    }


def load_state(session_id: str) -> dict:
    path = memory_path(session_id)
    if not path.exists():
        return default_state()

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(session_id: str, state: dict) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = memory_path(session_id)
    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def append_message(state: dict, role: str, content: str) -> None:
    state["messages"].append(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )


def trim_messages(state: dict, limit: int = 8) -> None:
    state["messages"] = state["messages"][-limit:]


def tool_save_fact(state: dict, key: str, value: str) -> str:
    state["facts"][key] = value
    return f"fact 저장 완료: {key} = {value}"


def tool_add_task(state: dict, task: str) -> str:
    existing = next((item for item in state["tasks"] if item["task"] == task), None)
    if existing:
        return f"이미 존재하는 할 일입니다: {task}"

    state["tasks"].append({"task": task, "done": False})
    return f"할 일 추가 완료: {task}"


def tool_complete_task(state: dict, task: str) -> str:
    for item in state["tasks"]:
        if item["task"] == task:
            item["done"] = True
            return f"할 일 완료 처리: {task}"
    return f"해당 할 일을 찾지 못했습니다: {task}"


def tool_get_memory(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2)


def execute_tool(state: dict, name: str, inputs: dict) -> str:
    if name == "save_fact":
        return tool_save_fact(state, inputs["key"], inputs["value"])
    if name == "add_task":
        return tool_add_task(state, inputs["task"])
    if name == "complete_task":
        return tool_complete_task(state, inputs["task"])
    if name == "get_memory":
        return tool_get_memory(state)
    return f"알 수 없는 tool입니다: {name}"


def build_context_message(state: dict) -> str:
    facts_text = json.dumps(state["facts"], ensure_ascii=False)
    tasks_text = json.dumps(state["tasks"], ensure_ascii=False)
    recent_messages = json.dumps(state["messages"][-4:], ensure_ascii=False)
    return (
        "현재 세션 메모리 요약입니다.\n"
        f"- facts: {facts_text}\n"
        f"- tasks: {tasks_text}\n"
        f"- recent_messages: {recent_messages}\n"
    )


def run_agent(user_message: str, session_id: str = "default") -> None:
    state = load_state(session_id)

    print(f"\n세션: {session_id}")
    print(f"사용자: {user_message}")
    print("=" * 60)

    append_message(state, "user", user_message)
    trim_messages(state)
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
            text_parts = [
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            ]
            final_text = "\n".join(text_parts).strip()
            print(f"Claude: {final_text}")

            append_message(state, "assistant", final_text)
            trim_messages(state)
            save_state(session_id, state)
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                print(
                    "  Tool 호출: "
                    f"{block.name}({json.dumps(block.input, ensure_ascii=False)})"
                )
                result = execute_tool(state, block.name, block.input)
                save_state(session_id, state)
                print(f"  Tool 결과: {result}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            messages.append({"role": "user", "content": tool_results})
            continue

        print("예상하지 못한 stop_reason입니다.")
        break


if __name__ == "__main__":
    print("=== Day 5: Memory / State 예제 ===")
    print("아래 예제는 같은 session_id를 사용해서 기억이 이어지는 모습을 보여줍니다.")

    run_agent("내가 좋아하는 도시는 부산이야. 기억해줘.", session_id="student")
    run_agent("아까 내가 좋아한다고 한 도시는 뭐였지?", session_id="student")
    run_agent("오늘 할 일은 수학 숙제와 영어 단어 외우기야. 기억해줘.", session_id="student")
    run_agent("영어 단어 외우기는 끝났어. 지금 남은 할 일을 알려줘.", session_id="student")
