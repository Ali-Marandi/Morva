from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class EducationLevel(StrEnum):
    DIPLOMA = "diploma"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"
    OTHER = "other"


class ExperienceType(StrEnum):
    MINISTRY = "ministry"
    GOVERNMENT = "government"
    NON_GOVERNMENT = "non_government"
    TEACHING = "teaching"
    OTHER = "other"


class DependentRelationship(StrEnum):
    CHILD = "child"
    SPOUSE = "spouse"
    PARENT = "parent"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Education:
    employee_no: str
    level: EducationLevel
    field_of_study: str
    institution: str
    completed_on: date | None = None
    certificate_reference: str | None = None


@dataclass(frozen=True, slots=True)
class Experience:
    employee_no: str
    experience_type: ExperienceType
    organization_name: str
    starts_on: date
    ends_on: date | None = None
    reference: str | None = None

    def active_on(self, day: date) -> bool:
        return self.starts_on <= day and (self.ends_on is None or day <= self.ends_on)

    def validate(self) -> None:
        if not self.employee_no.strip():
            raise ValueError("employee_no is required")
        if not self.organization_name.strip():
            raise ValueError("organization_name is required")
        if self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("ends_on cannot precede starts_on")


@dataclass(frozen=True, slots=True)
class Dependent:
    employee_no: str
    relationship: DependentRelationship
    name: str
    birth_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    def active_on(self, day: date) -> bool:
        return (self.valid_from is None or self.valid_from <= day) and (
            self.valid_to is None or day <= self.valid_to
        )

    def validate(self) -> None:
        if not self.employee_no.strip():
            raise ValueError("employee_no is required")
        if not self.name.strip():
            raise ValueError("name is required")
        if self.valid_to is not None and self.valid_from is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot precede valid_from")
