"""
Day 7: Web Study Assistant
- 06_study_assistant.py에 web_search를 추가한 확장판
- 모르는 공부 개념을 검색하고, 필요한 내용을 기억하거나 파일로 저장

이 파일의 목표:
- "기억하는 Agent"에 "검색하는 능력"을 붙여 본다.
- 사용자의 공부 질문이 들어오면 필요한 경우 웹 검색을 사용하게 만든다.
- 검색 결과를 바탕으로 공부 요약이나 할 일을 정리하게 만든다.

핵심 아이디어:
- web_search: 공부 개념이나 참고 정보를 검색
- generate_quiz: 공부 주제에 맞는 짧은 확인 문제 생성
- reveal_quiz_answers: 방금 낸 퀴즈의 정답만 나중에 확인
- grade_quiz_answer: 사용자의 퀴즈 답을 간단히 채점
- get_quiz_stats: 누적 퀴즈 기록 확인
- facts: 사용자의 선호 과목, 목표, 수준 저장
- tasks: 공부 할 일 관리
- write_file: 검색 결과 요약이나 공부 정리본 저장
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import json
import re

import anthropic
from dotenv import load_dotenv
import requests


load_dotenv(override=True)
client = anthropic.Anthropic()

MODEL_NAME = "claude-haiku-4-5-20251001"
BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"
HTTP_HEADERS = {
    "User-Agent": "study-agent-demo/0.1 (educational project)",
}
SEARCH_FILLER_WORDS = {
    "검색",
    "검색해서",
    "설명",
    "설명해줘",
    "알려줘",
    "찾아줘",
    "찾아",
    "정리",
    "정리해줘",
    "쉬운",
    "쉽게",
    "초보자",
    "입문",
    "개념",
    "자료",
    "뭔지",
    "무엇",
    "뭐야",
}
SEARCH_TERM_TRANSLATIONS = {
    "파이썬": "python",
    "리스트 컴프리헨션": "list comprehension",
    "딕셔너리 컴프리헨션": "dictionary comprehension",
    "제너레이터": "generator",
    "반복문": "for loop",
    "조건문": "if statement",
    "함수": "function",
    "클래스": "class",
    "변수": "variable",
    "리스트": "list",
    "튜플": "tuple",
    "딕셔너리": "dictionary",
    "집합": "set",
}
QUIZ_BANK = {
    "리스트 컴프리헨션": [
        {
            "question": "리스트 컴프리헨션은 무엇을 짧게 표현하기 위한 문법일까요?",
            "answer": "반복문으로 리스트를 만드는 코드를 짧게 표현하기 위한 문법입니다.",
            "hint": "핵심은 '반복문'과 '리스트를 짧게 만드는 문법'입니다.",
            "feedback": "좋습니다. 리스트 컴프리헨션은 반복문 기반 리스트 생성을 더 간결하게 쓸 때 유용합니다.",
        },
        {
            "question": "`[x * 2 for x in [1, 2, 3]]`의 결과는 무엇일까요?",
            "answer": "[2, 4, 6] 입니다.",
            "hint": "원소 1, 2, 3에 각각 2를 곱한 뒤 새 리스트를 만든다고 생각해보세요.",
            "feedback": "맞았습니다. 각 원소에 같은 연산을 적용한 새 리스트를 만든 예시입니다.",
        },
        {
            "question": "리스트 컴프리헨션에서 조건을 넣고 싶으면 보통 어디에 `if`를 붙일까요?",
            "answer": "for 뒤에 붙입니다. 예: [x for x in nums if x > 0]",
            "hint": "`if`는 보통 맨 앞이 아니라 반복 부분 뒤쪽에 따라옵니다.",
            "feedback": "좋습니다. 조건은 보통 `for ... in ...` 뒤에 붙여서 필터링합니다.",
        },
        {
            "question": "리스트 컴프리헨션이 항상 좋은 것은 아닌데, 너무 길어지면 무엇이 나빠질까요?",
            "answer": "코드 가독성이 나빠질 수 있습니다.",
            "hint": "짧고 읽기 쉬워야 좋은데, 너무 길어지면 오히려 읽기 어려워집니다.",
            "feedback": "맞습니다. 너무 복잡한 컴프리헨션은 읽기 어려워져서 오히려 유지보수성이 떨어집니다.",
        },
    ],
    "파이썬 함수": [
        {
            "question": "파이썬에서 함수를 만들 때 쓰는 키워드는 무엇일까요?",
            "answer": "def 입니다.",
            "hint": "함수를 정의할 때 맨 앞에 쓰는 3글자 키워드입니다.",
            "feedback": "맞습니다. 파이썬 함수 선언은 `def`로 시작합니다.",
        },
        {
            "question": "함수는 왜 사용할까요?",
            "answer": "반복되는 코드를 묶어서 재사용하기 위해 사용합니다.",
            "hint": "핵심은 '반복 코드'와 '재사용'입니다.",
            "feedback": "좋습니다. 함수는 같은 동작을 이름 붙여 재사용하게 해줍니다.",
        },
        {
            "question": "함수의 입력값은 보통 무엇이라고 부를까요?",
            "answer": "매개변수 또는 파라미터라고 부릅니다.",
            "hint": "영어로는 parameter라고도 부릅니다.",
            "feedback": "맞습니다. 함수 선언부의 입력값은 매개변수, 파라미터라고 부릅니다.",
        },
        {
            "question": "함수 결과를 돌려줄 때 쓰는 키워드는 무엇일까요?",
            "answer": "return 입니다.",
            "hint": "함수 바깥으로 값을 되돌려줄 때 쓰는 영단어입니다.",
            "feedback": "정확합니다. 함수 결과를 호출한 곳으로 돌려줄 때 `return`을 사용합니다.",
        },
    ],
    "파이썬 기초": [
        {
            "question": "리스트는 여러 값을 어떤 기호 안에 넣어 저장할까요?",
            "answer": "대괄호 [] 안에 넣어 저장합니다.",
            "hint": "튜플의 소괄호와 구분해서 떠올려보세요.",
            "feedback": "맞습니다. 리스트는 보통 대괄호 `[]`로 표현합니다.",
        },
        {
            "question": "조건에 따라 다른 코드를 실행할 때 많이 쓰는 문법은 무엇일까요?",
            "answer": "if 문입니다.",
            "hint": "조건문에서 가장 기본이 되는 두 글자 키워드입니다.",
            "feedback": "좋습니다. 조건 분기는 가장 기본적으로 `if` 문으로 시작합니다.",
        },
        {
            "question": "반복해서 코드를 실행할 때 자주 쓰는 두 문법은 무엇일까요?",
            "answer": "for 문과 while 문입니다.",
            "hint": "하나는 횟수/순회용, 하나는 조건이 참인 동안 반복하는 문법입니다.",
            "feedback": "맞습니다. 대표적인 반복문은 `for`와 `while`입니다.",
        },
        {
            "question": "문자열, 숫자, 리스트 같은 값의 종류를 무엇이라고 부를까요?",
            "answer": "자료형 또는 데이터 타입이라고 부릅니다.",
            "hint": "영어로는 data type이라고 부릅니다.",
            "feedback": "정확합니다. 값의 종류는 자료형 또는 데이터 타입이라고 합니다.",
        },
    ],
}

SYSTEM_PROMPT = """
너는 초심자용 웹 검색 공부 도우미 AI Agent다.
사용자의 공부 질문을 돕고, 공부 정보와 할 일을 정리하는 것이 목표다.

