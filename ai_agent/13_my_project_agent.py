"""
Day 13: My Project Agent
- 09~12단계에서 배운 planning / execution / verification / workflow를
  사용자의 주제에 맞는 나만의 프로젝트 Agent로 확장하는 예제
- 상태를 저장하고, 현재 단계에 맞춰 실행 -> 검증 -> 보완 -> 완료를 반복한다.
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

TOPIC_LIBRARY = {
    "파이썬 조건문": {
        "aliases": ["조건문", "if", "elif", "else"],
        "notes": [
            "조건문은 상황에 따라 다른 코드를 실행하게 해줍니다.",
            "파이썬에서는 if, elif, else를 사용해 분기합니다.",
            "조건식이 True일 때만 해당 블록이 실행됩니다.",
        ],
        "quiz": [
            "1. if와 else는 각각 언제 실행되나요?",
            "2. elif가 필요한 이유를 한 문장으로 설명해보세요.",
        ],
        "code": (
            "score = 85\n\n"
            "if score >= 90:\n"
            "    print('A')\n"
            "elif score >= 80:\n"
            "    print('B')\n"
            "else:\n"
            "    print('C')"
        ),
        "summary": [
            "조건문은 분기 처리를 담당합니다.",
            "elif를 쓰면 여러 조건을 순서대로 검사할 수 있습니다.",
            "조건식과 들여쓰기를 함께 정확히 써야 합니다.",
        ],
    },
    "리스트 컴프리헨션": {
        "aliases": ["리스트", "컴프리헨션", "list comprehension"],
        "notes": [
            "리스트 컴프리헨션은 리스트를 짧고 읽기 쉽게 만드는 문법입니다.",
            "기본 형태는 [표현식 for 변수 in 반복대상] 입니다.",
            "조건을 붙이면 원하는 값만 골라 새 리스트를 만들 수 있습니다.",
        ],
        "quiz": [
            "1. `[x * 2 for x in [1, 2, 3]]`의 결과는 무엇인가요?",
            "2. 리스트 컴프리헨션이 반복문보다 읽기 쉬운 이유를 말해보세요.",
        ],
        "code": (
            "numbers = [1, 2, 3, 4]\n"
            "evens = [x for x in numbers if x % 2 == 0]\n"
            "print(evens)"
        ),
        "summary": [
            "표현식과 반복 대상을 한 줄에 함께 표현할 수 있습니다.",
            "조건식을 넣으면 필터링까지 한 번에 처리할 수 있습니다.",
            "너무 복잡해지면 일반 반복문이 더 읽기 쉬울 수 있습니다.",
        ],
    },
    "영어 단어 암기": {
        "aliases": ["영어", "단어", "vocabulary"],
        "notes": [
            "단어 암기는 반복 노출과 짧은 회상이 중요합니다.",
            "뜻만 보는 것보다 예문과 함께 보는 편이 오래 기억됩니다.",
            "한 번에 많은 양보다 자주 짧게 복습하는 방식이 효율적입니다.",
        ],
        "quiz": [
            "1. 단어를 외울 때 예문을 같이 보면 왜 도움이 되나요?",
            "2. 짧고 자주 복습하는 방식이 좋은 이유를 설명해보세요.",
        ],
        "code": (
            "words = {\n"
            "    'focus': '집중',\n"
            "    'review': '복습',\n"
            "    'improve': '향상시키다',\n"
            "}\n\n"
            "for word, meaning in words.items():\n"
            "    print(f'{word}: {meaning}')"
        ),
        "summary": [
            "뜻, 예문, 발음을 같이 묶어서 외우면 기억이 더 오래 갑니다.",
            "헷갈리는 단어는 따로 모아 복습 주기를 짧게 잡는 편이 좋습니다.",
            "암기 후 바로 회상 문제를 풀면 약점을 빨리 찾을 수 있습니다.",
        ],
    },
}

DEFAULT_TOPIC = "파이썬 조건문"
DEFAULT_SEQUENCE = [
    ("개념 정리하기", "concept"),
    ("예제 만들기", "example"),
    ("확인 문제 풀기", "quiz"),
    ("약점 보완하기", "review"),
    ("최종 요약하기", "summary"),
]

SYSTEM_PROMPT = """
너는 초보자용 프로젝트 Agent다.
사용자의 목표를 작은 단계로 나누고, 현재 상태를 보고
실행 -> 검증 -> 보완 -> 완료를 이어가며 학습 프로젝트를 관리한다.

