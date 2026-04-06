"""
Day 12: Workflow Agent
- 계획, 실행, 검증, 보완, 완료 처리를 하나의 흐름으로 묶는 예제
- 상태를 보고 "지금 무엇을 해야 하는가"를 자동으로 고르는 오케스트레이션에 집중

이 파일의 목표:
- planning / execution / verification을 따로 배우는 것을 넘어, 하나의 workflow로 묶는 법을 이해한다.
- 현재 단계 상태를 보고 자동으로 실행, 검증, 보완, 완료 처리 중 무엇을 할지 고르게 만든다.
- "초안 실행 -> 검증 -> 보완 -> 재검증 -> 완료" 흐름을 상태로 관리하는 법을 익힌다.
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
        "함수는 반복되는 코드를 이름으로 묶어 다시 쓰게 해줍니다.",
        "입력값은 매개변수로 받고, 결과는 return으로 돌려줍니다.",
        "return이 없으면 기본적으로 None이 반환됩니다.",
    ],
    "리스트 컴프리헨션": [
        "리스트 컴프리헨션은 새 리스트를 짧게 만드는 문법입니다.",
        "기본 형태는 [표현식 for 변수 in 반복대상] 입니다.",
        "조건을 붙이면 원하는 값만 골라낼 수 있습니다.",
    ],
    "조건문": [
        "조건문은 상황에 따라 다른 코드를 실행하게 합니다.",
        "파이썬에서는 if, elif, else를 사용합니다.",
        "조건식이 True일 때 해당 블록이 실행됩니다.",
    ],
}

QUIZ_BANK = {
    "파이썬 함수": [
        "1. 함수 선언에 사용하는 키워드는 무엇일까요?",
        "2. return은 어떤 역할을 하나요?",
    ],
    "리스트 컴프리헨션": [
        "1. `[x * 2 for x in [1, 2, 3]]`의 결과는 무엇일까요?",
        "2. 리스트 컴프리헨션이 반복문보다 짧은 이유는 무엇일까요?",
    ],
    "조건문": [
        "1. if와 else는 각각 언제 실행될까요?",
        "2. elif는 왜 필요할까요?",
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
너는 초심자용 워크플로우 공부 도우미 AI Agent다.
사용자의 목표를 계획으로 만들고, 각 단계를 실행/검증/보완/완료 처리 흐름으로 관리하는 것이 목표다.

규칙:
- 새 목표를 말하면 create_plan을 사용하라.
- 계획을 보고 싶으면 get_plan을 사용하라.
- 자동으로 다음 workflow 사이클을 진행하려면 run_workflow_cycle을 사용하라.
- 현재 전체 상태를 보고 싶으면 get_workflow_status를 사용하라.
- 진행 기록을 보고 싶으면 get_workflow_log를 사용하라.
- 다음에 무엇을 해야 할지 묻는다면 recommend_next_action을 사용하라.
- 답변은 짧고 쉬운 한국어로 하라.
""".strip()