규칙:
- 사용자의 취향, 목표, 선호 과목, 실력 수준은 facts에 저장하라.
- 공부 할 일은 tasks에 저장하라.
- 사용자가 모르는 개념 설명이나 자료 탐색을 원하면 web_search를 사용하라.
- 사용자가 퀴즈, 확인 문제, 연습 문제를 원하면 generate_quiz를 사용하라.
- 사용자가 방금 낸 퀴즈의 정답이나 해설을 원하면 reveal_quiz_answers를 사용하라.
- 사용자가 퀴즈 답을 제출하면 grade_quiz_answer를 사용하라.
- 사용자가 퀴즈 기록, 정답 개수, 맞힌 개수를 물으면 get_quiz_stats를 사용하라.
- 사용자가 할 일을 지워 달라고 하면 delete_task를 사용하라.
- 사용자가 남은 할 일만 물으면 get_pending_tasks를 사용하라.
- 사용자가 끝낸 할 일만 물으면 get_completed_tasks를 사용하라.
- 사용자가 정리본 저장을 원하면 write_file을 사용하라.
- 기억을 확인해야 하면 get_memory를 사용하라.
- 검색 결과는 그대로 길게 복사하지 말고, 쉬운 한국어로 짧게 정리하라.
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
        "name": "delete_task",
        "description": "기존 공부 할 일을 삭제합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "삭제할 공부 할 일"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "get_pending_tasks",
        "description": "완료되지 않은 공부 할 일만 보여줍니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_completed_tasks",
        "description": "완료한 공부 할 일만 보여줍니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
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
        "description": "정리한 공부 메모나 요약을 파일로 저장합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "저장할 파일 경로"},
                "content": {"type": "string", "description": "파일에 저장할 내용"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "web_search",
        "description": "공부 개념이나 참고 자료를 웹에서 검색합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색할 주제"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_quiz",
        "description": "공부 주제에 맞는 짧은 퀴즈를 만듭니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "퀴즈 주제"},
                "count": {"type": "integer", "description": "문제 수"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "reveal_quiz_answers",
        "description": "가장 최근에 만든 퀴즈의 정답을 보여줍니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "grade_quiz_answer",
        "description": "가장 최근 퀴즈의 특정 문제에 대한 사용자의 답을 채점합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question_number": {
                    "type": "integer",
                    "description": "채점할 문제 번호",
                },
                "user_answer": {
                    "type": "string",
                    "description": "사용자가 제출한 답",
                },
            },
            "required": ["question_number", "user_answer"],
        },
    },
    {
        "name": "get_quiz_stats",
        "description": "지금까지의 누적 퀴즈 기록을 보여줍니다.",
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
        "latest_quiz": None,
        "quiz_stats": {
            "attempted": 0,
            "correct": 0,
            "history": [],
        },
    }


