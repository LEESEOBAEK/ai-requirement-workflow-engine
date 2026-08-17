# AI Requirement Workflow Engine

[![Tests](https://github.com/LEESEOBAEK/ai-requirement-workflow-engine/actions/workflows/tests.yml/badge.svg?branch=refactor/project-layout)](https://github.com/LEESEOBAEK/ai-requirement-workflow-engine/actions/workflows/tests.yml)

모호한 IT/SW 요구사항을 역할별 검토를 거쳐 개발 가능한 명세와 Task로 정제하는 Python 기반 워크플로 엔진입니다.

> A typed and testable workflow for transforming ambiguous IT/SW requirements into development-ready specifications.

## Workflow

```text
Raw Requirement
    → Planner
    → Service Planner
    → BA
    → PM
    → PO
    → Development-ready Tasks
```

## What this project demonstrates

- Pydantic 기반 데이터 계약과 입력 검증
- 역할 순서·상태 전이·미결 질문 재진입을 관리하는 workflow
- LLM Provider와 분리된 runner/router 구조
- CLI·FastAPI·멀티 에이전트로 확장 가능한 application boundary
- GitHub Actions 기반 자동 테스트
- **23 tests passed**

## Quick Start

Python 3.12 이상과 [uv](https://docs.astral.sh/uv/)가 필요합니다.

```powershell
uv sync
uv run pytest
```

FastAPI 서버 실행:

```powershell
uv run uvicorn requirement_workflow.interfaces.api:app --reload
```

- Health check: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Requirement API: `POST /v1/requirements/run`

## Core Files

| File | Responsibility |
| --- | --- |
| [`workflow.py`](src/requirement_workflow/application/workflow.py) | 역할 실행 순서와 상태 전이 |
| [`schemas.py`](src/requirement_workflow/domain/schemas.py) | 요구사항 데이터 계약과 검증 |
| [`llm_router.py`](src/requirement_workflow/infrastructure/llm_router.py) | 단계별 LLM 요청·응답 경계 |
| [`api.py`](src/requirement_workflow/interfaces/api.py) | FastAPI HTTP adapter |
| [`test_workflow.py`](tests/unit/test_workflow.py) | 핵심 workflow 동작 검증 |

## Architecture

```text
interfaces       → HTTP / external adapters
      ↓
application      → workflow orchestration / use cases
      ↓
domain           → schemas / validation / business rules
      ↑
infrastructure   → LLM and external provider adapters
```

현재 workflow는 실제 LLM Provider에 종속되지 않으며, runner를 주입하는 방식으로 동작합니다. 따라서 테스트용 runner에서 실제 Provider adapter로 단계적으로 교체할 수 있습니다.

## Scope

현재 포함된 역할:

```text
Planner          → 목표와 범위 정의
Service Planner  → 사용자 시나리오와 완료 조건 정의
BA               → 기능·데이터·API·권한·예외 분석
PM               → 우선순위·범위·리스크·출시 목표 정리
PO               → 개발 가능한 Task와 완료 조건 생성
```

현재 제외된 범위:

- 실제 소프트웨어 구현과 배포 자동화
- 운영 DevOps 시스템
- 실제 LLM Provider 인증·호출 adapter
- 전사 업무를 대상으로 하는 AX 자동화

## Next Steps

- 실제 LLM Provider adapter 연결
- 프롬프트·모델 버전 관리
- 사람 검토·승인 이력 저장
- A/B 테스트 결과 수집
- Codex·Claude Code·Antigravity adapter 확장

## Project Layout

```text
src/requirement_workflow/  # package source
tests/                     # unit and integration tests
docs/                      # design and learning notes
prompts/                   # prompt assets
examples/                  # usage examples
experiments/               # unpromoted experiments
pyproject.toml             # dependencies and build settings
uv.lock                    # reproducible dependency versions
```

API 키와 비밀값은 `.env`에 저장하며 Git에 커밋하지 않습니다. 자세한 보안 정책은 [SECURITY.md](SECURITY.md)를 확인하세요.

## License

MIT License. 자세한 내용은 [LICENSE](LICENSE)를 확인하세요.
