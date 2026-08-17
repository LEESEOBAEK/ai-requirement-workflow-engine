# AI Requirement Workflow Engine

AI로 IT/SW 요구사항을 Planner부터 PO까지 단계적으로 정제하고, 개발 가능한 명세와 Task로 연결하는 Python 기반 워크플로 엔진입니다.

> An AI-powered workflow engine for refining IT/SW requirements into development-ready specifications.

## 프로젝트 상태

현재는 초기 개발 단계입니다. 실제 LLM provider를 연결하기 전, 역할별 데이터 계약·워크플로·응답 검증 구조를 fake runner로 검증하고 있습니다.

## 현재 구현 범위

```text
Planner → Service Planner → BA → PM → PO → 개발 Task
```

- Pydantic 기반 요구사항 스키마
- 역할 순서와 상태 전이를 관리하는 workflow
- 단계별 LLM 요청과 JSON 응답 검증을 위한 router
- CLI·FastAPI·에이전트 확장을 위한 application service
- FastAPI HTTP adapter
- 총 23개 테스트

## 범위

포함 범위:

- Planner: 기능 목표와 범위 정의
- Service Planner: 사용자 시나리오와 완료 조건 정의
- BA: 기능·데이터·API·권한·예외 분석
- PM: 우선순위·범위·리스크·출시 목표 정리
- PO: 개발 가능한 Task와 완료 조건 생성

제외 범위:

- 실제 소프트웨어 개발 구현
- QA 실행과 배포 자동화
- DevOps·운영 시스템
- 전사 업무를 대상으로 하는 AX 자동화

## 프로젝트 구조

```text
.
├─ src/requirement_workflow/
│  ├─ domain/schemas.py
│  ├─ application/workflow.py
│  ├─ application/service.py
│  ├─ infrastructure/llm_router.py
│  ├─ interfaces/api.py
│  └─ main.py
├─ tests/unit/
├─ tests/integration/
├─ docs/
├─ prompts/
├─ experiments/
├─ examples/
├─ data/
├─ pyproject.toml
└─ uv.lock
```

## 실행

Python 3.12 이상과 uv가 필요합니다.

```powershell
uv sync
uv run pytest
```

예상 결과:

```text
23 passed
```

## FastAPI 서버

```powershell
uv run uvicorn requirement_workflow.interfaces.api:app --reload
```

API 문서:

- Health check: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- 요구사항 실행: `POST /v1/requirements/run`

실제 LLM runner가 연결되기 전까지 요구사항 실행 endpoint는 `503`을 반환합니다.

## 다음 단계

- 실제 LLM provider adapter 연결
- 역할별 프롬프트 버전 관리
- 사람 검토와 승인 이력 연결
- A/B 테스트 결과 저장
- Codex·Claude Code·Antigravity용 adapter 확장

## 개발 원칙

- `domain`은 데이터 계약과 도메인 규칙만 담당합니다.
- `application`은 업무 흐름과 실행 유스케이스를 담당합니다.
- `infrastructure`는 외부 LLM·DB·파일 시스템 연결을 담당합니다.
- `interfaces`는 FastAPI와 향후 Codex·Claude Code·Antigravity 어댑터를 담당합니다.
- API 키와 비밀값은 `.env`에 저장하고 Git에 커밋하지 않습니다.
- 검증 전 코드는 `experiments`에 두고, 검증된 코드만 `src`로 승격합니다.

## License

MIT License. 자세한 내용은 [LICENSE](LICENSE)를 확인하세요.