def normalize_state(state: dict) -> dict:
    state.setdefault("messages", [])
    state.setdefault("facts", {})
    state.setdefault("tasks", [])
    state.setdefault("latest_quiz", None)
    state.setdefault(
        "quiz_stats",
        {
            "attempted": 0,
            "correct": 0,
            "history": [],
        },
    )
    return state


def load_state(session_id: str) -> dict:
    path = memory_path(session_id)
    if not path.exists():
        return default_state()

    with path.open("r", encoding="utf-8") as file:
        return normalize_state(json.load(file))


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


def tool_delete_task(state: dict, task: str) -> str:
    for index, item in enumerate(state["tasks"]):
        if item["task"] == task:
            del state["tasks"][index]
            return f"할 일 삭제 완료: {task}"
    return f"삭제할 할 일을 찾지 못했습니다: {task}"


def tool_get_pending_tasks(state: dict) -> str:
    pending_tasks = [item["task"] for item in state["tasks"] if not item["done"]]
    if not pending_tasks:
        return "남은 할 일이 없습니다."
    return json.dumps(pending_tasks, ensure_ascii=False, indent=2)


def tool_get_completed_tasks(state: dict) -> str:
    completed_tasks = [item["task"] for item in state["tasks"] if item["done"]]
    if not completed_tasks:
        return "완료한 할 일이 없습니다."
    return json.dumps(completed_tasks, ensure_ascii=False, indent=2)


def tool_get_memory(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2)