tools = [
    {
        "name": "create_plan",
        "description": "큰 목표를 3~5개의 작은 단계로 나눈 workflow 계획을 저장합니다.",
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
        "name": "run_workflow_cycle",
        "description": "현재 상태를 보고 실행, 검증, 보완, 완료 처리 중 다음 행동 하나를 자동으로 진행합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_workflow_status",
        "description": "현재 workflow 전체 상태를 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_workflow_log",
        "description": "지금까지의 workflow 진행 기록을 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "recommend_next_action",
        "description": "현재 상태 기준으로 다음에 무엇을 하면 좋을지 추천합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def memory_path(session_id: str) -> Path:
    return MEMORY_DIR / f"{session_id}.json"


def default_state() -> dict:
    return {
        "messages": [],
        "workflow_phase": "idle",
        "plan": None,
        "workflow_log": [],
        "execution_log": [],
        "verification_log": [],
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
    state.setdefault("workflow_phase", "idle")
    state.setdefault("plan", None)
    state.setdefault("workflow_log", [])
    state.setdefault("execution_log", [])
    state.setdefault("verification_log", [])
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


def plan_step_status(item: dict) -> str:
    if item["done"]:
        return "완료"
    if item["verified"]:
        return "검증됨"
    if item["executed"]:
        return "실행됨"
    return "진행 전"


def current_step_item(state: dict) -> tuple[int | None, dict | None]:
    plan = state.get("plan")
    if not plan:
        return None, None

    step_number = plan.get("current_step")
    if step_number is None:
        return None, None

    return step_number, plan["steps"][step_number - 1]


def log_workflow(state: dict, action: str, detail: str) -> None:
    state["workflow_log"].append(
        {
            "action": action,
            "detail": detail,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    state["workflow_log"] = state["workflow_log"][-12:]


def tool_create_plan(state: dict, goal: str, steps: list[str]) -> str:
    cleaned_steps = [step.strip() for step in steps if step.strip()][:5]
    state["plan"] = {
        "goal": goal,
        "steps": [
            {
                "step": step,
                "done": False,
                "executed": False,
                "verified": False,
                "attempts": 0,
            }
            for step in cleaned_steps
        ],
        "current_step": 1 if cleaned_steps else None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    state["workflow_phase"] = "ready"
    state["workflow_log"] = []
    state["execution_log"] = []
    state["verification_log"] = []
    state["last_execution_result"] = None
    state["last_verification_result"] = None
    log_workflow(state, "create_plan", f"목표 '{goal}' 계획 생성")
    return f"workflow 계획 저장 완료: {goal}"


def tool_get_plan(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "아직 저장된 계획이 없습니다."

    lines = [f"목표: {plan['goal']}"]
    for index, item in enumerate(plan["steps"], start=1):
        marker = " <== 현재 단계" if plan.get("current_step") == index else ""
        attempts = f", 시도 {item['attempts']}회" if item["attempts"] else ""
        lines.append(f"{index}. {item['step']} [{plan_step_status(item)}{attempts}]{marker}")
    return "\n".join(lines)


def build_step_result(goal: str, step_text: str, attempt: int) -> str:
    topic = infer_topic(goal, step_text)
    is_draft = attempt <= 1

    if any(keyword in step_text for keyword in ["정리", "요약", "개념", "설명"]):
        notes = TOPIC_NOTES.get(topic, TOPIC_NOTES["파이썬 함수"])
        if is_draft:
            return (
                f"실행 초안: {topic} 간단 정리\n"
                f"- {notes[0]}"
            )
        lines = [f"실행 결과: {topic} 핵심 정리"]
        for note in notes:
            lines.append(f"- {note}")
        return "\n".join(lines)

    if any(keyword in step_text for keyword in ["퀴즈", "문제", "테스트", "확인"]):
        questions = QUIZ_BANK.get(topic, QUIZ_BANK["파이썬 함수"])
        if is_draft:
            return "실행 초안: 확인 문제 준비\n" + questions[0]
        return "실행 결과: 확인 문제 준비\n" + "\n".join(questions)

    if any(keyword in step_text for keyword in ["예제", "실습", "코드", "작성"]):
        code = CODE_BANK.get(topic, CODE_BANK["파이썬 함수"])
        if is_draft:
            return (
                f"실행 초안: {topic} 예제 코드\n"
                "```python\n"
                f"{code}\n"
                "```"
            )
        return (
            f"실행 결과: {topic} 실습 코드\n"
            "```python\n"
            f"{code}\n"
            "```\n"
            "- 연습: 코드를 직접 실행하고 출력 결과를 말해보세요."
        )

    if is_draft:
        return (
            "실행 초안: 현재 단계 메모\n"
            f"- 지금 단계: {step_text}"
        )

    return (
        "실행 결과: 현재 단계 체크리스트\n"
        f"- 목표: {goal}\n"
        f"- 지금 단계: {step_text}\n"
        "- 바로 할 작은 행동 1개를 정하고 시작해보세요."
    )


def verification_issues(step_text: str, execution_content: str) -> list[str]:
    issues: list[str] = []

    if not execution_content.strip():
        issues.append("실행 결과가 비어 있습니다.")

    if any(keyword in step_text for keyword in ["정리", "요약", "개념", "설명"]):
        if execution_content.count("- ") < 2:
            issues.append("핵심 정리는 최소 2개 이상이어야 합니다.")

    if any(keyword in step_text for keyword in ["퀴즈", "문제", "테스트", "확인"]):
        if "1." not in execution_content or "2." not in execution_content:
            issues.append("확인 문제는 최소 2개가 있어야 합니다.")

    if any(keyword in step_text for keyword in ["예제", "실습", "코드", "작성"]):
        if "```python" not in execution_content:
            issues.append("코드 예제가 포함되어야 합니다.")
        if "연습:" not in execution_content and "출력 결과" not in execution_content:
            issues.append("코드 뒤에 연습 안내가 있으면 더 좋습니다.")

    return issues


def execute_current_step(state: dict) -> str:
    plan = state.get("plan")
    step_number, step_item = current_step_item(state)
    if not plan or step_number is None or step_item is None:
        return "실행할 현재 단계가 없습니다."

    step_item["attempts"] += 1
    result = build_step_result(plan["goal"], step_item["step"], step_item["attempts"])
    step_item["executed"] = True
    step_item["verified"] = False
    state["workflow_phase"] = "verification_pending"
    state["last_verification_result"] = None
    state["last_execution_result"] = {
        "step_number": step_number,
        "step": step_item["step"],
        "content": result,
        "attempt": step_item["attempts"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    state["execution_log"].append(
        {
            "step_number": step_number,
            "step": step_item["step"],
            "attempt": step_item["attempts"],
            "result_preview": result.splitlines()[0],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    state["execution_log"] = state["execution_log"][-10:]
    return result


def verify_last_execution(state: dict) -> str:
    step_number, step_item = current_step_item(state)
    last_result = state.get("last_execution_result")
    if step_number is None or step_item is None or not last_result:
        return "먼저 현재 단계를 실행해야 검증할 수 있습니다."

    if last_result["step_number"] != step_number:
        return "현재 단계와 마지막 실행 결과가 맞지 않습니다."

    issues = verification_issues(step_item["step"], last_result["content"])
    passed = len(issues) == 0
    step_item["verified"] = passed
    state["workflow_phase"] = "completion_pending" if passed else "needs_revision"

    verification_result = {
        "step_number": step_number,
        "step": step_item["step"],
        "passed": passed,
        "issues": issues,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }
    state["last_verification_result"] = verification_result
    state["verification_log"].append(verification_result)
    state["verification_log"] = state["verification_log"][-10:]

    if passed:
        return (
            "검증 결과: 통과\n"
            f"- 단계: {step_item['step']}\n"
            "- 실행 결과가 현재 단계 목표와 잘 맞습니다."
        )

    lines = ["검증 결과: 보완 필요", f"- 단계: {step_item['step']}"]
    for issue in issues:
        lines.append(f"- 이유: {issue}")
    return "\n".join(lines)


def revise_current_step(state: dict) -> str:
    state["workflow_phase"] = "revising"
    return execute_current_step(state)


def complete_current_step(state: dict) -> str:
    plan = state.get("plan")
    step_number, step_item = current_step_item(state)
    if not plan or step_number is None or step_item is None:
        return "완료 처리할 현재 단계가 없습니다."

    if not step_item["verified"]:
        return "검증이 끝난 단계만 완료 처리할 수 있습니다."

    step_item["done"] = True
    next_step = None
    for index, item in enumerate(plan["steps"], start=1):
        if not item["done"]:
            next_step = index
            break

    plan["current_step"] = next_step
    state["workflow_phase"] = "complete" if next_step is None else "ready"
    if next_step is None:
        return f"{step_number}번 단계 완료. workflow의 모든 단계를 끝냈습니다."
    return f"{step_number}번 단계 완료. 다음은 {next_step}번 단계입니다."


def tool_run_workflow_cycle(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "먼저 목표를 정하고 계획부터 만들어보세요."

    step_number, step_item = current_step_item(state)
    if step_number is None or step_item is None:
        state["workflow_phase"] = "complete"
        return "현재 workflow는 모두 완료되었습니다."

    failed_verification = state.get("last_verification_result")
    if failed_verification and failed_verification.get("step_number") == step_number:
        if failed_verification.get("passed") is False and step_item["executed"] and not step_item["verified"]:
            result = revise_current_step(state)
            log_workflow(state, "revise", f"{step_number}번 단계 보완 실행")
            return "workflow 사이클: 보완 단계\n" + result

    if not step_item["executed"]:
        result = execute_current_step(state)
        log_workflow(state, "execute", f"{step_number}번 단계 실행")
        return "workflow 사이클: 실행 단계\n" + result

    if not step_item["verified"]:
        result = verify_last_execution(state)
        log_workflow(state, "verify", f"{step_number}번 단계 검증")
        return "workflow 사이클: 검증 단계\n" + result

    result = complete_current_step(state)
    log_workflow(state, "complete", f"{step_number}번 단계 완료 처리")
    return "workflow 사이클: 완료 처리 단계\n" + result


def tool_get_workflow_status(state: dict) -> str:
    plan = state.get("plan")
    phase = state.get("workflow_phase", "idle")
    if not plan:
        return f"현재 workflow 상태: {phase}\n- 아직 계획이 없습니다."

    total = len(plan["steps"])
    done_count = sum(1 for item in plan["steps"] if item["done"])
    verified_count = sum(1 for item in plan["steps"] if item["verified"])
    step_number, step_item = current_step_item(state)

    lines = [
        f"현재 workflow 상태: {phase}",
        f"- 목표: {plan['goal']}",
        f"- 완료한 단계: {done_count}/{total}",
        f"- 검증된 단계: {verified_count}/{total}",
    ]

    if step_number is not None and step_item is not None:
        lines.append(f"- 현재 단계: {step_number}번 / {step_item['step']}")
        lines.append(f"- 현재 단계 상태: {plan_step_status(step_item)}")
        lines.append(f"- 현재 단계 시도 횟수: {step_item['attempts']}회")
    else:
        lines.append("- 현재 단계: 없음 (모든 단계 완료)")

    last_verification = state.get("last_verification_result")
    if last_verification:
        verification_text = "통과" if last_verification["passed"] else "보완 필요"
        lines.append(f"- 마지막 검증: {verification_text}")

    return "\n".join(lines)


def tool_get_workflow_log(state: dict) -> str:
    log = state.get("workflow_log", [])
    if not log:
        return "아직 workflow 기록이 없습니다."

    lines = ["최근 workflow 기록"]
    for item in log:
        lines.append(f"- {item['timestamp']} | {item['action']} | {item['detail']}")
    return "\n".join(lines)


def tool_recommend_next_action(state: dict) -> str:
    plan = state.get("plan")
    if not plan:
        return "먼저 큰 목표를 말하고 계획부터 만들어보세요."

    step_number, step_item = current_step_item(state)
    if step_number is None or step_item is None:
        return "현재 workflow는 모두 끝났습니다. 새 목표를 세워도 좋습니다."

    failed_verification = state.get("last_verification_result")
    if not step_item["executed"]:
        return f"추천 다음 행동\n- {step_number}번 단계를 실행해보세요: {step_item['step']}"

    if failed_verification and failed_verification.get("step_number") == step_number:
        if failed_verification.get("passed") is False and not step_item["verified"]:
            return (
                "추천 다음 행동\n"
                f"- {step_number}번 단계 결과를 보완해보세요.\n"
                "- workflow 사이클을 한 번 더 돌리면 보완 실행으로 이어집니다."
            )

    if not step_item["verified"]:
        return (
            "추천 다음 행동\n"
            f"- {step_number}번 단계 실행 결과를 검증해보세요.\n"
            "- workflow 사이클을 한 번 더 돌리면 검증 단계로 이어집니다."
        )

    return (
        "추천 다음 행동\n"
        f"- {step_number}번 단계는 검증이 끝났습니다.\n"
        "- workflow 사이클을 한 번 더 돌리면 완료 처리로 넘어갑니다."
    )


def execute_tool(state: dict, name: str, inputs: dict) -> str:
    if name == "create_plan":
        return tool_create_plan(state, inputs["goal"], inputs["steps"])
    if name == "get_plan":
        return tool_get_plan(state)
    if name == "run_workflow_cycle":
        return tool_run_workflow_cycle(state)
    if name == "get_workflow_status":
        return tool_get_workflow_status(state)
    if name == "get_workflow_log":
        return tool_get_workflow_log(state)
    if name == "recommend_next_action":
        return tool_recommend_next_action(state)
    return f"알 수 없는 tool입니다: {name}"


def build_context_message(state: dict) -> str:
    return (
        "현재 workflow 상태 요약입니다.\n"
        f"- workflow_phase: {state['workflow_phase']}\n"
        f"- plan: {json.dumps(state['plan'], ensure_ascii=False)}\n"
        f"- last_execution_result: {json.dumps(state['last_execution_result'], ensure_ascii=False)}\n"
        f"- last_verification_result: {json.dumps(state['last_verification_result'], ensure_ascii=False)}\n"
    )


def run_agent(user_message: str, session_id: str = "student_workflow") -> None:
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
    print("=== Day 12: Workflow Agent ===")
    print("같은 세션에서 workflow 사이클을 반복하면 실행 -> 검증 -> 보완 -> 완료 흐름을 볼 수 있습니다.")

    run_agent(
        "파이썬 함수 기초를 공부하는 3단계 계획을 만들어줘. 단계는 함수 개념 정리, 함수 확인 문제 풀기, 함수 예제 코드 작성으로 해줘."
    )
    run_agent("현재 workflow 상태 보여줘.")
    run_agent("다음 workflow 사이클 진행해줘.")
    run_agent("다음 workflow 사이클 진행해줘.")
    run_agent("다음 workflow 사이클 진행해줘.")
    run_agent("다음 workflow 사이클 진행해줘.")
    run_agent("다음 workflow 사이클 진행해줘.")
    run_agent("최근 workflow 기록 보여줘.")
