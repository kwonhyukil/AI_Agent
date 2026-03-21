"""
Day 8: Adaptive Study Agent
- 상태를 보고 다음 행동을 정하는 적응형 Agent 예제
- 퀴즈 기록을 바탕으로 약한 주제를 찾고, 난이도와 다음 공부 행동을 조절
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re

import anthropic
from dotenv import load_dotenv


load_dotenv(override=True)
client = anthropic.Anthropic()

MODEL_NAME = "claude-haiku-4-5-20251001"
BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"

QUIZ_BANK = {
    "리스트 컴프리헨션": {
        "easy": [
            {
                "question": "리스트 컴프리헨션은 무엇을 짧게 표현하기 위한 문법일까요?",
                "answer": "반복문으로 리스트를 만드는 코드를 짧게 표현하는 문법입니다.",
                "hint": "핵심은 반복문과 리스트 생성입니다.",
                "feedback": "좋습니다. 반복문 기반 리스트 생성을 더 간결하게 쓰는 개념을 잡았습니다.",
            },
            {
                "question": "`[x * 2 for x in [1, 2, 3]]`의 결과는 무엇일까요?",
                "answer": "[2, 4, 6] 입니다.",
                "hint": "1, 2, 3에 각각 2를 곱한 새 리스트입니다.",
                "feedback": "맞았습니다. 각 원소에 같은 연산을 적용한 새 리스트입니다.",
            },
        ],
        "medium": [
            {
                "question": "[x for x in range(10) if x % 2 == 0]은 무엇을 만드는 코드일까요?",
                "answer": "0부터 9까지 중 짝수만 모은 리스트를 만드는 코드입니다.",
                "hint": "range(10) 전체가 아니라 조건을 만족하는 값만 남습니다.",
                "feedback": "좋습니다. 조건을 써서 원하는 값만 걸러내는 흐름을 이해했습니다.",
            },
        ],
    },
    "파이썬 함수": {
        "easy": [
            {
                "question": "파이썬에서 함수를 만들 때 쓰는 키워드는 무엇일까요?",
                "answer": "def 입니다.",
                "hint": "함수 선언 맨 앞의 3글자 키워드입니다.",
                "feedback": "맞습니다. 함수 선언은 def로 시작합니다.",
            },
            {
                "question": "함수는 왜 사용할까요?",
                "answer": "반복되는 코드를 묶어서 재사용하기 위해 사용합니다.",
                "hint": "핵심은 반복 코드와 재사용입니다.",
                "feedback": "좋습니다. 함수는 같은 동작을 이름 붙여 재사용하게 해줍니다.",
            },
        ],
        "medium": [
            {
                "question": "return을 쓰지 않으면 함수 결과는 보통 무엇이 될까요?",
                "answer": "보통 None이 됩니다.",
                "hint": "아무것도 돌려주지 않을 때의 기본 반환값입니다.",
                "feedback": "정확합니다. return이 없으면 기본적으로 None이 반환됩니다.",
            },
        ],
    },
}

SYSTEM_PROMPT = """
너는 초심자용 적응형 공부 도우미 AI Agent다.
사용자의 공부 상태를 보고, 지금 무엇을 해야 할지 추천하는 것이 목표다.

