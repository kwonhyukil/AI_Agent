"""
Day 11: Reflection Agent
- 계획과 실행 뒤에 "검증"과 "회고"를 붙여서 더 안정적인 Agent 흐름을 만드는 예제
- "계획 -> 실행 -> 검증 -> 회고 -> 다음 행동 추천" 흐름을 직접 확인
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

TOPIC_NOTES = {
    "파이썬 함수": [
        "함수는 반복되는 코드를 이름으로 묶어서 다시 사용하게 해준다.",
        "입력값은 매개변수(parameter)로 받고, 결과는 return으로 돌려준다.",
        "return이 없으면 기본적으로 None을 반환한다.",
    ],
    "리스트 컴프리헨션": [
        "리스트 컴프리헨션은 반복문으로 새 리스트를 짧게 만드는 방법이다.",
        "기본 형태는 [표현식 for 변수 in 반복대상] 이다.",
        "조건을 붙이면 원하는 값만 골라서 만들 수 있다.",
    ],
    "조건문": [
        "조건문은 상황에 따라 다른 코드를 실행하게 한다.",
        "파이썬에서는 if, elif, else를 사용한다.",
        "조건식의 결과가 True일 때 해당 블록이 실행된다.",
    ],
}

QUIZ_BANK = {
    "파이썬 함수": [
        "1. 함수 선언에 사용하는 키워드는 무엇일까요?",
        "2. return은 어떤 역할을 하나요?",
    ],
    "리스트 컴프리헨션": [
        "1. `[x * 2 for x in [1, 2, 3]]`의 결과는 무엇일까요?",
        "2. 리스트 컴프리헨션이 반복문보다 짧은 이유를 말해보세요.",
    ],
    "조건문": [
        "1. if와 else는 각각 언제 실행될까요?",
        "2. elif가 필요한 이유는 무엇일까요?",
    ],
}

CODE_BANK = {
    "파이썬 함수": (
        "def add(a, b):\n"
        "    return a + b\n\n"
        "print(add(2, 3))"
    ),
    "리스트 컴프리헨션": (
        "numbers = [1, 2, 3, 4]\n"
        "doubled = [x * 2 for x in numbers]\n"
        "print(doubled)"
    ),
    "조건문": (
        "score = 85\n\n"
        "if score >= 90:\n"
        "    print('A')\n"
        "elif score >= 80:\n"
        "    print('B')\n"
        "else:\n"
        "    print('C')"
    ),
}

SYSTEM_PROMPT = """
너는 초보자용 회고/검증 학습 도우미 AI Agent다.
사용자의 공부 계획과 실행 결과를 보고, 지금 결과가 괜찮은지 확인하고 다음 행동을 정리하는 것이 목표다.

