# Claude API 공부 시작

## 목표
Anthropic Python SDK를 사용해서 Claude API를 직접 다루는 방법을 익힌다.

## 학습 순서

| 파일 | 주제 |
|------|------|
| `01_basic.py` | 기본 메시지 전송 (Messages API) |
| `02_streaming.py` | 스트리밍 응답 처리 |
| `03_conversation.py` | 멀티턴 대화 (대화 히스토리 관리) |
| `04_system_prompt.py` | 시스템 프롬프트 활용 |
| `05_tool_use.py` | Tool Use (함수 호출) |
| `06_vision.py` | 이미지 입력 처리 |

## 환경 설정

```bash
# ai_agent의 venv 활용
source ../ai_agent/venv/Scripts/activate

# anthropic 패키지 확인
pip show anthropic
```

## 핵심 개념

- **Messages API**: Claude와 대화하는 기본 인터페이스
- **Role**: `user` / `assistant` 번갈아 가며 대화
- **System Prompt**: Claude의 역할/성격 지정
- **Tool Use**: Claude가 외부 함수를 호출하게 하는 기능
- **Streaming**: 응답을 토큰 단위로 실시간 수신
