"""
Day 2: Agentic Loop
- while loop으로 tool을 목표 달성까지 반복 호출
- stop_reason == "end_turn" 이 될 때까지 계속
- 02_tool_use.py와 비교: tool 호출이 1번 → N번으로 확장
"""

from dotenv import load_dotenv
import anthropic
import json

load_dotenv(override=True)
client = anthropic.Anthropic()

# ── Tool 정의 ─────────────────────────────────────────────
tools = [
    {
        "name": "get_weather",
        "description": "특정 도시의 현재 날씨를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "조회할 도시"}
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
                "operation": {"type": "string", "enum": ["add", "multiply"]}
            },
            "required": ["a", "b", "operation"]
        }
    }
]

def execute_tool(name: str, inputs: dict) -> str:
    if name == "get_weather":
        data = {"서울": "맑음 15도", "부산": "흐림 18도", "제주": "비 20도"}
        return data.get(inputs["city"], "정보 없음")
    elif name == "calculate":
        a, b = inputs["a"], inputs["b"]
        if inputs["operation"] == "add":
            return str(a + b)
        elif inputs["operation"] == "multiply":
            return str(a * b)
    return "알 수 없는 tool"

# ── Agentic Loop ───────────────────────────────────────────
def run_agent(user_message: str):
    print(f"\n사용자: {user_message}")
    print("=" * 50)

    messages = [{"role": "user", "content": user_message}]
    step = 0

    # 핵심: end_turn이 될 때까지 반복
    while True:
        step += 1
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        print(f"[Step {step}] stop_reason: {response.stop_reason}")

        # 목표 달성 → 루프 종료
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"최종 답변: {block.text}")
            break

        # tool_use → 실행 후 결과를 messages에 추가하고 계속
        if response.stop_reason == "tool_use":
            # assistant 메시지 추가
            messages.append({"role": "assistant", "content": response.content})

            # 모든 tool 호출 처리 (한 번에 여러 tool 호출 가능)
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool 호출: {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                    result = execute_tool(block.name, block.input)
                    print(f"  Tool 결과: {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # tool 결과를 messages에 추가
            messages.append({"role": "user", "content": tool_results})


# ── 테스트 ────────────────────────────────────────────────
if __name__ == "__main__":
    # 케이스 1: tool 1번
    run_agent("서울 날씨 알려줘")

    # 케이스 2: tool 2번 연속 (날씨 조회 후 계산)
    run_agent("서울이랑 부산 날씨 둘 다 알려줘")

    # 케이스 3: tool 없이 바로 답변
    run_agent("AI Agent가 뭔지 한 줄로 설명해줘")