규칙:
- 새 목표를 말하면 create_plan을 사용하라.
- 현재 계획을 보고 싶으면 get_plan을 사용하라.
- 현재 단계를 실제로 진행하려면 execute_current_step을 사용하라.
- 방금 실행한 결과를 확인하려면 verify_last_execution을 사용하라.
- 지금까지 진행을 되돌아보려면 reflect_on_progress를 사용하라.
- 특정 단계를 끝냈다면 complete_plan_step을 사용하라.
- 검증 기록을 보고 싶으면 get_verification_log를 사용하라.
- 다음에 무엇을 해야 할지 묻는다면 recommend_next_action을 사용하라.
- 답변은 짧고 쉬운 한국어로 하라.
""".strip()

tools = [
    {
        "name": "create_plan",
        "description": "큰 목표를 3~5개의 작은 단계로 나눈 계획을 저장합니다.",
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
        "name": "execute_current_step",
        "description": "현재 단계를 실제로 진행해서 실행 결과를 만듭니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "verify_last_execution",
        "description": "방금 실행한 결과가 현재 단계와 잘 맞는지 점검합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "reflect_on_progress",
        "description": "계획, 실행, 검증 상태를 바탕으로 지금까지의 진행을 짧게 회고합니다.",
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
        "name": "get_verification_log",
        "description": "지금까지 쌓인 검증 기록을 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "recommend_next_action",
        "description": "현재 계획, 실행, 검증 상태를 바탕으로 다음 행동을 추천합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def memory_path(session_id: str) -> Path:
    return MEMORY_DIR / f"{session_id}.json"


def default_state() -> dict:
    return {
        "messages": [],
        "plan": None,
        "execution_log": [],
        "verification_log": [],
        "reflection_notes": [],
        "last_execution_result": None,
        "last_verification_result": None,
    }


def load_state(session_id: str) -> dict:
    path = memory_path(session_id)
    if not path.exists():
        return default_state()

    with path.open("r", encoding="utf-8") as file:
        state = json.load(file)

    state.setdefault("messages", [])
    state.setdefault("plan", None)
    state.setdefault("execution_log", [])
    state.setdefault("verification_log", [])
    state.setdefault("reflection_notes", [])
    state.setdefault("last_execution_result", None)
    state.setdefault("last_verification_result", None)
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


def infer_topic(*texts: str) -> str:
    merged = " ".join(texts)
    if "리스트 컴프리헨션" in merged:
        return "리스트 컴프리헨션"
    if "조건문" in merged:
        return "조건문"
    return "파이썬 함수"


def tool_create_plan(state: dict, goal: str, steps: list[str]) -> str:
    cleaned_steps = [step.strip() for step in steps if step.strip()][:5]
    state["plan"] = {
        "goal": goal,
        "steps": [
            {"step": step, "done": False, "executed": False, "verified": False}
            for step in cleaned_steps
        ],
        "current_step": 1 if cleaned_steps else None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    state["execution_log"] = []
    state["verification_log"] = []
    state["reflection_notes"] = []
    state["last_execution_result"] = None
    state["last_verification_result"] = None
    return f"새 계획 저장 완료: {goal}"


def plan_step_status(item: dict) -> str:
    if item["done"]:
        return "완료"
    if item["verified"]:
        return "검증됨"
    if item["executed"]:
        return "실행됨"
    return "진행 전"


def tool_get_plan(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "아직 저장된 계획이 없습니다."

    lines = [f"목표: {plan['goal']}"]
    for index, item in enumerate(plan["steps"], start=1):
        marker = " <== 현재 단계" if plan.get("current_step") == index else ""
        lines.append(f"{index}. {item['step']} [{plan_step_status(item)}]{marker}")
    return "\n".join(lines)


def build_step_result(goal: str, step_text: str) -> str:
    topic = infer_topic(goal, step_text)

    if any(keyword in step_text for keyword in ["정리", "요약", "개념", "설명"]):
        notes = TOPIC_NOTES.get(topic, TOPIC_NOTES["파이썬 함수"])
        lines = [f"실행 결과: {topic} 핵심 정리"]
        for note in notes:
            lines.append(f"- {note}")
        return "\n".join(lines)

    if any(keyword in step_text for keyword in ["퀴즈", "문제", "테스트", "확인"]):
        questions = QUIZ_BANK.get(topic, QUIZ_BANK["파이썬 함수"])
        return "실행 결과: 확인 문제 준비\n" + "\n".join(questions)

    if any(keyword in step_text for keyword in ["예제", "실습", "코드", "작성"]):
        code = CODE_BANK.get(topic, CODE_BANK["파이썬 함수"])
        return (
            f"실행 결과: {topic} 실습 코드\n"
            "```python\n"
            f"{code}\n"
            "```\n"
            "- 연습: 코드를 직접 실행하고 출력 결과를 말해보세요."
        )

    return (
        "실행 결과: 현재 단계 체크리스트\n"
        f"- 목표: {goal}\n"
        f"- 지금 단계: {step_text}\n"
        "- 작은 행동 하나를 바로 시작해보세요."
    )


def tool_execute_current_step(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "먼저 계획을 만들어야 실행할 수 있습니다."

    current_step = plan.get("current_step")
    if current_step is None:
        return "현재 계획의 모든 단계가 끝났습니다."

    step_item = plan["steps"][current_step - 1]
    result = build_step_result(plan["goal"], step_item["step"])
    step_item["executed"] = True
    step_item["verified"] = False
    state["last_verification_result"] = None
    state["last_execution_result"] = {
        "step_number": current_step,
        "step": step_item["step"],
        "content": result,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    state["execution_log"].append(
        {
            "step_number": current_step,
            "step": step_item["step"],
            "result_preview": result.splitlines()[0],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    state["execution_log"] = state["execution_log"][-10:]
    return result


def verification_checks(step_text: str, execution_content: str) -> list[str]:
    checks = ["실행 결과가 비어 있지 않다."]

    if "정리" in step_text or "요약" in step_text or "개념" in step_text:
        checks.append("핵심 개념 설명이 들어 있다." if "- " in execution_content else "핵심 개념 설명이 부족하다.")
    elif "퀴즈" in step_text or "문제" in step_text or "확인" in step_text or "테스트" in step_text:
        checks.append("확인 문제가 포함되어 있다." if "1." in execution_content else "확인 문제가 보이지 않는다.")
    elif "예제" in step_text or "실습" in step_text or "코드" in step_text or "작성" in step_text:
        checks.append("코드 예제가 포함되어 있다." if "```python" in execution_content else "코드 예제가 부족하다.")
    else:
        checks.append("현재 단계에 바로 쓸 수 있는 안내가 있다." if "- " in execution_content else "실행 안내가 부족하다.")

    return checks


def tool_verify_last_execution(state: dict) -> str:
    plan = state.get("plan")
    last_result = state.get("last_execution_result")
    if not plan or not last_result:
        return "먼저 현재 단계를 실행한 뒤에 검증할 수 있습니다."

    step_number = last_result["step_number"]
    step_item = plan["steps"][step_number - 1]
    checks = verification_checks(step_item["step"], last_result["content"])
    passed = all("부족" not in item and "보이지" not in item for item in checks)
    status = "통과" if passed else "다시 보기"
    next_action = (
        "이 단계는 검증을 통과했으니 완료 처리해도 됩니다."
        if passed
        else "이 단계는 결과를 조금 더 보완한 뒤 다시 검증해보세요."
    )

    step_item["verified"] = passed
    verification_result = {
        "step_number": step_number,
        "step": step_item["step"],
        "status": status,
        "checks": checks,
        "next_action": next_action,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    state["last_verification_result"] = verification_result
    state["verification_log"].append(verification_result)
    state["verification_log"] = state["verification_log"][-10:]

    lines = [f"검증 결과: {status}", f"- 단계: {step_item['step']}"]
    for check in checks:
        lines.append(f"- {check}")
    lines.append(f"- 다음 행동: {next_action}")
    return "\n".join(lines)


def tool_reflect_on_progress(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "회고하려면 먼저 계획이 필요합니다."

    done_count = sum(1 for item in plan["steps"] if item["done"])
    verified_count = sum(1 for item in plan["steps"] if item["verified"])
    total_count = len(plan["steps"])
    last_verification = state.get("last_verification_result")

    if last_verification:
        verification_line = f"최근 검증 상태는 '{last_verification['status']}' 입니다."
    else:
        verification_line = "아직 검증한 단계는 없습니다."

    note = (
        f"지금까지 {total_count}단계 중 {done_count}단계를 완료했고, "
        f"{verified_count}단계는 검증까지 끝냈습니다. {verification_line}"
    )
    state["reflection_notes"].append(
        {"content": note, "created_at": datetime.now().isoformat(timespec="seconds")}
    )
    state["reflection_notes"] = state["reflection_notes"][-10:]

    return (
        "회고 메모\n"
        f"- 목표: {plan['goal']}\n"
        f"- 완료한 단계 수: {done_count}/{total_count}\n"
        f"- 검증이 끝난 단계 수: {verified_count}/{total_count}\n"
        f"- 한 줄 회고: {note}"
    )


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
        return f"{step_number}번 단계를 완료했습니다. 계획의 모든 단계가 끝났습니다."
    return f"{step_number}번 단계를 완료했습니다. 다음은 {next_step}번 단계입니다."


def tool_get_verification_log(state: dict) -> str:
    log = state.get("verification_log", [])
    if not log:
        return "아직 검증 기록이 없습니다."

    lines = ["검증 기록"]
    for item in log:
        lines.append(
            f"- {item['step_number']}번 단계: {item['step']} / {item['status']} / {item['created_at']}"
        )
    return "\n".join(lines)


def tool_recommend_next_action(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "먼저 목표를 말하고 계획부터 만들어보세요."

    current_step = plan.get("current_step")
    if current_step is None:
        return "현재 계획은 모두 끝났습니다. 새 목표를 세우거나 전체 내용을 복습해보세요."

    step_item = plan["steps"][current_step - 1]
    if not step_item["executed"]:
        return f"추천 다음 행동\n- 먼저 {current_step}번 단계를 실행해보세요: {step_item['step']}"
    if not step_item["verified"]:
        return (
            "추천 다음 행동\n"
            f"- 방금 실행한 {current_step}번 단계 결과를 검증해보세요.\n"
            "- 검증이 통과하면 완료 처리하세요."
        )
    return (
        "추천 다음 행동\n"
        f"- {current_step}번 단계는 검증이 끝났습니다.\n"
        f"- 실제로 끝냈다면 {current_step}번 단계를 완료 처리하세요."
    )


def execute_tool(state: dict, name: str, inputs: dict) -> str:
    if name == "create_plan":
        return tool_create_plan(state, inputs["goal"], inputs["steps"])
    if name == "get_plan":
        return tool_get_plan(state)
    if name == "execute_current_step":
        return tool_execute_current_step(state)
    if name == "verify_last_execution":
        return tool_verify_last_execution(state)
    if name == "reflect_on_progress":
        return tool_reflect_on_progress(state)
    if name == "complete_plan_step":
        return tool_complete_plan_step(state, inputs["step_number"])
    if name == "get_verification_log":
        return tool_get_verification_log(state)
    if name == "recommend_next_action":
        return tool_recommend_next_action(state)
    return f"알 수 없는 tool입니다: {name}"


def build_context_message(state: dict) -> str:
    return (
        "현재 회고/검증 학습 상태 요약입니다.\n"
        f"- plan: {json.dumps(state['plan'], ensure_ascii=False)}\n"
        f"- execution_log: {json.dumps(state['execution_log'], ensure_ascii=False)}\n"
        f"- verification_log: {json.dumps(state['verification_log'], ensure_ascii=False)}\n"
        f"- last_execution_result: {json.dumps(state['last_execution_result'], ensure_ascii=False)}\n"
        f"- last_verification_result: {json.dumps(state['last_verification_result'], ensure_ascii=False)}\n"
    )


def run_agent(user_message: str, session_id: str = "student_reflection") -> None:
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
                preview = result[:140] + ("..." if len(result) > 140 else "")
                print(f"  Tool 결과: {preview}")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
            messages.append({"role": "user", "content": tool_results})
            continue

        print("예상하지 못한 stop_reason입니다.")
        break


if __name__ == "__main__":
    print("=== Day 11: Reflection Agent ===")
    print("계획과 실행 뒤에 검증과 회고를 붙여 더 안정적으로 공부하는 예제입니다.")

    run_agent("파이썬 함수 기초를 복습하는 3단계 계획을 만들어줘.")
    run_agent("현재 단계를 실행해줘.")
    run_agent("방금 실행한 결과를 검증해줘.")
    run_agent("지금까지 진행을 회고해줘.")
    run_agent("1번 단계를 완료 처리해줘.")
    run_agent("이제 다음에 뭘 하면 좋을지 알려줘.")
