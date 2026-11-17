from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Criterion(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["exact", "contains"]
    reference: str = Field(min_length=1, max_length=10000)
    weight: int = Field(default=1, ge=1, le=100)
    case_sensitive: bool = True


class TaskInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    language: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9+#.-]+$")
    difficulty: Literal["easy", "medium", "hard"]
    expected_outcome: str = Field(min_length=1, max_length=20000)
    criteria: list[Criterion] = Field(min_length=1, max_length=50)

    @field_validator("criteria")
    @classmethod
    def unique_names(cls, criteria):
        if len({c.name for c in criteria}) != len(criteria):
            raise ValueError("Criterion names must be unique")
        return criteria


class TaskRead(TaskInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    revision: int
    created_at: datetime
    updated_at: datetime


class Submission(StrictModel):
    response: str = Field(min_length=1, max_length=50000)


class Feedback(BaseModel):
    criterion: str
    passed: bool
    earned_weight: int
    possible_weight: int
    message: str


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    response: str
    score: float
    feedback: list[Feedback]
    task_snapshot: dict
    engine_version: str
    created_at: datetime


class TaskPage(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int


class EvaluationPage(BaseModel):
    items: list[EvaluationRead]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    location: list[str | int]
    message: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]
    request_id: str | None


class ErrorResponse(BaseModel):
    error: ErrorBody
