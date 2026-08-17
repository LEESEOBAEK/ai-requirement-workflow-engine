# IT/SW Requirement Agent

IT/SW 요구사항을 Planner부터 PO까지 단계적으로 정제하고, 각 단계의 결과를 검증·기록하는 Python 기반 워크플로 엔진입니다.

## 현재 구현 범위

```text
Planner → Service Planner → BA → PM → PO → 개발 Task
```

- Pydantic 기반 요구사항 스키마
- 역할 순서와 상태 전이를 관리하는 workflow
- 단계별 LLM 요청과 JSON 응답 검증을 위한 router
- CLI·FastAPI·MCP 확장을 위한 application service
- FastAPI HTTP adapter
- 총 23개 테스트

현재 LLM provider API는 아직 연결하지 않았습니다. 먼저 fake runner로 전체 구조를 검증한 뒤 실제 provider client를 연결하는 단계입니다.

## 프로젝트 구조

```text
.
├─ src/it_sw_agent/
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
uv run uvicorn it_sw_agent.interfaces.api:app --reload
```

API 문서:

- Health check: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- 요구사항 실행: `POST /v1/requirements/run`

실제 LLM runner가 연결되기 전까지 요구사항 실행 endpoint는 `503`을 반환합니다.

## 개발 원칙

- `domain`은 데이터 계약과 도메인 규칙만 담당합니다.
- `application`은 업무 흐름과 실행 유스케이스를 담당합니다.
- `infrastructure`는 외부 LLM·DB·파일 시스템 연결을 담당합니다.
- `interfaces`는 FastAPI와 향후 Codex·Claude Code·Antigravity 어댑터를 담당합니다.
- API 키와 비밀값은 `.env`에 저장하고 Git에 커밋하지 않습니다.
- 검증 전 코드는 `experiments`에 두고, 검증된 코드만 `src`로 승격합니다.
