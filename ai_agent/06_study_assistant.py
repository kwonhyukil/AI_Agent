"""
Day 6: Mini Project - Study Assistant
- 04_practical_tools.py의 실용 도구 일부를 사용
- 05_memory_state.py의 memory 구조를 사용
- "도구 + 반복 + 기억"을 하나로 합친 미니 프로젝트

이 파일의 목표:
- 지금까지 배운 내용을 한 번에 묶어 본다.
- Agent가 사용자의 공부 정보와 할 일을 기억하게 만든다.
- 필요하면 메모리를 파일로 정리해서 저장하게 만든다.

핵심 아이디어:
- facts: 사용자의 선호 정보 저장
- tasks: 공부 할 일 저장
- write_file: 정리본 저장
- get_memory: 현재 기억 확인
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
너는 초심자용 공부 도우미 AI Agent다.
사용자의 공부 정보와 할 일을 정리하는 것이 목표다.

규칙:
- 사용자의 취향, 목표, 선호 과목은 facts에 저장하라.
- 공부 할 일은 tasks에 저장하라.
- 사용자가 정리본 저장을 원하면 write_file을 사용하라.
- 기억을 확인해야 하면 get_memory를 사용하라.
- 답변은 짧고 쉬운 한국어로 하라.
""".strip()

tools = [
    {
        "name": "save_fact",
        "description": "사용자의 중요한 공부 관련 사실을 저장합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "사실 이름"},
                "value": {"type": "string", "description": "저장할 내용"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "add_task",
        "description": "새 공부 할 일을 추가합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "추가할 공부 할 일"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "complete_task",
        "description": "기존 공부 할 일을 완료 처리합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "완료할 공부 할 일"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "get_memory",
        "description": "현재 세션의 기억 전체를 확인합니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "write_file",
        "description": "정리한 공부 계획을 파일로 저장합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "저장할 파일 경로"},
                "content": {"type": "string", "description": "파일에 저장할 내용"},
            },
            "required": ["path", "content"],
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


def tool_write_file(path: str, content: str) -> str:
    full_path = (BASE_DIR / path).resolve() if not Path(path).is_absolute() else Path(path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with full_path.open("w", encoding="utf-8") as file:
        file.write(content)
    return f"파일 저장 완료: {full_path}"


def execute_tool(state: dict, name: str, inputs: dict) -> str:
    if name == "save_fact":
        return tool_save_fact(state, inputs["key"], inputs["value"])
    if name == "add_task":
        return tool_add_task(state, inputs["task"])
    if name == "complete_task":
        return tool_complete_task(state, inputs["task"])
    if name == "get_memory":
        return tool_get_memory(state)
    if name == "write_file":
        return tool_write_file(inputs["path"], inputs["content"])
    return f"알 수 없는 tool입니다: {name}"


def build_context_message(state: dict) -> str:
    facts_text = json.dumps(state["facts"], ensure_ascii=False)
    tasks_text = json.dumps(state["tasks"], ensure_ascii=False)
    recent_messages = json.dumps(state["messages"][-4:], ensure_ascii=False)
    return (
        "현재 공부 메모리 요약입니다.\n"
        f"- facts: {facts_text}\n"
        f"- tasks: {tasks_text}\n"
        f"- recent_messages: {recent_messages}\n"
    )


def run_agent(user_message: str, session_id: str = "student") -> None:
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
    print("=== Day 6: Study Assistant 미니 프로젝트 ===")
    print("같은 세션을 사용하면 공부 정보와 할 일이 이어집니다.")

    run_agent("내가 가장 좋아하는 과목은 과학이야. 기억해줘.")
    run_agent("오늘 할 일은 수학 문제 10개 풀기와 영어 단어 20개 외우기야. 기억해줘.")
    run_agent("영어 단어 20개 외우기는 끝났어. 지금 남은 할 일을 알려줘.")
    run_agent("지금까지 기억한 내용을 study_summary.txt로 정리해서 저장해줘.")
