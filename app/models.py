from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CaseStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class LossType(StrEnum):
    MONEY = "money"
    TIME = "time"
    DIGNITY = "dignity"
    OPPORTUNITY = "opportunity"
    ENERGY = "energy"
    OTHER = "other"


class Loss(BaseModel):
    amount: float | None = None
    currency: str | None = None
    types: list[LossType] = Field(default_factory=list)
    description: str | None = None

    @field_validator("currency", "description", mode="before")
    @classmethod
    def trim_optional_string(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class GapAnalysis(BaseModel):
    dimension: str
    assumed: str
    actual: str

    @field_validator("dimension", "assumed", "actual", mode="before")
    @classmethod
    def trim_required_string(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    date: Date
    status: CaseStatus = CaseStatus.PUBLISHED
    loss: Loss | None = None
    summary: str
    genius_logic: str | None = None
    reality: str
    gap_analysis: list[GapAnalysis] = Field(default_factory=list)
    avoidance: list[str]
    checklist: list[str]
    mood: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("title", "summary", "reality", mode="before")
    @classmethod
    def trim_required_string(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("genius_logic", "mood", mode="before")
    @classmethod
    def trim_optional_string(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("avoidance", "checklist", "tags", mode="before")
    @classmethod
    def trim_string_list(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() for item in value if isinstance(item, str) and item.strip()]
        return value

    @model_validator(mode="after")
    def reject_empty_required_values(self) -> "CaseCreate":
        required = {
            "title": self.title,
            "summary": self.summary,
            "reality": self.reality,
        }
        for name, value in required.items():
            if not value:
                raise ValueError(f"{name} is required")
        if not self.avoidance:
            raise ValueError("avoidance is required")
        if not self.checklist:
            raise ValueError("checklist is required")
        return self


class CaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    date: Date | None = None
    status: CaseStatus | None = None
    loss: Loss | None = None
    summary: str | None = None
    genius_logic: str | None = None
    reality: str | None = None
    gap_analysis: list[GapAnalysis] | None = None
    avoidance: list[str] | None = None
    checklist: list[str] | None = None
    mood: str | None = None
    tags: list[str] | None = None

    @field_validator("title", "summary", "reality", mode="before")
    @classmethod
    def trim_required_string(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("genius_logic", "mood", mode="before")
    @classmethod
    def trim_optional_string(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("avoidance", "checklist", "tags", mode="before")
    @classmethod
    def trim_string_list(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() for item in value if isinstance(item, str) and item.strip()]
        return value


class CaseRecord(CaseCreate):
    id: str
    slug: str
    created_at: datetime
    updated_at: datetime
