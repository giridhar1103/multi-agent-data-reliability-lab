from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Cause(str, Enum):
    DUPLICATE_JOIN = "duplicate_join"
    REFUND_SIGN = "refund_sign"
    STATUS_FILTER = "status_filter"
    HEALTHY = "healthy"
    UPSTREAM_MISSING = "upstream_missing"
    UNKNOWN = "unknown"


class Finding(StrictModel):
    cause: Cause
    explanation: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(max_length=12)


class Plan(StrictModel):
    objective: str = Field(min_length=1, max_length=1000)
    data_question: str = Field(min_length=1, max_length=1000)
    code_question: str = Field(min_length=1, max_length=1000)


class Decision(Finding):
    action: Literal["repair", "no_change", "abstain"]


class Patch(StrictModel):
    sql: str = Field(min_length=1, max_length=12000)
    rationale: str = Field(min_length=1, max_length=2000)


class RunRequest(StrictModel):
    scenario: Literal[
        "duplicate_join", "refund_sign", "status_filter", "healthy", "upstream_missing", "unknown"
    ] = "duplicate_join"
    seed: int = Field(default=11, ge=0, le=1000000)
    mode: Literal["demo", "live"] = "demo"
    topology: Literal["multi", "single"] = "multi"
