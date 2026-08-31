from datetime import date
from decimal import Decimal
from morva.domain.models import Money

class PayrollService:
    def gross(self, base: Money, earnings: list[Money]) -> Money:
        return Money(amount=base.amount + sum((x.amount for x in earnings), Decimal(0)))

    def period_key(self, period: date) -> str:
        return f"{period.year:04d}-{period.month:02d}"