def tool_write_file(path: str, content: str) -> str:
    full_path = (BASE_DIR / path).resolve() if not Path(path).is_absolute() else Path(path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with full_path.open("w", encoding="utf-8") as file:
        file.write(content)
    return f"파일 저장 완료: {full_path}"


def strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def normalize_answer_text(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"`", "", lowered)
    lowered = re.sub(r"[^0-9a-zA-Z가-힣\[\]\s]", " ", lowered)
    return " ".join(lowered.split())


def answer_tokens(text: str) -> list[str]:
    suffixes = (
        "입니다",
        "이다",
        "하는",
        "하다",
        "위한",
        "입니다",
        "이야",
        "예요",
        "이에요",
    )
    tokens = []
    for token in normalize_answer_text(text).split():
        simplified = token
        for suffix in suffixes:
            if simplified.endswith(suffix) and len(simplified) > len(suffix) + 1:
                simplified = simplified[: -len(suffix)]
                break
        if simplified:
            tokens.append(simplified)
    return tokens


def build_search_queries(query: str) -> list[str]:
    candidates: list[str] = []
    original = " ".join(query.split()).strip()
    if original:
        candidates.append(original)

    cleaned_words = [
        word
        for word in re.split(r"\s+", original)
        if word and word not in SEARCH_FILLER_WORDS
    ]
    cleaned = " ".join(cleaned_words).strip()
    if cleaned and cleaned not in candidates:
        candidates.append(cleaned)

    translated = cleaned or original
    for source, target in SEARCH_TERM_TRANSLATIONS.items():
        translated = translated.replace(source, target)
    translated = " ".join(translated.split()).strip()
    if translated and translated not in candidates:
        candidates.append(translated)

    return candidates


def search_duckduckgo(query: str) -> str:
    response = requests.get(
        "https://api.duckduckgo.com/",
        params={
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "kl": "kr-kr",
        },
        headers=HTTP_HEADERS,
        timeout=5,
    )
    data = response.json()

    if data.get("AbstractText"):
        return data["AbstractText"]

    topics = []
    for item in data.get("RelatedTopics", []):
        if isinstance(item, dict) and item.get("Text"):
            topics.append(item["Text"])
        elif isinstance(item, dict) and item.get("Topics"):
            for sub_item in item["Topics"]:
                if isinstance(sub_item, dict) and sub_item.get("Text"):
                    topics.append(sub_item["Text"])

    if topics:
        return "\n".join(topics[:3])

    return ""


def search_wikipedia(query: str) -> str:
    for language in ("ko", "en"):
        search_response = requests.get(
            f"https://{language}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "utf8": "1",
                "srlimit": 1,
            },
            headers=HTTP_HEADERS,
            timeout=5,
        )
        search_data = search_response.json()
        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            continue

        first_result = search_results[0]
        title = first_result["title"]
        summary_response = requests.get(
            f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
            headers=HTTP_HEADERS,
            timeout=5,
        )

        if summary_response.ok:
            summary_data = summary_response.json()
            extract = summary_data.get("extract", "").strip()
            if extract:
                return f"[Wikipedia {language}] {title}: {extract}"

        snippet = strip_html_tags(first_result.get("snippet", "")).strip()
        if snippet:
            return f"[Wikipedia {language}] {title}: {snippet}"

    return ""


def pick_quiz_topic(topic: str) -> str:
    normalized = " ".join(topic.split()).strip()
    for known_topic in QUIZ_BANK:
        if known_topic in normalized or normalized in known_topic:
            return known_topic
    return "파이썬 기초"


def tool_generate_quiz(state: dict, topic: str, count: int = 3) -> str:
    selected_topic = pick_quiz_topic(topic)
    quiz_items = QUIZ_BANK[selected_topic]
    safe_count = max(1, min(count, len(quiz_items)))

    selected_quiz = quiz_items[:safe_count]
    state["latest_quiz"] = {
        "topic": selected_topic,
        "items": selected_quiz,
    }

    lines = [f"주제: {selected_topic}", "문제를 먼저 풀어보세요."]
    for index, item in enumerate(selected_quiz, start=1):
        lines.append(f"{index}. 질문: {item['question']}")

    return "\n".join(lines)


