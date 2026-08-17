import pytest
from pydantic import ValidationError

from it_sw_agent.application.service import RequirementRunCommand, run_requirement
from it_sw_agent.domain.schemas import (
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
    WorkflowStatus,
)
from it_sw_agent.application.workflow import RoleOutput


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


def test_application_runs_requirement_through_workflow() -> None:
    result = run_requirement(
        RequirementRunCommand(
            raw_requirement="회원 프로필 수정",
            prompt_version="prompt-1",
            model_version="fake-model",
            experiment_variant="A",
        ),
        fake_runner,
    )

    assert result.status is WorkflowStatus.READY_FOR_DEVELOPMENT
    assert result.revision == 6
    assert result.prompt_version == "prompt-1"
    assert result.model_version == "fake-model"
    assert result.experiment_variant == "A"


def test_application_rejects_blank_requirement() -> None:
    with pytest.raises(ValidationError):
        RequirementRunCommand(raw_requirement="   ")
