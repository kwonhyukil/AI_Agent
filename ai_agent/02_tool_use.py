"""
Day 1: Tool Use 이해
- tool 정의 방법
- LLM이 tool을 선택하는 흐름
- tool result를 다시 LLM에 넘기는 흐름
"""

from dotenv import load_dotenv
import anthropic
import json

load_dotenv(override=True)
client = anthropic.Anthropic()

# ── 1. Tool 정의 ──────────────────────────────────────────
tools = [
    {
        "name": "get_weather",
        "description": "특정 도시의 현재 날씨를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "날씨를 조회할 도시 이름"
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "calculate",
        "description": "두 수를 더하거나 곱합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "operation": {
                    "type": "string",
                    "enum": ["add", "multiply"]
                }
            },
            "required": ["a", "b", "operation"]
        }
    }
]

# ── 2. Tool 실행 함수 (실제로는 API 호출 등) ──────────────
def execute_tool(name: str, inputs: dict) -> str:
    if name == "get_weather":
        # 실제 날씨 API 대신 mock 데이터
        weather_data = {
            "서울": "맑음, 15도",
            "부산": "흐림, 18도",
            "제주": "비, 20도",
        }
        city = inputs["city"]
        return weather_data.get(city, f"{city}의 날씨 정보를 찾을 수 없습니다.")

    elif name == "calculate":
        a, b = inputs["a"], inputs["b"]
        if inputs["operation"] == "add":
            return str(a + b)
        elif inputs["operation"] == "multiply":
            return str(a * b)

    return "알 수 없는 tool"

# ── 3. Tool use 흐름 실행 ─────────────────────────────────
def run_with_tool(user_message: str):
    print(f"\n사용자: {user_message}")
    print("-" * 40)

    messages = [{"role": "user", "content": user_message}]

    # LLM 호출 → tool 선택
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    print(f"stop_reason: {response.stop_reason}")

    # tool_use가 아니면 바로 출력
    if response.stop_reason != "tool_use":
        print(f"Claude: {response.content[0].text}")
        return

    # tool_use 블록 찾기
    for block in response.content:
        if block.type == "tool_use":
            print(f"Tool 호출: {block.name}({json.dumps(block.input, ensure_ascii=False)})")

            # tool 실행
            result = execute_tool(block.name, block.input)
            print(f"Tool 결과: {result}")

            # tool 결과를 포함해 LLM 재호출
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                }]
            })

    # 최종 응답
    final_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    print(f"Claude: {final_response.content[0].text}")


# ── 테스트 ────────────────────────────────────────────────
if __name__ == "__main__":
    run_with_tool("서울 날씨 어때?")
    run_with_tool("23 곱하기 47은?")
    run_with_tool("안녕!")  # tool 없이 바로 응답하는 케이스
