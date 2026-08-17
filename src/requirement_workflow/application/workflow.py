"""Orchestrates the B-style workflow through an injected role runner.
LLM integration remains external for testability and future agent expansion.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

from requirement_workflow.domain.schemas import (
    BAOutput,
    ExecutionRecord,
    ExecutionStatus,
    PlannerOutput,
    POOutput,
    PMOutput,
    RequirementState,
    ServicePlannerOutput,
    WorkflowStage,
    WorkflowStatus,
)


class WorkflowError(ValueError):
    """Raised when a workflow transition is invalid."""


RoleOutput: TypeAlias = (
    PlannerOutput | ServicePlannerOutput | BAOutput | PMOutput | POOutput
)


RoleRunner: TypeAlias = Callable[
    [WorkflowStage, RequirementState],
    RoleOutput,
]


STAGE_ORDER: tuple[WorkflowStage, ...] = (
    WorkflowStage.PLANNER,
    WorkflowStage.SERVICE_PLANNER,
    WorkflowStage.BA,
    WorkflowStage.PM,
    WorkflowStage.PO,
)

_OUTPUT_FIELD_BY_STAGE = {
    WorkflowStage.PLANNER: "planner_output",
    WorkflowStage.SERVICE_PLANNER: "service_planner_output",
    WorkflowStage.BA: "ba_output",
    WorkflowStage.PM: "pm_output",
    WorkflowStage.PO: "po_output",
}

_OUTPUT_TYPE_BY_STAGE = {
    WorkflowStage.PLANNER: PlannerOutput,
    WorkflowStage.SERVICE_PLANNER: ServicePlannerOutput,
    WorkflowStage.BA: BAOutput,
    WorkflowStage.PM: PMOutput,
    WorkflowStage.PO: POOutput,
}


class RequirementWorkflow:
    """Run and validate the Planner → Service Planner → BA → PM → PO flow."""

    def __init__(self, workflow_version: str = "1.0.0") -> None:
        self.workflow_version = workflow_version

    def start(
        self,
        raw_requirement: str,
        *,
        prompt_version: str | None = None,
        model_version: str | None = None,
        experiment_variant: str | None = None,
    ) -> RequirementState:
        """Create a new draft requirement case."""

        return RequirementState(
            raw_requirement=raw_requirement,
            workflow_version=self.workflow_version,
            prompt_version=prompt_version,
            model_version=model_version,
            experiment_variant=experiment_variant,
        )

    @staticmethod
    def next_stage(state: RequirementState) -> WorkflowStage | None:
        """Return the first incomplete or unresolved stage."""

        for stage in STAGE_ORDER:
            output = getattr(state, _OUTPUT_FIELD_BY_STAGE[stage])
            if output is None or output.open_questions:
                return stage
        return None

    def apply_stage(
        self,
        state: RequirementState,
        stage: WorkflowStage,
        output: RoleOutput,
        *,
        prompt_version: str | None = None,
        model_version: str | None = None,
        experiment_variant: str | None = None,
        notes: str | None = None,
    ) -> RequirementState:
        """Apply one correctly ordered role output to a requirement case.

        If the output contains open questions, the state becomes
        ``needs_clarification`` and the same stage must be resubmitted after
        those questions are resolved.
        """

        expected_stage = self.next_stage(state)
        if expected_stage is None:
            raise WorkflowError("the workflow is already complete")
        if stage is not expected_stage:
            raise WorkflowError(
                f"expected stage '{expected_stage.value}', received '{stage.value}'"
            )

        expected_type = _OUTPUT_TYPE_BY_STAGE[stage]
        if not isinstance(output, expected_type):
            raise TypeError(
                f"stage '{stage.value}' requires {expected_type.__name__}, "
                f"received {type(output).__name__}"
            )

        record = ExecutionRecord(
            stage=stage,
            # Create the record as started first because the schema requires
            # a completion timestamp whenever status is ``completed``.
            status=ExecutionStatus.STARTED,
            workflow_version=self.workflow_version,
            prompt_version=(
                prompt_version
                if prompt_version is not None
                else state.prompt_version
            ),
            model_version=(
                model_version
                if model_version is not None
                else state.model_version
            ),
            experiment_variant=(
                experiment_variant
                if experiment_variant is not None
                else state.experiment_variant
            ),
            notes=notes,
        )
        record = ExecutionRecord.model_validate(
            record.model_dump()
            | {
                "status": ExecutionStatus.COMPLETED,
                "completed_at": record.started_at,
            }
        )

        updates = state.model_dump()
        field_name = _OUTPUT_FIELD_BY_STAGE[stage]
        updates[field_name] = output.model_dump()
        updates["revision"] = state.revision + 1
        updates["execution_history"] = [
            *updates["execution_history"],
            record.model_dump(),
        ]

        if output.open_questions:
            updates["status"] = WorkflowStatus.NEEDS_CLARIFICATION
        elif (
            stage is WorkflowStage.PO
            and isinstance(output, POOutput)
            and output.tasks
        ):
            updates["status"] = WorkflowStatus.READY_FOR_DEVELOPMENT
        else:
            updates["status"] = WorkflowStatus.REVIEW

        return RequirementState.model_validate(updates)

    def run(
        self,
        raw_requirement: str,
        runner: RoleRunner,
        *,
        prompt_version: str | None = None,
        model_version: str | None = None,
        experiment_variant: str | None = None,
    ) -> RequirementState:
        """Run stages until completion or until clarification is required."""

        state = self.start(
            raw_requirement,
            prompt_version=prompt_version,
            model_version=model_version,
            experiment_variant=experiment_variant,
        )

        while True:
            stage = self.next_stage(state)
            if stage is None:
                return state

            output = runner(stage, state)
            state = self.apply_stage(
                state,
                stage,
                output,
                prompt_version=prompt_version,
                model_version=model_version,
                experiment_variant=experiment_variant,
            )

            if state.status is WorkflowStatus.NEEDS_CLARIFICATION:
                return state


__all__ = [
    "RequirementWorkflow",
    "RoleOutput",
    "RoleRunner",
    "STAGE_ORDER",
    "WorkflowError",
]
