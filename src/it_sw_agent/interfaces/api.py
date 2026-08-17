"""FastAPI adapter for the shared requirement application service."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from it_sw_agent.application.service import RequirementRunCommand, run_requirement
from it_sw_agent.application.workflow import RoleRunner
from it_sw_agent.domain.schemas import RequirementState


def create_app(runner: RoleRunner | None = None) -> FastAPI:
    """Create an API app with an optional injected role runner."""

    fastapi_app = FastAPI(
        title="IT/SW Requirement Engine",
        version="1.0.0",
    )

    @fastapi_app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @fastapi_app.post(
        "/v1/requirements/run",
        response_model=RequirementState,
    )
    def run_requirement_endpoint(
        command: RequirementRunCommand,
    ) -> RequirementState:
        if runner is None:
            raise HTTPException(
                status_code=503,
                detail="LLM role runner is not configured",
            )

        return run_requirement(command, runner)

    return fastapi_app


app = create_app()


__all__ = ["app", "create_app"]
