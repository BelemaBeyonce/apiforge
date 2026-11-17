from datetime import datetime
from typing import Literal

import regex
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Criterion(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["exact", "contains", "regex"]
    reference: str = Field(min_length=1, max_length=10000)
    weight: int = Field(default=1, ge=1, le=100)
    case_sensitive: bool = True
    category: str = Field(default="general", min_length=1, max_length=80)

    @model_validator(mode="after")
    def bounded_regex(self):
        if self.kind == "regex":
            if len(self.reference) > 512 or self.reference.count("(") > 20:
                raise ValueError("Regex limited to 512 characters and 20 groups")
            if any(int(n) > 1000 for n in regex.findall(r"\d+", self.reference)):
                raise ValueError("Regex numeric bounds are limited to 1000")
            try:
                regex.compile(self.reference)
            except regex.error:
                raise ValueError("Invalid regex") from None
        return self


class RubricCategory(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    weight: int = Field(default=1, ge=1, le=100)


class TaskInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    language: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9+#.-]+$")
    difficulty: Literal["easy", "medium", "hard"]
    expected_outcome: str = Field(min_length=1, max_length=20000)
    criteria: list[Criterion] = Field(min_length=1, max_length=50)
    categories: list[RubricCategory] = Field(
        default_factory=lambda: [RubricCategory(name="general")], min_length=1, max_length=10
    )

    @model_validator(mode="after")
    def valid_categories(self):
        names = {category.name for category in self.categories}
        if len(names) != len(self.categories):
            raise ValueError("Category names must be unique")
        if names != {criterion.category for criterion in self.criteria}:
            raise ValueError(
                "Each category must be used; every criterion must reference a category"
            )
        return self

    @field_validator("criteria")
    @classmethod
    def unique_names(cls, criteria):
        if len({c.name for c in criteria}) != len(criteria):
            raise ValueError("Criterion names must be unique")
        return criteria


class TaskUpdate(TaskInput):
    expected_revision: int = Field(ge=1)


class TaskRead(TaskInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    revision: int
    owner_id: int | None
    archived_at: datetime | None
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
    category: str = "general"
    contribution: float | None = None
    reason: str | None = None


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    response: str
    author_id: int | None
    status: str
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
