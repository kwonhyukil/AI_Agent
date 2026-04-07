"""
02_streaming.py - 스트리밍 응답 처리

배울 것:
- 일반 응답 vs 스트리밍 응답의 차이
- stream=True 로 실시간 토큰 수신
- with 구문으로 스트림 관리
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

# =============================================
# 방법 1: 일반 응답 (응답 완성까지 기다림)
# =============================================
print("=== 일반 응답 (기다렸다가 한번에 출력) ===")
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "1부터 5까지 천천히 세면서 각 숫자를 설명해줘"}
    ]
)
print(message.content[0].text)

# =============================================
# 방법 2: 스트리밍 응답 (토큰 단위로 실시간 수신)
# =============================================
print("\n=== 스트리밍 응답 (실시간 출력) ===")
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "1부터 5까지 천천히 세면서 각 숫자를 설명해줘"}
    ]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)  # 토큰이 올 때마다 즉시 출력

print("\n")  # 줄바꿈

# =============================================
# 스트리밍 + 최종 메타데이터 함께 가져오기
# =============================================
print("=== 스트리밍 + 메타데이터 ===")
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "파이썬의 장점을 3가지만 알려줘"}
    ]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

    # 스트림이 끝난 후 최종 메시지 객체 가져오기
    final = stream.get_final_message()

print("\n")
print(f"입력 토큰: {final.usage.input_tokens}")
print(f"출력 토큰: {final.usage.output_tokens}")
print(f"종료 이유: {final.stop_reason}")
