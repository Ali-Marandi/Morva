from datetime import date
from decimal import Decimal
from enum import StrEnum
from pydantic import BaseModel, Field

class EmploymentType(StrEnum):
    PERMANENT = "permanent"
    CONTRACTUAL = "contractual"
    TEMPORARY = "temporary"

class Person(BaseModel):
    national_id: str = Field(min_length=10, max_length=10)
    first_name: str
    last_name: str
    birth_date: date | None = None

class Employee(Person):
    employee_no: str
    employment_type: EmploymentType
    organization_unit_id: str
    position_id: str

class Money(BaseModel):
    amount: Decimal = Field(ge=0)
    currency: str = "IRR"
