from fastapi.testclient import TestClient

from requirement_workflow.interfaces.api import create_app
from requirement_workflow.domain.schemas import (
    BAOutput,
    PlannerOutput,
    POOutput,
    POTask,
    PMOutput,
    Priority,
    RequirementState,
    ServicePlannerOutput,
    TaskArea,
    WorkflowStage,
)
from requirement_workflow.application.workflow import RoleOutput


def fake_runner(
    stage: WorkflowStage,
    _state: RequirementState,
) -> RoleOutput:
    if stage is WorkflowStage.PLANNER:
        return PlannerOutput(feature_goal="회원 프로필 수정")
    if stage is WorkflowStage.SERVICE_PLANNER:
        return ServicePlannerOutput(acceptance_criteria=["저장된다."])
    if stage is WorkflowStage.BA:
        return BAOutput(functional_requirements=["본인만 수정한다."])
    if stage is WorkflowStage.PM:
        return PMOutput(priority=Priority.HIGH)
    if stage is WorkflowStage.PO:
        return POOutput(
            tasks=[
                POTask(
                    title="프로필 수정 API",
                    area=TaskArea.BACKEND,
                    description="프로필 수정 API를 구현한다.",
                    acceptance_criteria=["본인만 수정 가능하다."],
                )
            ]
        )
    raise AssertionError(f"unexpected stage: {stage}")


def test_health_endpoint() -> None:
    client = TestClient(create_app(fake_runner))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_endpoint_returns_requirement_state() -> None:
    client = TestClient(create_app(fake_runner))

    response = client.post(
        "/v1/requirements/run",
        json={
            "raw_requirement": "회원 프로필 수정",
            "prompt_version": "prompt-1",
            "model_version": "fake-model",
            "experiment_variant": "A",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready_for_development"
    assert response.json()["revision"] == 6


def test_run_endpoint_rejects_invalid_request() -> None:
    client = TestClient(create_app(fake_runner))

    response = client.post(
        "/v1/requirements/run",
        json={"raw_requirement": "   "},
    )

    assert response.status_code == 422


def test_run_endpoint_requires_a_runner() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/requirements/run",
        json={"raw_requirement": "회원 프로필 수정"},
    )

    assert response.status_code == 503
