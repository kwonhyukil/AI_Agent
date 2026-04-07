"""
01_basic.py - Claude API 기초: 메시지 전송

배울 것:
- Anthropic 클라이언트 초기화
- messages.create() 로 메시지 보내기
- 응답 구조 이해하기
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

# 1. 클라이언트 초기화
client = anthropic.Anthropic()
# ANTHROPIC_API_KEY 환경변수를 자동으로 읽음

# 2. 기본 메시지 전송
print("=== 기본 메시지 전송 ===")
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "안녕하세요! 간단하게 자기소개 해주세요."}
    ]
)

# 3. 응답 구조 출력
print("\n[응답 텍스트]")
print(message.content[0].text)

print("\n[응답 메타데이터]")
print(f"모델: {message.model}")
print(f"입력 토큰: {message.usage.input_tokens}")
print(f"출력 토큰: {message.usage.output_tokens}")
print(f"종료 이유: {message.stop_reason}")

# 4. 실습: 직접 질문을 바꿔보세요
print("\n=== 실습: 나만의 질문 ===")
my_question = "파이썬과 자바스크립트의 차이점을 3줄로 설명해줘"

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[
        {"role": "user", "content": my_question}
    ]
)

print(f"질문: {my_question}")
print(f"답변: {response.content[0].text}")
