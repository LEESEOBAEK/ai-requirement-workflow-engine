import json

import pytest

from requirement_workflow.infrastructure.llm_router import (
    LLMRequest,
    LLMRoleRouter,
    RouterError,
    build_request,
)
from requirement_workflow.domain.schemas import (
    BAOutput,
    PlannerOutput,
    POOutput,
    Priority,
    RequirementState,
    TaskArea,
    WorkflowStage,
    WorkflowStatus,
)
from requirement_workflow.application.workflow import RequirementWorkflow


def test_build_request_contains_stage_schema_and_current_state() -> None:
    state = RequirementState(raw_requirement="회원 프로필 수정 기능")

    request = build_request(
        WorkflowStage.PLANNER,
        state,
        prompt_version="prompt-1",
        model_version="model-1",
        experiment_variant="A",
    )

    assert request.stage is WorkflowStage.PLANNER
    assert "회원 프로필 수정 기능" in request.user_prompt
    assert "feature_goal" in json.dumps(request.response_schema)
    assert request.prompt_version == "prompt-1"
    assert request.model_version == "model-1"
    assert request.experiment_variant == "A"


def test_router_returns_the_output_model_for_the_selected_stage() -> None:
    received: list[LLMRequest] = []

    def fake_client(request: LLMRequest) -> dict[str, object]:
        received.append(request)
        return {
            "feature_goal": "회원 프로필 수정 기능 제공",
            "target_users": ["일반 회원"],
            "scope_in": ["이름 수정"],
        }

    router = LLMRoleRouter(fake_client)
    output = router(
        WorkflowStage.PLANNER,
        RequirementState(raw_requirement="회원 프로필 수정 기능"),
    )

    assert isinstance(output, PlannerOutput)
    assert received[0].stage is WorkflowStage.PLANNER


def test_router_accepts_fenced_json_response() -> None:
    def fake_client(_request: LLMRequest) -> str:
        return """```json
        {"feature_goal": "프로필 수정"}
        ```"""

    router = LLMRoleRouter(fake_client)
    output = router(
        WorkflowStage.PLANNER,
        RequirementState(raw_requirement="프로필 수정"),
    )

    assert isinstance(output, PlannerOutput)
    assert output.feature_goal == "프로필 수정"


def test_router_rejects_invalid_json() -> None:
    def fake_client(_request: LLMRequest) -> str:
        return "이것은 JSON이 아니다"

    router = LLMRoleRouter(fake_client)

    with pytest.raises(RouterError, match="valid JSON"):
        router(
            WorkflowStage.PLANNER,
            RequirementState(raw_requirement="프로필 수정"),
        )


def test_router_runs_the_full_workflow_with_a_fake_llm() -> None:
    def fake_client(request: LLMRequest) -> dict[str, object]:
        if request.stage is WorkflowStage.PLANNER:
            return {
                "feature_goal": "회원 프로필 수정 기능 제공",
                "target_users": ["일반 회원"],
                "scope_in": ["이름 수정"],
            }
        if request.stage is WorkflowStage.SERVICE_PLANNER:
            return {"acceptance_criteria": ["저장 후 변경 내용이 조회된다."]}
        if request.stage is WorkflowStage.BA:
            return {
                "functional_requirements": ["회원 본인만 수정한다."],
                "data_requirements": ["이름을 저장한다."],
            }
        if request.stage is WorkflowStage.PM:
            return {"priority": Priority.HIGH.value, "approved_scope": ["이름 수정"]}
        if request.stage is WorkflowStage.PO:
            return {
                "sprint_goal": "프로필 수정 기능 구현",
                "tasks": [
                    {
                        "title": "프로필 수정 API 개발",
                        "area": TaskArea.BACKEND.value,
                        "description": "프로필 수정 API를 구현한다.",
                        "acceptance_criteria": ["본인 프로필만 수정 가능하다."],
                    }
                ],
            }
        raise AssertionError(f"unexpected stage: {request.stage}")

    workflow = RequirementWorkflow()
    router = LLMRoleRouter(
        fake_client,
        prompt_version="prompt-1",
        model_version="fake-model",
        experiment_variant="A",
    )

    result = workflow.run("회원 프로필 수정 기능", router)

    assert result.status is WorkflowStatus.READY_FOR_DEVELOPMENT
    assert len(result.execution_history) == 5
    assert isinstance(result.ba_output, BAOutput)
    assert isinstance(result.po_output, POOutput)
    assert result.pm_output is not None
    assert result.pm_output.priority is Priority.HIGH
