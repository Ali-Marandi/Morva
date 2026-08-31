from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class EmploymentType(StrEnum):
    PERMANENT = "permanent"
    CONTRACTUAL = "contractual"
    TEMPORARY = "temporary"
    PART_TIME = "part_time"


class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    TERMINATED = "terminated"
    DECEASED = "deceased"


class Person(BaseModel):
    national_id: str = Field(min_length=10, max_length=10)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None

    @field_validator("national_id")
    @classmethod
    def validate_national_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("national_id must contain only digits")
        return value


class Employee(Person):
    employee_no: str = Field(min_length=1, max_length=50)
    employment_type: EmploymentType
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    organization_unit_id: str
    position_id: str
    hire_date: date | None = None


class Money(BaseModel):
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="IRR", min_length=3, max_length=3)


class SalaryComponent(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(ge=0)
    kind: str = Field(pattern="^(earning|deduction)$")
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False
    rule_code: str | None = None


class EmploymentSnapshot(BaseModel):
    employee_no: str
    employment_type: EmploymentType
    status: EmployeeStatus
    organization_unit_id: str
    position_id: str
    effective_date: date


class PersonnelOrder(BaseModel):
    number: str
    order_type: str
    issue_date: date
    effective_date: date
    status: str = Field(default="draft", pattern="^(draft|approved|cancelled)$")
    components: list[SalaryComponent] = Field(default_factory=list)
    legal_references: list[str] = Field(default_factory=list)
