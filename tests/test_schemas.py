from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from schemas import (
    BAOutput,
    ExecutionRecord,
    ExecutionStatus,
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


def make_ready_requirement() -> RequirementState:
    return RequirementState(
        raw_requirement="회원이 자신의 프로필 정보를 수정할 수 있어야 한다.",
        status=WorkflowStatus.READY_FOR_DEVELOPMENT,
        planner_output=PlannerOutput(
            feature_goal="회원 프로필 수정 기능 제공",
            target_users=["일반 회원"],
            scope_in=["이름 수정", "프로필 이미지 수정"],
            scope_out=["회원 탈퇴"],
        ),
        service_planner_output=ServicePlannerOutput(
            user_scenarios=["회원이 프로필 화면에서 정보를 수정하고 저장한다."],
            acceptance_criteria=["저장 후 변경된 프로필 정보가 다시 조회된다."],
        ),
        ba_output=BAOutput(
            functional_requirements=["인증된 회원만 본인의 프로필을 수정할 수 있다."],
            data_requirements=["회원 이름과 프로필 이미지 URL을 저장한다."],
            api_requirements=["PUT /users/{user_id}/profile"],
            permission_requirements=["요청 사용자의 ID와 대상 회원 ID가 일치해야 한다."],
        ),
        pm_output=PMOutput(
            priority=Priority.HIGH,
            approved_scope=["이름 수정", "프로필 이미지 수정"],
            target_release_date=date(2026, 9, 1),
        ),
        po_output=POOutput(
            sprint_goal="프로필 수정 기능을 개발 준비 상태로 만든다.",
            tasks=[
                POTask(
                    title="프로필 수정 API 개발",
                    area=TaskArea.BACKEND,
                    description="회원 프로필 수정 API와 권한 검사를 구현한다.",
                    priority=Priority.HIGH,
                    acceptance_criteria=["인증된 회원이 본인의 프로필만 수정할 수 있다."],
                ),
                POTask(
                    title="프로필 수정 화면 개발",
                    area=TaskArea.FRONTEND,
                    description="프로필 수정 화면과 API 연동을 구현한다.",
                    dependencies=["프로필 수정 API 개발"],
                    acceptance_criteria=["수정 성공 후 최신 정보가 화면에 표시된다."],
                ),
            ],
            definition_of_ready=["API 계약이 확정되었다.", "QA가 완료 조건을 확인했다."],
        ),
    )


def test_draft_requirement_can_be_created_incrementally() -> None:
    requirement = RequirementState(raw_requirement="회원 프로필 수정 기능")

    assert requirement.case_id
    assert requirement.status is WorkflowStatus.DRAFT
    assert requirement.planner_output is None
    assert requirement.all_open_questions == []


def test_ready_requirement_requires_all_workflow_outputs() -> None:
    requirement = make_ready_requirement()

    assert requirement.status is WorkflowStatus.READY_FOR_DEVELOPMENT
    assert len(requirement.po_output.tasks) == 2
    assert requirement.po_output.tasks[0].area is TaskArea.BACKEND
    assert requirement.all_open_questions == []


def test_ready_requirement_rejects_missing_acceptance_criteria() -> None:
    requirement = make_ready_requirement()
    requirement.po_output.tasks[0].acceptance_criteria = []

    with pytest.raises(ValidationError, match="acceptance_criteria"):
        RequirementState.model_validate(requirement.model_dump())


def test_needs_clarification_requires_a_question() -> None:
    with pytest.raises(ValidationError, match="open question"):
        RequirementState(
            raw_requirement="기능 요구사항",
            status=WorkflowStatus.NEEDS_CLARIFICATION,
        )


def test_open_questions_are_collected_from_all_roles() -> None:
    requirement = RequirementState(
        raw_requirement="로그인 기능",
        planner_output=PlannerOutput(open_questions=["지원할 로그인 방식은?"]),
        ba_output=BAOutput(open_questions=["지원할 로그인 방식은?", "세션 만료시간은?"]),
    )

    assert requirement.all_open_questions == ["지원할 로그인 방식은?", "세션 만료시간은?"]


def test_execution_record_requires_completion_time_when_completed() -> None:
    started_at = datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="completed_at"):
        ExecutionRecord(
            stage=WorkflowStage.BA,
            status=ExecutionStatus.COMPLETED,
            started_at=started_at,
        )


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="extra_field"):
        PlannerOutput(feature_goal="기능 목표", extra_field="잘못된 필드")


def test_json_serialization_is_available() -> None:
    requirement = make_ready_requirement()

    data = requirement.model_dump(mode="json")

    assert data["case_id"]
    assert data["status"] == "ready_for_development"
    assert data["po_output"]["tasks"][0]["area"] == "backend"
