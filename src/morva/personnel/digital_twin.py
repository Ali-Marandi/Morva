from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from morva.personnel.orders import PersonnelOrder


@dataclass(frozen=True, slots=True)
class DigitalTwinSnapshot:
    employee_no: str
    effective_date: date
    position_id: str
    employment_type: str
    organization_unit_id: str
    order_numbers: tuple[str, ...]
    components: tuple[tuple[str, Decimal], ...]


def build_snapshot(
    *,
    employee_no: str,
    effective_date: date,
    position_id: str,
    employment_type: str,
    organization_unit_id: str,
    orders: tuple[PersonnelOrder, ...],
) -> DigitalTwinSnapshot:
    effective = tuple(order for order in orders if order.is_effective_on(effective_date))
    effective = tuple(sorted(effective, key=lambda item: (item.effective_from, item.number)))
    components: dict[str, Decimal] = {}
    for order in effective:
        for line in order.lines:
            components[line.code] = line.amount
    return DigitalTwinSnapshot(
        employee_no=employee_no,
        effective_date=effective_date,
        position_id=position_id,
        employment_type=employment_type,
        organization_unit_id=organization_unit_id,
        order_numbers=tuple(item.number for item in effective),
        components=tuple(sorted(components.items())),
    )
