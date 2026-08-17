"""Defines typed data contracts and validation for the IT/SW requirement workflow.
LLM calls, workflow execution, persistence, and UI/API concerns are handled elsewhere.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class SchemaBase(BaseModel):
    """Common validation behavior for every schema in this module."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    NEEDS_CLARIFICATION = "needs_clarification"
    READY_FOR_DEVELOPMENT = "ready_for_development"
    APPROVED = "approved"
    REJECTED = "rejected"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskArea(str, Enum):
    """Actual delivery area of a development task, not a business role."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    MOBILE = "mobile"
    DATABASE = "database"
    QA = "qa"
    DEVOPS = "devops"
    DESIGN = "design"
    OTHER = "other"


class WorkflowStage(str, Enum):
    PLANNER = "planner"
    SERVICE_PLANNER = "service_planner"
    BA = "ba"
    PM = "pm"
    PO = "po"


class ExecutionStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class Assumption(SchemaBase):
    """An explicit assumption made during requirement refinement."""

    statement: str = Field(min_length=1)
    reason: str | None = None
    owner: str | None = None


class ExecutionRecord(SchemaBase):
    """Auditable record of one workflow-stage execution."""

    run_id: UUID = Field(default_factory=uuid4)
    stage: WorkflowStage
    status: ExecutionStatus
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    workflow_version: str = Field(default="1.0.0", min_length=1)
    prompt_version: str | None = None
    model_version: str | None = None
    experiment_variant: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> "ExecutionRecord":
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at")
        if self.status == ExecutionStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed executions require completed_at")
        return self


class ReviewRecord(SchemaBase):
    """Human review decision kept separately from generated output."""

    reviewer: str = Field(min_length=1)
    decision: ReviewDecision
    comment: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RoleOutputBase(SchemaBase):
    """Common information produced by each role in the B workflow."""

    open_questions: list[str] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    notes: str | None = None


class PlannerOutput(RoleOutputBase):
    """Business/product framing produced by the Planner."""

    feature_goal: str | None = None
    target_users: list[str] = Field(default_factory=list)
    scope_in: list[str] = Field(default_factory=list)
    scope_out: list[str] = Field(default_factory=list)
    business_value: str | None = None


class ServicePlannerOutput(RoleOutputBase):
    """User flow and completion definition produced by the Service Planner."""

    user_scenarios: list[str] = Field(default_factory=list)
    user_flow: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class BAOutput(RoleOutputBase):
    """Business/system analysis produced by the Business Analyst."""

    functional_requirements: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)
    api_requirements: list[str] = Field(default_factory=list)
    permission_requirements: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)


class PMOutput(RoleOutputBase):
    """Scope, priority, risk, and release decision produced by the PM."""

    priority: Priority | None = None
    approved_scope: list[str] = Field(default_factory=list)
    deferred_scope: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    target_release_date: date | None = None


class POTask(SchemaBase):
    """One implementation-ready task produced by the Product Owner."""

    task_id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1)
    area: TaskArea
    description: str = Field(min_length=1)
    priority: Priority = Priority.MEDIUM
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class POOutput(RoleOutputBase):
    """Implementation backlog and readiness information produced by the PO."""

    sprint_goal: str | None = None
    tasks: list[POTask] = Field(default_factory=list)
    definition_of_ready: list[str] = Field(default_factory=list)


class RequirementState(SchemaBase):
    """Complete state of one requirement through the B workflow."""

    case_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    raw_requirement: str = Field(min_length=1)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    workflow_version: str = Field(default="1.0.0", min_length=1)
    prompt_version: str | None = None
    model_version: str | None = None
    experiment_variant: str | None = None
    revision: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    execution_history: list[ExecutionRecord] = Field(default_factory=list)
    review_history: list[ReviewRecord] = Field(default_factory=list)

    planner_output: PlannerOutput | None = None
    service_planner_output: ServicePlannerOutput | None = None
    ba_output: BAOutput | None = None
    pm_output: PMOutput | None = None
    po_output: POOutput | None = None

    @property
    def all_open_questions(self) -> list[str]:
        """Return de-duplicated open questions from every completed stage.

        This is a derived convenience value, not persisted state. The source of
        truth remains each role output's ``open_questions`` list.
        """

        questions: list[str] = []
        outputs = (
            self.planner_output,
            self.service_planner_output,
            self.ba_output,
            self.pm_output,
            self.po_output,
        )
        for output in outputs:
            if output is not None:
                for question in output.open_questions:
                    if question not in questions:
                        questions.append(question)
        return questions

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "RequirementState":
        if self.status == WorkflowStatus.NEEDS_CLARIFICATION and not self.all_open_questions:
            raise ValueError(
                "needs_clarification status requires at least one open question"
            )

        if self.status in {
            WorkflowStatus.READY_FOR_DEVELOPMENT,
            WorkflowStatus.APPROVED,
        }:
            missing: list[str] = []

            if self.planner_output is None or not self.planner_output.feature_goal:
                missing.append("planner_output.feature_goal")
            if self.service_planner_output is None:
                missing.append("service_planner_output")
            elif not self.service_planner_output.acceptance_criteria:
                missing.append("service_planner_output.acceptance_criteria")
            if self.ba_output is None or not self.ba_output.functional_requirements:
                missing.append("ba_output.functional_requirements")
            if self.pm_output is None or self.pm_output.priority is None:
                missing.append("pm_output.priority")
            if self.po_output is None or not self.po_output.tasks:
                missing.append("po_output.tasks")
            else:
                for index, task in enumerate(self.po_output.tasks):
                    if not task.acceptance_criteria:
                        missing.append(f"po_output.tasks[{index}].acceptance_criteria")

            if self.all_open_questions:
                missing.append("all_open_questions must be empty")

            if missing:
                raise ValueError(
                    "requirement is not ready for development: " + ", ".join(missing)
                )

        return self


__all__ = [
    "Assumption",
    "BAOutput",
    "ExecutionRecord",
    "ExecutionStatus",
    "PlannerOutput",
    "POOutput",
    "POTask",
    "PMOutput",
    "Priority",
    "RequirementState",
    "ReviewDecision",
    "ReviewRecord",
    "ServicePlannerOutput",
    "TaskArea",
    "WorkflowStage",
    "WorkflowStatus",
]