규칙:
- 새 프로젝트를 만들고 싶다면 create_project_plan을 사용하라.
- 현재 프로젝트 상태를 확인하려면 get_project_status를 사용하라.
- 현재 단계를 직접 실행하려면 execute_current_step을 사용하라.
- 방금 실행한 결과를 점검하려면 verify_last_execution을 사용하라.
- 보완이 필요하면 revise_current_step을 사용하라.
- 자동으로 흐름을 한 번 진행하려면 run_project_cycle을 사용하라.
- 다음 행동을 추천하려면 recommend_next_action을 사용하라.
- 최근 기록을 보여주려면 get_workflow_log를 사용하라.
- 답변은 짧고 분명하게 설명하라.
""".strip()

tools = [
    {
        "name": "create_project_plan",
        "description": "사용자 목표를 3~5단계 프로젝트 계획으로 저장합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "topic": {"type": "string"},
                "project_type": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["goal"],
        },
    },
    {
        "name": "get_project_status",
        "description": "현재 프로젝트 전체 상태를 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "execute_current_step",
        "description": "현재 단계를 실행하고 결과를 만듭니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "verify_last_execution",
        "description": "방금 실행한 결과가 현재 단계와 맞는지 검증합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "revise_current_step",
        "description": "검증 실패 후 현재 단계를 보완 실행합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_project_cycle",
        "description": "현재 상태를 보고 실행, 검증, 보완, 완료 중 다음 행동 하나를 자동으로 진행합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "recommend_next_action",
        "description": "현재 상태 기준으로 다음에 무엇을 하면 좋을지 추천합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_workflow_log",
        "description": "최근 프로젝트 workflow 기록을 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def memory_path(session_id: str) -> Path:
    return MEMORY_DIR / f"{session_id}.json"


def default_state() -> dict:
    return {
        "messages": [],
        "project": None,
        "workflow_phase": "idle",
        "execution_log": [],
        "verification_log": [],
        "workflow_log": [],
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
    state.setdefault("project", None)
    state.setdefault("workflow_phase", "idle")
    state.setdefault("execution_log", [])
    state.setdefault("verification_log", [])
    state.setdefault("workflow_log", [])
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


def log_workflow(state: dict, action: str, detail: str) -> None:
    state["workflow_log"].append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "detail": detail,
        }
    )
    state["workflow_log"] = state["workflow_log"][-12:]


def infer_topic(*texts: str) -> str:
    merged = " ".join(texts).lower()
    for topic, data in TOPIC_LIBRARY.items():
        if topic.lower() in merged:
            return topic
        if any(alias.lower() in merged for alias in data["aliases"]):
            return topic
    return DEFAULT_TOPIC


def infer_step_kind(step_text: str, default_kind: str = "concept") -> str:
    normalized = step_text.lower()
    if any(keyword in normalized for keyword in ["예제", "코드", "실습", "작성"]):
        return "example"
    if any(keyword in normalized for keyword in ["퀴즈", "문제", "테스트", "확인"]):
        return "quiz"
    if any(keyword in normalized for keyword in ["보완", "복습", "개선", "약점"]):
        return "review"
    if any(keyword in normalized for keyword in ["요약", "정리본", "회고", "마무리"]):
        return "summary"
    if any(keyword in normalized for keyword in ["개념", "설명", "기초", "정리"]):
        return "concept"
    return default_kind


def make_step_items(steps: list[str] | None) -> list[dict]:
    if steps:
        cleaned_steps = [step.strip() for step in steps if step.strip()][:5]
        return [
            {
                "step": step,
                "kind": infer_step_kind(step),
                "done": False,
                "executed": False,
                "verified": False,
                "attempts": 0,
            }
            for step in cleaned_steps
        ]

    return [
        {
            "step": step_text,
            "kind": kind,
            "done": False,
            "executed": False,
            "verified": False,
            "attempts": 0,
        }
        for step_text, kind in DEFAULT_SEQUENCE
    ]


def current_step_item(state: dict) -> tuple[int | None, dict | None]:
    project = state.get("project")
    if not project:
        return None, None

    step_number = project.get("current_step")
    if step_number is None:
        return None, None

    return step_number, project["steps"][step_number - 1]


def step_status(item: dict) -> str:
    if item["done"]:
        return "완료"
    if item["verified"]:
        return "검증됨"
    if item["executed"]:
        return "실행됨"
    return "대기중"


def tool_create_project_plan(
    state: dict,
    goal: str,
    topic: str | None = None,
    project_type: str | None = None,
    steps: list[str] | None = None,
) -> str:
    selected_topic = infer_topic(topic or "", goal)
    step_items = make_step_items(steps)

    state["project"] = {
        "goal": goal,
        "topic": selected_topic,
        "project_type": project_type or "study",
        "steps": step_items,
        "current_step": 1 if step_items else None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    state["workflow_phase"] = "ready"
    state["execution_log"] = []
    state["verification_log"] = []
    state["workflow_log"] = []
    state["last_execution_result"] = None
    state["last_verification_result"] = None
    log_workflow(state, "create_plan", f"목표 '{goal}' 프로젝트 생성")
    return f"프로젝트 계획 저장 완료: {goal}"


def tool_get_project_status(state: dict) -> str:
    project = state.get("project")
    phase = state.get("workflow_phase", "idle")
    if not project:
        return f"현재 프로젝트 상태: {phase}\n- 아직 프로젝트 계획이 없습니다."

    total = len(project["steps"])
    done_count = sum(1 for item in project["steps"] if item["done"])
    verified_count = sum(1 for item in project["steps"] if item["verified"])
    step_number, step_item = current_step_item(state)

    lines = [
        f"현재 프로젝트 상태: {phase}",
        f"- 목표: {project['goal']}",
        f"- 주제: {project['topic']}",
        f"- 완료 단계: {done_count}/{total}",
        f"- 검증 단계: {verified_count}/{total}",
    ]

    if step_number is not None and step_item is not None:
        lines.append(f"- 현재 단계: {step_number}번 / {step_item['step']}")
        lines.append(f"- 현재 단계 상태: {step_status(step_item)}")
        lines.append(f"- 현재 단계 시도 횟수: {step_item['attempts']}회")
    else:
        lines.append("- 현재 단계: 없음 (모든 단계 완료)")

    if state.get("last_verification_result"):
        verdict = "통과" if state["last_verification_result"]["passed"] else "보완 필요"
        lines.append(f"- 마지막 검증: {verdict}")

    return "\n".join(lines)


def build_execution_result(state: dict, step_item: dict, revised: bool = False) -> str:
    project = state["project"]
    topic = project["topic"]
    topic_data = TOPIC_LIBRARY[topic]
    issues = []
    if state.get("last_verification_result"):
        issues = state["last_verification_result"].get("issues", [])

    prefix = "보완 실행 결과" if revised else "실행 결과"

    if step_item["kind"] == "concept":
        lines = [f"{prefix}: {topic} 개념 정리"]
        for note in topic_data["notes"]:
            lines.append(f"- {note}")
        lines.append(f"- 이 단계 목적: {step_item['step']}")
        return "\n".join(lines)

    if step_item["kind"] == "example":
        return (
            f"{prefix}: {topic} 예제 코드\n"
            "```python\n"
            f"{topic_data['code']}\n"
            "```\n"
            f"설명: {step_item['step']}에 맞는 가장 기본 예제입니다."
        )

    if step_item["kind"] == "quiz":
        lines = [f"{prefix}: {topic} 확인 문제"]
        lines.extend(topic_data["quiz"])
        lines.append("3. 위 문제 중 가장 헷갈리는 부분을 한 문장으로 적어보세요.")
        return "\n".join(lines)

    if step_item["kind"] == "review":
        lines = [f"{prefix}: {topic} 약점 보완"]
        if issues:
            for issue in issues:
                lines.append(f"- 보완 포인트: {issue}")
        else:
            lines.append("- 보완 포인트: 최근 결과를 다시 짧고 정확하게 정리합니다.")
        lines.append(f"- 다시 확인할 개념: {topic_data['notes'][0]}")
        lines.append(f"- 이번 보완 목표: {step_item['step']}")
        return "\n".join(lines)

    lines = [f"{prefix}: {topic} 최종 요약"]
    for summary in topic_data["summary"]:
        lines.append(f"- {summary}")
    lines.append("- 다음에는 직접 문제를 만들어 설명까지 해보면 좋습니다.")
    return "\n".join(lines)


def execute_current_step(state: dict, revised: bool = False) -> str:
    project = state.get("project")
    step_number, step_item = current_step_item(state)
    if not project or step_number is None or step_item is None:
        return "실행할 현재 단계가 없습니다."

    step_item["attempts"] += 1
    step_item["executed"] = True
    step_item["verified"] = False
    state["workflow_phase"] = "verification_pending"

    result = build_execution_result(state, step_item, revised=revised)
    state["last_execution_result"] = {
        "step_number": step_number,
        "step": step_item["step"],
        "kind": step_item["kind"],
        "content": result,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "revised": revised,
    }
    state["execution_log"].append(state["last_execution_result"])
    state["execution_log"] = state["execution_log"][-12:]
    return result


def tool_execute_current_step(state: dict) -> str:
    return execute_current_step(state, revised=False)


def verify_last_execution(state: dict) -> str:
    project = state.get("project")
    last_result = state.get("last_execution_result")
    step_number, step_item = current_step_item(state)
    if not project or not last_result or step_number is None or step_item is None:
        return "검증할 실행 결과가 없습니다."

    content = last_result["content"]
    issues: list[str] = []

    if step_item["kind"] in {"concept", "summary"}:
        if content.count("- ") < 2:
            issues.append("핵심 내용을 bullet로 두 개 이상 정리해야 합니다.")
        if project["topic"] not in content:
            issues.append("현재 주제가 결과에 드러나야 합니다.")
    elif step_item["kind"] == "example":
        if "```python" not in content:
            issues.append("예제 단계에는 파이썬 코드 블록이 포함되어야 합니다.")
    elif step_item["kind"] == "quiz":
        if content.count("1.") == 0 or content.count("2.") == 0:
            issues.append("퀴즈 단계에는 최소 두 개의 질문이 필요합니다.")
    elif step_item["kind"] == "review":
        if "보완 포인트" not in content:
            issues.append("보완 단계에는 보완 포인트가 분명히 적혀야 합니다.")

    passed = not issues
    if passed:
        step_item["verified"] = True
        state["workflow_phase"] = "completion_pending"
    else:
        state["workflow_phase"] = "needs_revision"

    state["last_verification_result"] = {
        "step_number": step_number,
        "step": step_item["step"],
        "passed": passed,
        "issues": issues,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    state["verification_log"].append(state["last_verification_result"])
    state["verification_log"] = state["verification_log"][-12:]

    if passed:
        return (
            "검증 결과: 통과\n"
            f"- 단계: {step_item['step']}\n"
            "- 현재 단계 목적에 맞는 결과가 준비되었습니다."
        )

    lines = ["검증 결과: 보완 필요", f"- 단계: {step_item['step']}"]
    for issue in issues:
        lines.append(f"- 이유: {issue}")
    return "\n".join(lines)


def tool_verify_last_execution(state: dict) -> str:
    return verify_last_execution(state)


def tool_revise_current_step(state: dict) -> str:
    state["workflow_phase"] = "revising"
    return execute_current_step(state, revised=True)


def complete_current_step(state: dict) -> str:
    project = state.get("project")
    step_number, step_item = current_step_item(state)
    if not project or step_number is None or step_item is None:
        return "완료 처리할 현재 단계가 없습니다."

    if not step_item["verified"]:
        return "검증된 단계만 완료 처리할 수 있습니다."

    step_item["done"] = True
    next_step = None
    for index, item in enumerate(project["steps"], start=1):
        if not item["done"]:
            next_step = index
            break

    project["current_step"] = next_step
    state["workflow_phase"] = "complete" if next_step is None else "ready"
    if next_step is None:
        return f"{step_number}번 단계 완료. 프로젝트의 모든 단계를 끝냈습니다."
    return f"{step_number}번 단계 완료. 다음은 {next_step}번 단계입니다."


def tool_run_project_cycle(state: dict) -> str:
    project = state.get("project")
    if not project:
        return "먼저 목표를 정하고 프로젝트 계획부터 만들어보세요."

    step_number, step_item = current_step_item(state)
    if step_number is None or step_item is None:
        state["workflow_phase"] = "complete"
        return "현재 프로젝트는 모두 완료되었습니다."

    failed_verification = state.get("last_verification_result")
    if failed_verification and failed_verification.get("step_number") == step_number:
        if failed_verification.get("passed") is False and step_item["executed"] and not step_item["verified"]:
            result = tool_revise_current_step(state)
            log_workflow(state, "revise", f"{step_number}번 단계 보완 실행")
            return "project cycle: 보완 단계\n" + result

    if not step_item["executed"]:
        result = tool_execute_current_step(state)
        log_workflow(state, "execute", f"{step_number}번 단계 실행")
        return "project cycle: 실행 단계\n" + result

    if not step_item["verified"]:
        result = tool_verify_last_execution(state)
        log_workflow(state, "verify", f"{step_number}번 단계 검증")
        return "project cycle: 검증 단계\n" + result

    result = complete_current_step(state)
    log_workflow(state, "complete", f"{step_number}번 단계 완료 처리")
    return "project cycle: 완료 처리 단계\n" + result


def tool_recommend_next_action(state: dict) -> str:
    project = state.get("project")
    if not project:
        return "먼저 목표를 말하고 프로젝트 계획부터 만들어보세요."

    step_number, step_item = current_step_item(state)
    if step_number is None or step_item is None:
        return "현재 프로젝트는 모두 끝났습니다. 새 목표로 다른 프로젝트를 시작해도 좋습니다."

    failed_verification = state.get("last_verification_result")
    if not step_item["executed"]:
        return (
            "추천 다음 행동\n"
            f"- {step_number}번 단계를 실행해보세요: {step_item['step']}"
        )

    if failed_verification and failed_verification.get("step_number") == step_number:
        if failed_verification.get("passed") is False and not step_item["verified"]:
            return (
                "추천 다음 행동\n"
                f"- {step_number}번 단계 결과를 보완해보세요.\n"
                "- project cycle을 한 번 더 돌리면 보완 실행으로 이어집니다."
            )

    if not step_item["verified"]:
        return (
            "추천 다음 행동\n"
            f"- {step_number}번 단계 실행 결과를 검증해보세요.\n"
            "- project cycle을 한 번 더 돌리면 검증 단계로 이어집니다."
        )

    return (
        "추천 다음 행동\n"
        f"- {step_number}번 단계는 검증이 끝났습니다.\n"
        "- project cycle을 한 번 더 돌리면 완료 처리로 넘어갑니다."
    )


def tool_get_workflow_log(state: dict) -> str:
    log = state.get("workflow_log", [])
    if not log:
        return "아직 프로젝트 workflow 기록이 없습니다."

    lines = ["최근 프로젝트 workflow 기록"]
    for item in log:
        lines.append(f"- {item['timestamp']} | {item['action']} | {item['detail']}")
    return "\n".join(lines)


def execute_tool(state: dict, name: str, inputs: dict) -> str:
    if name == "create_project_plan":
        return tool_create_project_plan(
            state,
            inputs["goal"],
            inputs.get("topic"),
            inputs.get("project_type"),
            inputs.get("steps"),
        )
    if name == "get_project_status":
        return tool_get_project_status(state)
    if name == "execute_current_step":
        return tool_execute_current_step(state)
    if name == "verify_last_execution":
        return tool_verify_last_execution(state)
    if name == "revise_current_step":
        return tool_revise_current_step(state)
    if name == "run_project_cycle":
        return tool_run_project_cycle(state)
    if name == "recommend_next_action":
        return tool_recommend_next_action(state)
    if name == "get_workflow_log":
        return tool_get_workflow_log(state)
    return f"지원하지 않는 tool입니다: {name}"


def build_context_message(state: dict) -> str:
    return (
        "현재 프로젝트 상태 요약입니다.\n"
        f"- workflow_phase: {state['workflow_phase']}\n"
        f"- project: {json.dumps(state['project'], ensure_ascii=False)}\n"
        f"- last_execution_result: {json.dumps(state['last_execution_result'], ensure_ascii=False)}\n"
        f"- last_verification_result: {json.dumps(state['last_verification_result'], ensure_ascii=False)}\n"
    )


def run_agent(user_message: str, session_id: str = "student_my_project") -> None:
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
    print("=== Day 13: My Project Agent ===")
    print("내 주제를 넣어 나만의 학습 프로젝트를 실행하는 단계입니다.")

    run_agent("파이썬 조건문 공부 프로젝트를 만들어줘.")
    run_agent("현재 프로젝트 상태 보여줘.")
    run_agent("다음 project cycle 진행해줘.")
    run_agent("다음 project cycle 진행해줘.")
    run_agent("다음 project cycle 진행해줘.")
    run_agent("최근 workflow 기록 보여줘.")