def tool_reveal_quiz_answers(state: dict) -> str:
    latest_quiz = state.get("latest_quiz")
    if not latest_quiz:
        return "아직 만든 퀴즈가 없습니다."

    lines = [f"주제: {latest_quiz['topic']}", "최근 퀴즈 정답입니다."]
    for index, item in enumerate(latest_quiz["items"], start=1):
        lines.append(f"{index}. 정답: {item['answer']}")

    return "\n".join(lines)


def tool_get_quiz_stats(state: dict) -> str:
    quiz_stats = state.get("quiz_stats", {})
    attempted = quiz_stats.get("attempted", 0)
    correct = quiz_stats.get("correct", 0)
    history = quiz_stats.get("history", [])
    accuracy = 0.0 if attempted == 0 else (correct / attempted) * 100

    lines = [
        "누적 퀴즈 기록",
        f"- 답안 제출 수: {attempted}",
        f"- 정답 수: {correct}",
        f"- 정답률: {accuracy:.0f}%",
    ]

    if history:
        lines.append("- 최근 기록:")
        for item in history[-3:]:
            verdict = "정답" if item["correct"] else "오답"
            lines.append(
                f"  {item['question_number']}번 {verdict} ({item['topic']})"
            )

    return "\n".join(lines)


def ensure_review_task(state: dict, topic: str) -> str | None:
    review_task = f"복습: {topic}"
    existing = next((item for item in state["tasks"] if item["task"] == review_task), None)
    if existing:
        return None

    state["tasks"].append({"task": review_task, "done": False})
    return review_task


def topic_quiz_accuracy(state: dict, topic: str) -> tuple[int, int]:
    history = state.get("quiz_stats", {}).get("history", [])
    topic_history = [item for item in history if item["topic"] == topic]
    attempted = len(topic_history)
    correct = sum(1 for item in topic_history if item["correct"])
    return attempted, correct


