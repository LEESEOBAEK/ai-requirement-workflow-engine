"""Application service shared by CLI, FastAPI, and future agent adapters."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from schemas import RequirementState
from workflow import RequirementWorkflow, RoleRunner


class RequirementRunCommand(BaseModel):
    """Validated input needed to execute one requirement case."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    raw_requirement: str = Field(min_length=1)
    prompt_version: str | None = None
    model_version: str | None = None
    experiment_variant: str | None = None


def run_requirement(
    command: RequirementRunCommand,
    runner: RoleRunner,
    *,
    workflow: RequirementWorkflow | None = None,
) -> RequirementState:
    """Run one requirement case using the shared workflow engine."""

    engine = workflow or RequirementWorkflow()
    return engine.run(
        command.raw_requirement,
        runner,
        prompt_version=command.prompt_version,
        model_version=command.model_version,
        experiment_variant=command.experiment_variant,
    )


__all__ = ["RequirementRunCommand", "run_requirement"]
