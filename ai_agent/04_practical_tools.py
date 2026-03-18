"""
Day 3-4: 실용 Tool 3종 세트
- web_search: DuckDuckGo로 실제 웹 검색
- read_file / write_file: 로컬 파일 읽기/쓰기
- run_python: 코드 실행

03_agentic_loop.py와 비교:
- mock 데이터 → 실제 외부 연동
- tool 3개 조합으로 복합 태스크 처리 가능
"""

from dotenv import load_dotenv
import anthropic
import json
import os
import requests
import subprocess
import sys
import tempfile

load_dotenv(override=True)
client = anthropic.Anthropic()

# ── Tool 정의 ─────────────────────────────────────────────
tools = [
    {
        "name": "web_search",
        "description": "DuckDuckGo로 웹을 검색합니다. 최신 정보나 모르는 내용을 찾을 때 사용하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색 키워드"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_file",
        "description": "로컬 파일의 내용을 읽습니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "읽을 파일 경로"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "로컬 파일에 내용을 씁니다. 파일이 없으면 생성합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "쓸 파일 경로"},
                "content": {"type": "string", "description": "파일에 쓸 내용"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "run_python",
        "description": "Python 코드를 실행하고 결과를 반환합니다. 계산, 데이터 처리 등에 사용하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "실행할 Python 코드"}
            },
            "required": ["code"]
        }
    }
]

# ── Tool 실행 함수 ─────────────────────────────────────────
def execute_tool(name: str, inputs: dict) -> str:
    if name == "web_search":
        return tool_web_search(inputs["query"])
    elif name == "read_file":
        return tool_read_file(inputs["path"])
    elif name == "write_file":
        return tool_write_file(inputs["path"], inputs["content"])
    elif name == "run_python":
        return tool_run_python(inputs["code"])
    return "알 수 없는 tool"


def tool_web_search(query: str) -> str:
    """DuckDuckGo Instant Answer API로 검색"""
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        res = requests.get(url, params=params, timeout=5)
        data = res.json()

        # AbstractText가 있으면 반환
        if data.get("AbstractText"):
            return data["AbstractText"]

        # RelatedTopics에서 첫 번째 결과
        topics = data.get("RelatedTopics", [])
        results = []
        for t in topics[:3]:
            if isinstance(t, dict) and t.get("Text"):
                results.append(t["Text"])

        if results:
            return "\n".join(results)

        return f"'{query}' 검색 결과를 찾지 못했습니다."
    except Exception as e:
        return f"검색 오류: {e}"


def tool_read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"파일을 찾을 수 없습니다: {path}"
    except Exception as e:
        return f"파일 읽기 오류: {e}"


def tool_write_file(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"파일 저장 완료: {path}"
    except Exception as e:
        return f"파일 쓰기 오류: {e}"


def tool_run_python(code: str) -> str:
    """임시 파일에 코드 저장 후 서브프로세스로 실행"""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            timeout=10,
            env=env
        )
        result.stdout = result.stdout.decode("utf-8", errors="replace")
        result.stderr = result.stderr.decode("utf-8", errors="replace")
        os.unlink(tmp_path)

        output = result.stdout.strip()
        error = result.stderr.strip()

        if error:
            return f"오류:\n{error}"
        return output if output else "(출력 없음)"
    except subprocess.TimeoutExpired:
        return "실행 시간 초과 (10초)"
    except Exception as e:
        return f"실행 오류: {e}"


# ── Agentic Loop (03과 동일한 구조) ───────────────────────
def run_agent(user_message: str):
    print(f"\n사용자: {user_message}")
    print("=" * 50)

    messages = [{"role": "user", "content": user_message}]
    step = 0

    while True:
        step += 1
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            tools=tools,
            messages=messages
        )

        print(f"[Step {step}] stop_reason: {response.stop_reason}")

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"최종 답변:\n{block.text}")
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool 호출: {block.name}({json.dumps(block.input, ensure_ascii=False)[:80]})")
                    result = execute_tool(block.name, block.input)
                    print(f"  Tool 결과: {result[:100]}{'...' if len(result) > 100 else ''}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})


# ── 테스트 ────────────────────────────────────────────────
if __name__ == "__main__":
    # 케이스 1: 파이썬 코드 실행
    run_agent("1부터 10까지 합을 파이썬으로 계산해줘")

    # 케이스 2: 파일 쓰기 + 읽기
    run_agent("'안녕하세요, AI Agent입니다!'라는 내용을 hello.txt에 저장하고, 저장됐는지 확인해줘")

    # 케이스 3: 웹 검색
    run_agent("Python이 뭔지 검색해서 알려줘")
