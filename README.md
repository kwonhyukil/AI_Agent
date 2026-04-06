# AI Agent Study

이 저장소는 `ai_agent` 폴더를 중심으로 `AI Agent`를 단계별로 직접 만들어 보며 공부한 내용을 정리한 학습용 프로젝트입니다.

## 핵심 요약

`AI Agent = LLM + Prompt + Tool + Loop + Memory + Planning + Execution + Verification + Workflow + Reliability`

즉, AI Agent는 단순히 답변만 하는 모델이 아니라, 목표를 이해하고, 필요한 도구를 고르고, 상태를 기억하고, 계획하고, 실행하고, 검증하는 작업 시스템입니다.

## 문서 안내

- `ai_agent/00_START_HERE.md`
  처음 시작할 때 보는 입문 설명
- `ai_agent/STUDY_GUIDE.md`
  단계별 학습 순서와 관찰 포인트
- `THEORY_NOTES.md`
  지금까지 공부한 핵심 이론 정리

## 단계별 학습 흐름

| 단계 | 파일 | 핵심 주제 | 한 줄 요약 |
|---|---|---|---|
| 01 | `ai_agent/01_hello.py` | LLM 호출 | AI에게 처음 말 걸기 |
| 02 | `ai_agent/02_tool_use.py` | Tool Use | 판단은 모델, 실행은 코드 |
| 03 | `ai_agent/03_agentic_loop.py` | Agentic Loop | 끝날 때까지 반복하는 Agent |
| 04 | `ai_agent/04_practical_tools.py` | Practical Tools | 검색, 파일, 실행 도구 붙이기 |
| 05 | `ai_agent/05_memory_state.py` | Memory / State | 기억하는 Agent 만들기 |
| 06 | `ai_agent/06_study_assistant.py` | Mini Project | 공부 도우미 Agent 만들기 |
| 07 | `ai_agent/07_web_study_assistant.py` | Search + Quiz | 검색하고 퀴즈 내는 Agent |
| 08 | `ai_agent/08_adaptive_study_agent.py` | Adaptive | 상태에 맞게 반응하는 Agent |
| 09 | `ai_agent/09_planning_agent.py` | Planning | 목표를 단계로 나누는 Agent |
| 10 | `ai_agent/10_execution_agent.py` | Execution | 현재 단계를 실제로 실행하는 Agent |
| 11 | `ai_agent/11_reflection_agent.py` | Verification / Reflection | 실행 결과를 검증하고 회고하는 Agent |
| 12 | `ai_agent/12_workflow_agent.py` | Workflow / Orchestration | 실행, 검증, 보완, 완료를 흐름으로 묶는 Agent |
| 13 | `ai_agent/13_my_project_agent.py` | Custom Project | 내 주제로 Agent를 직접 설계하는 단계 |

## 추천 학습 순서

1. `ai_agent/00_START_HERE.md` 읽기
2. `ai_agent/STUDY_GUIDE.md` 기준으로 01부터 차례대로 보기
3. 각 파일을 직접 실행해 출력 흐름 관찰하기
4. 왜 그 단계가 필요한지 한 문장으로 설명해보기
5. 이론이 헷갈릴 때는 `THEORY_NOTES.md` 같이 보기

## 이론 로드맵

아래 순서로 이론을 잡으면 코드 흐름이 더 잘 이해됩니다.

1. LLM 기초
2. Prompt Engineering
3. Tool Calling / Function Calling
4. Memory / State
5. Planning
6. Execution
7. Verification / Reflection
8. Workflow / Orchestration
9. Reliability / Safety

자세한 내용은 `THEORY_NOTES.md`에 정리했습니다.

## 실행 예시

```powershell
cd C:\Users\YJU\KWONHYUKIL\study_1\ai_agent
.\venv\Scripts\python.exe .\01_hello.py
```

## 최종 정리

이 프로젝트의 학습 흐름은 아래처럼 이어집니다.

1. LLM과 대화하기
2. 도구 연결하기
3. 반복 구조 만들기
4. 기억 붙이기
5. 상태 기반 반응 만들기
6. 계획 세우기
7. 실행하기
8. 검증하기
9. 전체 workflow로 묶기
10. 내 주제로 확장하기

결론적으로, AI Agent를 이해한다는 것은 `모델의 한계를 이해하고, 그 한계를 도구와 상태와 workflow로 보완하는 구조를 이해하는 것`입니다.
