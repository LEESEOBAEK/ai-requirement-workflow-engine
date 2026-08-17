from schemas import (
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
from workflow import RequirementWorkflow, RoleOutput, WorkflowError


def complete_runner(
    stage: WorkflowStage,
    _state: RequirementState,
) -> RoleOutput:
    if stage is WorkflowStage.PLANNER:
        return PlannerOutput(
            feature_goal="회원 프로필 수정 기능 제공",
            target_users=["일반 회원"],
            scope_in=["이름 수정"],
        )
    if stage is WorkflowStage.SERVICE_PLANNER:
        return ServicePlannerOutput(
            user_scenarios=["회원이 프로필을 수정한다."],
            acceptance_criteria=["저장 후 변경 내용이 조회된다."],
        )
    if stage is WorkflowStage.BA:
        return BAOutput(
            functional_requirements=["회원 본인만 프로필을 수정한다."],
            data_requirements=["이름을 저장한다."],
            api_requirements=["PUT /users/{id}/profile"],
        )
    if stage is WorkflowStage.PM:
        return PMOutput(
            priority=Priority.HIGH,
            approved_scope=["이름 수정"],
        )
    if stage is WorkflowStage.PO:
        return POOutput(
            sprint_goal="프로필 수정 기능 구현",
            tasks=[
                POTask(
                    title="프로필 수정 API 개발",
                    area=TaskArea.BACKEND,
                    description="프로필 수정 API를 구현한다.",
                    acceptance_criteria=["본인 프로필만 수정 가능하다."],
                )
            ],
        )
    raise AssertionError(f"unexpected stage: {stage}")


def test_workflow_runs_all_stages_in_order() -> None:
    workflow = RequirementWorkflow()
    result = workflow.run("회원 프로필 수정 기능", complete_runner)

    assert result.status is WorkflowStatus.READY_FOR_DEVELOPMENT
    assert [record.stage for record in result.execution_history] == [
        WorkflowStage.PLANNER,
        WorkflowStage.SERVICE_PLANNER,
        WorkflowStage.BA,
        WorkflowStage.PM,
        WorkflowStage.PO,
    ]
    assert result.revision == 6


def test_workflow_rejects_out_of_order_stage() -> None:
    workflow = RequirementWorkflow()
    state = workflow.start("회원 프로필 수정 기능")

    try:
        workflow.apply_stage(
            state,
            WorkflowStage.BA,
            BAOutput(functional_requirements=["잘못된 순서"]),
        )
    except WorkflowError as error:
        assert "planner" in str(error)
    else:
        raise AssertionError("out-of-order stage should fail")


def test_workflow_stops_for_clarification() -> None:
    workflow = RequirementWorkflow()
    state = workflow.start("로그인 기능")

    result = workflow.apply_stage(
        state,
        WorkflowStage.PLANNER,
        PlannerOutput(open_questions=["로그인 방식은 무엇인가?"]),
    )

    assert result.status is WorkflowStatus.NEEDS_CLARIFICATION
    assert result.all_open_questions == ["로그인 방식은 무엇인가?"]
    assert workflow.next_stage(result) is WorkflowStage.PLANNER


def test_workflow_can_replace_stage_after_question_is_resolved() -> None:
    workflow = RequirementWorkflow()
    state = workflow.start("로그인 기능")
    state = workflow.apply_stage(
        state,
        WorkflowStage.PLANNER,
        PlannerOutput(open_questions=["로그인 방식은 무엇인가?"]),
    )

    state = workflow.apply_stage(
        state,
        WorkflowStage.PLANNER,
        PlannerOutput(
            feature_goal="이메일 로그인 제공",
            target_users=["회원"],
            scope_in=["이메일 로그인"],
        ),
    )

    assert state.status is WorkflowStatus.REVIEW
    assert workflow.next_stage(state) is WorkflowStage.SERVICE_PLANNER