규칙:
- 사용자의 목표나 실력 수준은 facts에 저장하라.
- 공부 할 일은 tasks에 저장하라.
- 퀴즈가 필요하면 generate_quiz를 사용하라.
- 퀴즈 답 제출에는 grade_quiz_answer를 사용하라.
- 약한 주제를 묻는다면 get_weak_topics를 사용하라.
- 다음 공부 행동을 묻는다면 recommend_next_step을 사용하라.
- 퀴즈 기록을 묻는다면 get_quiz_stats를 사용하라.
- 남은 할 일을 묻는다면 get_pending_tasks를 사용하라.
- 답변은 짧고 쉬운 한국어로 하라.
""".strip()

tools = [
    {
        "name": "save_fact",
        "description": "사용자의 중요한 공부 관련 사실을 저장합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"},
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
                "task": {"type": "string"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "get_pending_tasks",
        "description": "완료되지 않은 공부 할 일만 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_quiz",
        "description": "상태에 맞춰 퀴즈를 만듭니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "grade_quiz_answer",
        "description": "최근 퀴즈의 특정 문제를 채점합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question_number": {"type": "integer"},
                "user_answer": {"type": "string"},
            },
            "required": ["question_number", "user_answer"],
        },
    },
    {
        "name": "get_quiz_stats",
        "description": "누적 퀴즈 기록을 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_weak_topics",
        "description": "약한 주제를 보여줍니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "recommend_next_step",
        "description": "현재 상태를 바탕으로 다음 공부 행동을 추천합니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def memory_path(session_id: str) -> Path:
    return MEMORY_DIR / f"{session_id}.json"


def default_state() -> dict:
    return {
        "messages": [],
        "facts": {},
        "tasks": [],
        "latest_quiz": None,
        "quiz_stats": {"attempted": 0, "correct": 0, "history": []},
    }


def load_state(session_id: str) -> dict:
    path = memory_path(session_id)
    if not path.exists():
        return default_state()

    with path.open("r", encoding="utf-8") as file:
        state = json.load(file)
    state.setdefault("messages", [])
    state.setdefault("facts", {})
    state.setdefault("tasks", [])
    state.setdefault("latest_quiz", None)
    state.setdefault("quiz_stats", {"attempted": 0, "correct": 0, "history": []})
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


def normalize_answer_text(text: str) -> str:
    lowered = re.sub(r"[^0-9a-zA-Z가-힣\[\]\s]", " ", text.strip().lower())
    return " ".join(lowered.split())


def answer_tokens(text: str) -> set[str]:
    return set(normalize_answer_text(text).split())


def pick_topic(topic: str) -> str:
    for known_topic in QUIZ_BANK:
        if known_topic in topic or topic in known_topic:
            return known_topic
    return "파이썬 함수"


def topic_accuracy(state: dict, topic: str) -> tuple[int, int]:
    history = [item for item in state["quiz_stats"]["history"] if item["topic"] == topic]
    attempted = len(history)
    correct = sum(1 for item in history if item["correct"])
    return attempted, correct


def resolve_difficulty(state: dict, topic: str) -> str:
    level = state["facts"].get("학습 수준", "")
    attempted, correct = topic_accuracy(state, topic)
    accuracy = 0.0 if attempted == 0 else (correct / attempted) * 100

    if "초보" in level or "입문" in level:
        return "easy"
    if attempted >= 2 and accuracy < 70:
        return "easy"
    return "medium"


def ensure_review_task(state: dict, topic: str) -> str | None:
    task_name = f"복습: {topic}"
    if any(item["task"] == task_name for item in state["tasks"]):
        return None
    state["tasks"].append({"task": task_name, "done": False})
    return task_name


def tool_save_fact(state: dict, key: str, value: str) -> str:
    state["facts"][key] = value
    return f"fact 저장 완료: {key} = {value}"


def tool_add_task(state: dict, task: str) -> str:
    if any(item["task"] == task for item in state["tasks"]):
        return f"이미 존재하는 할 일입니다: {task}"
    state["tasks"].append({"task": task, "done": False})
    return f"할 일 추가 완료: {task}"


def tool_get_pending_tasks(state: dict) -> str:
    pending = [item["task"] for item in state["tasks"] if not item["done"]]
    if not pending:
        return "남은 할 일이 없습니다."
    return json.dumps(pending, ensure_ascii=False, indent=2)


def tool_generate_quiz(state: dict, topic: str, count: int = 2) -> str:
    selected_topic = pick_topic(topic)
    difficulty = resolve_difficulty(state, selected_topic)
    quiz_items = QUIZ_BANK[selected_topic][difficulty][: max(1, min(count, 2))]
    state["latest_quiz"] = {
        "topic": selected_topic,
        "difficulty": difficulty,
        "items": quiz_items,
    }

    lines = [f"주제: {selected_topic}", f"난이도: {difficulty}", "문제를 먼저 풀어보세요."]
    for index, item in enumerate(quiz_items, start=1):
        lines.append(f"{index}. 질문: {item['question']}")
    return "\n".join(lines)


def tool_get_quiz_stats(state: dict) -> str:
    attempted = state["quiz_stats"]["attempted"]
    correct = state["quiz_stats"]["correct"]
    accuracy = 0.0 if attempted == 0 else (correct / attempted) * 100
    return (
        "누적 퀴즈 기록\n"
        f"- 답안 제출 수: {attempted}\n"
        f"- 정답 수: {correct}\n"
        f"- 정답률: {accuracy:.0f}%"
    )


def tool_get_weak_topics(state: dict) -> str:
    lines = []
    for topic in QUIZ_BANK:
        attempted, correct = topic_accuracy(state, topic)
        if attempted < 2:
            continue
        accuracy = (correct / attempted) * 100
        if accuracy < 70:
            lines.append(f"- {topic}: {correct}/{attempted} 정답, 정답률 {accuracy:.0f}%")

    if not lines:
        return "아직 뚜렷하게 약한 주제는 없습니다."
    return "약한 주제\n" + "\n".join(lines)


def tool_recommend_next_step(state: dict) -> str:
    weak_topics = tool_get_weak_topics(state)
    if weak_topics != "아직 뚜렷하게 약한 주제는 없습니다.":
        first_topic = weak_topics.splitlines()[1].split(":")[0].replace("- ", "").strip()
        return (
            "추천 다음 단계\n"
            f"- 우선 복습할 주제: {first_topic}\n"
            f"- 추천 행동: {first_topic} 쉬운 퀴즈 2문제 다시 풀기"
        )

    pending = [item["task"] for item in state["tasks"] if not item["done"]]
    if pending:
        return f"추천 다음 단계\n- 먼저 남은 할 일부터 진행하세요: {pending[0]}"

    return "추천 다음 단계\n- 파이썬 함수 또는 리스트 컴프리헨션으로 쉬운 퀴즈를 풀어보세요."


def tool_grade_quiz_answer(state: dict, question_number: int, user_answer: str) -> str:
    latest_quiz = state.get("latest_quiz")
    if not latest_quiz:
        return "아직 채점할 퀴즈가 없습니다."
    if question_number < 1 or question_number > len(latest_quiz["items"]):
        return f"{question_number}번 문제는 최근 퀴즈에 없습니다."

    quiz_item = latest_quiz["items"][question_number - 1]
    expected_tokens = answer_tokens(quiz_item["answer"])
    submitted_tokens = answer_tokens(user_answer)
    overlap = 0.0 if not submitted_tokens else len(expected_tokens & submitted_tokens) / len(submitted_tokens)
    is_match = overlap >= 0.6 or normalize_answer_text(user_answer) in normalize_answer_text(quiz_item["answer"])

    state["quiz_stats"]["attempted"] += 1
    if is_match:
        state["quiz_stats"]["correct"] += 1
    state["quiz_stats"]["history"].append(
        {
            "topic": latest_quiz["topic"],
            "question_number": question_number,
            "correct": is_match,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    state["quiz_stats"]["history"] = state["quiz_stats"]["history"][-20:]

    attempted, correct = topic_accuracy(state, latest_quiz["topic"])
    accuracy = (correct / attempted) * 100 if attempted else 0.0
    review_task = None
    if attempted >= 2 and accuracy < 60:
        review_task = ensure_review_task(state, latest_quiz["topic"])

    extra = ""
    if review_task:
        extra = f"\n- 추가된 할 일: {review_task}\n- 이유: {latest_quiz['topic']} 정답률이 {accuracy:.0f}%입니다."

    if is_match:
        return (
            f"{question_number}번 정답입니다.\n"
            f"- 질문: {quiz_item['question']}\n"
            f"- 피드백: {quiz_item['feedback']}"
            f"{extra}"
        )

    return (
        f"{question_number}번은 아직 정답으로 보기 어렵습니다.\n"
        f"- 질문: {quiz_item['question']}\n"
        f"- 힌트: {quiz_item['hint']}\n"
        f"- 정답이 궁금하면 다시 물어보세요."
        f"{extra}"
    )


def execute_tool(state: dict, name: str, inputs: dict) -> str:
    if name == "save_fact":
        return tool_save_fact(state, inputs["key"], inputs["value"])
    if name == "add_task":
        return tool_add_task(state, inputs["task"])
    if name == "get_pending_tasks":
        return tool_get_pending_tasks(state)
    if name == "generate_quiz":
        return tool_generate_quiz(state, inputs["topic"], inputs.get("count", 2))
    if name == "grade_quiz_answer":
        return tool_grade_quiz_answer(state, inputs["question_number"], inputs["user_answer"])
    if name == "get_quiz_stats":
        return tool_get_quiz_stats(state)
    if name == "get_weak_topics":
        return tool_get_weak_topics(state)
    if name == "recommend_next_step":
        return tool_recommend_next_step(state)
    return f"알 수 없는 tool입니다: {name}"


def build_context_message(state: dict) -> str:
    return (
        "현재 공부 상태 요약입니다.\n"
        f"- facts: {json.dumps(state['facts'], ensure_ascii=False)}\n"
        f"- tasks: {json.dumps(state['tasks'], ensure_ascii=False)}\n"
        f"- quiz_stats: {json.dumps(state['quiz_stats'], ensure_ascii=False)}\n"
    )


def run_agent(user_message: str, session_id: str = "student_adaptive") -> None:
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
    print("=== Day 8: Adaptive Study Agent ===")
    print("상태를 보고 다음 공부 행동을 추천하는 적응형 예제입니다.")

    run_agent("나는 파이썬 초보자야. 리스트 컴프리헨션과 함수를 공부 중이야. 기억해줘.")
    run_agent("리스트 컴프리헨션 확인 문제 2개 내줘.")
    run_agent("1번 답은 잘 모르겠어.")
    run_agent("2번 답은 잘 모르겠어.")
    run_agent("내 약한 주제 보여줘.")
    run_agent("지금 다음에 뭘 공부하면 좋을지 추천해줘.")