def tool_grade_quiz_answer(state: dict, question_number: int, user_answer: str) -> str:
    latest_quiz = state.get("latest_quiz")
    if not latest_quiz:
        return "아직 채점할 퀴즈가 없습니다."

    if question_number < 1 or question_number > len(latest_quiz["items"]):
        return f"{question_number}번 문제는 최근 퀴즈에 없습니다."

    quiz_item = latest_quiz["items"][question_number - 1]
    expected = normalize_answer_text(quiz_item["answer"])
    submitted = normalize_answer_text(user_answer)
    expected_tokens = set(answer_tokens(quiz_item["answer"]))
    submitted_tokens = set(answer_tokens(user_answer))
    overlap_ratio = 0.0
    if submitted_tokens:
        overlap_ratio = len(expected_tokens & submitted_tokens) / len(submitted_tokens)

    is_match = (
        submitted == expected
        or submitted in expected
        or expected in submitted
        or overlap_ratio >= 0.6
    )
    quiz_stats = state["quiz_stats"]
    quiz_stats["attempted"] += 1
    if is_match:
        quiz_stats["correct"] += 1
    quiz_stats["history"].append(
        {
            "topic": latest_quiz["topic"],
            "question_number": question_number,
            "correct": is_match,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    quiz_stats["history"] = quiz_stats["history"][-20:]
    topic_attempted, topic_correct = topic_quiz_accuracy(state, latest_quiz["topic"])
    topic_accuracy = 0.0 if topic_attempted == 0 else (topic_correct / topic_attempted) * 100
    review_task_added = None
    if topic_attempted >= 2 and topic_accuracy < 60:
        review_task_added = ensure_review_task(state, latest_quiz["topic"])

    if is_match:
        extra_line = ""
        if review_task_added:
            extra_line = (
                f"\n- 추가된 할 일: {review_task_added}"
                f"\n- 이유: {latest_quiz['topic']} 주제 정답률이 {topic_accuracy:.0f}%로 낮습니다."
            )
        return (
            f"{question_number}번 정답입니다.\n"
            f"- 질문: {quiz_item['question']}\n"
            f"- 제출한 답: {user_answer}\n"
            f"- 피드백: {quiz_item.get('feedback', '핵심을 잘 짚었습니다.')}"
            f"{extra_line}"
        )

    extra_line = ""
    if review_task_added:
        extra_line = (
            f"\n- 추가된 할 일: {review_task_added}"
            f"\n- 이유: {latest_quiz['topic']} 주제 정답률이 {topic_accuracy:.0f}%로 낮습니다."
        )

    return (
        f"{question_number}번은 아직 정답으로 보기 어렵습니다.\n"
        f"- 질문: {quiz_item['question']}\n"
        f"- 제출한 답: {user_answer}\n"
        f"- 힌트: {quiz_item.get('hint', '정답의 핵심 단어를 다시 떠올려보세요.')}\n"
        f"- 정답 확인이 필요하면 '방금 낸 퀴즈 정답 보여줘'라고 말해보세요."
        f"{extra_line}"
    )


def tool_web_search(query: str) -> str:
    try:
        for candidate in build_search_queries(query):
            duckduckgo_result = search_duckduckgo(candidate)
            if duckduckgo_result:
                return duckduckgo_result

            wikipedia_result = search_wikipedia(candidate)
            if wikipedia_result:
                return wikipedia_result

        return f"'{query}' 검색 결과를 찾지 못했습니다."
    except Exception as error:
        return f"검색 오류: {error}"


def execute_tool(state: dict, name: str, inputs: dict) -> str:
    if name == "save_fact":
        return tool_save_fact(state, inputs["key"], inputs["value"])
    if name == "add_task":
        return tool_add_task(state, inputs["task"])
    if name == "complete_task":
        return tool_complete_task(state, inputs["task"])
    if name == "delete_task":
        return tool_delete_task(state, inputs["task"])
    if name == "get_pending_tasks":
        return tool_get_pending_tasks(state)
    if name == "get_completed_tasks":
        return tool_get_completed_tasks(state)
    if name == "get_memory":
        return tool_get_memory(state)
    if name == "write_file":
        return tool_write_file(inputs["path"], inputs["content"])
    if name == "web_search":
        return tool_web_search(inputs["query"])
    if name == "generate_quiz":
        return tool_generate_quiz(state, inputs["topic"], inputs.get("count", 3))
    if name == "reveal_quiz_answers":
        return tool_reveal_quiz_answers(state)
    if name == "grade_quiz_answer":
        return tool_grade_quiz_answer(
            state,
            inputs["question_number"],
            inputs["user_answer"],
        )
    if name == "get_quiz_stats":
        return tool_get_quiz_stats(state)
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


def run_agent(user_message: str, session_id: str = "student_web") -> None:
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
                print(f"  Tool 결과: {result[:120]}{'...' if len(result) > 120 else ''}")
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
    print("=== Day 7: Web Study Assistant ===")
    print("검색과 기억을 함께 쓰는 공부 도우미 예제입니다.")

    run_agent("나는 파이썬 기초를 공부 중인 초보자야. 기억해줘.")
    run_agent("리스트 컴프리헨션이 뭔지 검색해서 쉬운 말로 설명해줘.")
    run_agent("리스트 컴프리헨션 연습 문제 3개를 내 공부 할 일에 추가해줘.")
    run_agent("리스트 컴프리헨션 확인 문제 3개 내줘.")
    run_agent("1번 답은 반복문으로 리스트를 짧게 만드는 문법이야.")
    run_agent("내 퀴즈 기록 보여줘.")
    run_agent("방금 낸 퀴즈 정답 보여줘.")
    run_agent("남은 할 일만 보여줘.")
    run_agent("지금까지 검색하고 기억한 내용을 python_study_note.txt로 정리해서 저장해줘.")
