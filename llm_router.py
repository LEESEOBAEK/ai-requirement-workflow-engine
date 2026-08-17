"""Provider-agnostic LLM routing for the requirement workflow.

The workflow controls order and state transitions. This module only builds a
stage-specific request, calls an injected LLM client, and validates the result
with the matching Pydantic output model.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeAlias, cast

from pydantic import BaseModel, ValidationError

from schemas import (
    BAOutput,
    PlannerOutput,
    POOutput,
    PMOutput,
    RequirementState,
    ServicePlannerOutput,
    WorkflowStage,
)


class RouterError(RuntimeError):
    """Raised when an LLM response cannot become a valid role output."""


RoleOutput: TypeAlias = (
    PlannerOutput | ServicePlannerOutput | BAOutput | PMOutput | POOutput
)

LLMResponse: TypeAlias = str | Mapping[str, object]


@dataclass(frozen=True)
class LLMRequest:
    """All information an LLM provider adapter needs for one LLM request."""

    stage: WorkflowStage
    system_prompt: str
    user_prompt: str
    response_schema: dict[str, object]
    prompt_version: str | None = None
    model_version: str | None = None
    experiment_variant: str | None = None


LLMClient: TypeAlias = Callable[[LLMRequest], LLMResponse]


_OUTPUT_MODEL_BY_STAGE: dict[WorkflowStage, type[BaseModel]] = {
    WorkflowStage.PLANNER: PlannerOutput,
    WorkflowStage.SERVICE_PLANNER: ServicePlannerOutput,
    WorkflowStage.BA: BAOutput,
    WorkflowStage.PM: PMOutput,
    WorkflowStage.PO: POOutput,
}

_ROLE_INSTRUCTIONS: dict[WorkflowStage, str] = {
    WorkflowStage.PLANNER: (
        "기능의 목적, 대상 사용자, 포함 범위와 제외 범위를 정의한다."
    ),
    WorkflowStage.SERVICE_PLANNER: (
        "사용자 시나리오와 사용자 흐름을 정리하고 완료 조건을 정의한다."
    ),
    WorkflowStage.BA: (
        "기능·데이터·API·권한·예외 케이스를 시스템 관점에서 분석한다."
    ),
    WorkflowStage.PM: (
        "우선순위, 승인·보류 범위, 리스크와 출시 목표를 결정한다."
    ),
    WorkflowStage.PO: (
        "개발 가능한 Task와 Task별 완료 조건을 작성한다."
    ),
}


def _state_context(state: RequirementState) -> str:
    """Serialize the current case without execution/review audit noise."""

    context = state.model_dump(
        mode="json",
        exclude={"execution_history", "review_history"},
    )
    return json.dumps(context, ensure_ascii=False, indent=2)


def build_request(
    stage: WorkflowStage,
    state: RequirementState,
    *,
    prompt_version: str | None = None,
    model_version: str | None = None,
    experiment_variant: str | None = None,
) -> LLMRequest:
    """Build a role-specific request without calling an LLM."""

    output_model = _OUTPUT_MODEL_BY_STAGE[stage]
    schema_json = cast(dict[str, object], output_model.model_json_schema())
    system_prompt = (
        f"당신은 IT/SW 요구사항 워크플로의 {stage.value} 역할이다. "
        f"{_ROLE_INSTRUCTIONS[stage]}\n"
        "현재 단계의 결과만 작성하고, 결정할 수 없는 내용은 "
        "open_questions에 기록한다. 응답은 JSON 객체 하나만 반환한다. "
        "JSON 이외의 설명이나 Markdown 코드 블록은 반환하지 않는다."
    )
    user_prompt = (
        "다음은 원본 요구사항과 현재까지의 정제 상태다.\n\n"
        "--- CURRENT REQUIREMENT STATE ---\n"
        f"{_state_context(state)}\n"
        "--- END CURRENT REQUIREMENT STATE ---\n\n"
        "위 상태를 바탕으로 현재 역할의 결과를 작성하라."
    )
    return LLMRequest(
        stage=stage,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=schema_json,
        prompt_version=prompt_version,
        model_version=model_version,
        experiment_variant=experiment_variant,
    )


def _parse_response(response: LLMResponse) -> dict[str, object]:
    """Accept a mapping or a JSON string, including a fenced JSON response."""

    if isinstance(response, Mapping):
        return dict(response)

    text = response.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
        if text.lower().startswith("json\n"):
            text = text[5:].lstrip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise RouterError("LLM response is not valid JSON") from error

    if not isinstance(payload, dict):
        raise RouterError("LLM response must be a JSON object")
    return payload


class LLMRoleRouter:
    """Callable adapter that turns one LLM client into a workflow runner."""

    def __init__(
        self,
        client: LLMClient,
        *,
        prompt_version: str | None = None,
        model_version: str | None = None,
        experiment_variant: str | None = None,
    ) -> None:
        self.client = client
        self.prompt_version = prompt_version
        self.model_version = model_version
        self.experiment_variant = experiment_variant

    def __call__(self, stage: WorkflowStage, state: RequirementState) -> RoleOutput:
        request = build_request(
            stage,
            state,
            prompt_version=self.prompt_version,
            model_version=self.model_version,
            experiment_variant=self.experiment_variant,
        )
        response = self.client(request)
        payload = _parse_response(response)
        output_model = _OUTPUT_MODEL_BY_STAGE[stage]

        try:
            output = output_model.model_validate(payload)
        except ValidationError as error:
            raise RouterError(
                f"LLM response does not match the {stage.value} output schema"
            ) from error

        return cast(RoleOutput, output)


__all__ = [
    "LLMClient",
    "LLMRequest",
    "LLMResponse",
    "LLMRoleRouter",
    "RoleOutput",
    "RouterError",
    "build_request",
]
