from dataclasses import dataclass

from ..models import Payable, RiskCategory


@dataclass
class ScoredBill:
    bill: Payable
    score: float


@dataclass
class OptimizationResult:
    strategy: str
    selected_bills: list[ScoredBill]
    delayed_bills: list[ScoredBill]
    total_selected_amount: float
    projected_runway_days: float
    explanation: str


def _score_bill(bill: Payable, category: RiskCategory) -> float:
    trust = bill.trust_score
    penalty = bill.penalty_risk * (1.5 if category == RiskCategory.RISKY else 1.0)
    if category == RiskCategory.CRITICAL:
        trust = 0
    if bill.days_overdue > 7:
        penalty += 0.25
    return (trust * 0.3) + (penalty * 0.3) + (bill.criticality * 0.2) + (bill.revenue_impact * 0.2)


def solve_payment_strategy(
    company_category: RiskCategory,
    bills: list[Payable],
    cash: float,
    monthly_expenses: float,
    cash_floor: float = 2000,
) -> OptimizationResult:
    available_cash = max(cash - cash_floor, 0)

    if company_category == RiskCategory.SAFE:
        total_due = sum(bill.amount for bill in bills)
        scored_bills = [ScoredBill(bill=bill, score=round(_score_bill(bill, company_category), 3)) for bill in bills]
        if total_due <= available_cash:
            selected = list(scored_bills)
            delayed: list[ScoredBill] = []
        else:
            selected = []
            delayed = list(scored_bills)
        total = round(sum(item.bill.amount for item in selected), 2)
        runway = ((cash - total) / (monthly_expenses / 30)) if monthly_expenses else 999.0
        return OptimizationResult(
            strategy="Pay all bills",
            selected_bills=selected,
            delayed_bills=delayed,
            total_selected_amount=total,
            projected_runway_days=round(runway, 1),
            explanation="SAFE mode unlocked full-pay behavior because the company has healthy coverage and runway.",
        )

    if company_category == RiskCategory.CRITICAL:
        selected_bills = [bill for bill in bills if bill.is_critical or bill.payroll_date or bill.category in {"Legal", "Payroll"}]
        if available_cash > 0:
            selected_bills = sorted(selected_bills, key=lambda bill: _score_bill(bill, company_category), reverse=True)
            filtered: list[Payable] = []
            running_total = 0.0
            for bill in selected_bills:
                if running_total + bill.amount <= available_cash:
                    filtered.append(bill)
                    running_total += bill.amount
            selected_bills = filtered
        selected = [ScoredBill(bill=bill, score=round(_score_bill(bill, company_category), 3)) for bill in selected_bills]
        delayed = [
            ScoredBill(bill=bill, score=round(_score_bill(bill, company_category), 3))
            for bill in bills
            if bill.id not in {item.bill.id for item in selected}
        ]
        total = round(sum(item.bill.amount for item in selected), 2)
        runway = ((cash - total) / (monthly_expenses / 30)) if monthly_expenses else 999.0
        return OptimizationResult(
            strategy="Critical survival triage",
            selected_bills=selected,
            delayed_bills=delayed,
            total_selected_amount=total,
            projected_runway_days=round(runway, 1),
            explanation="CRITICAL mode protected survival obligations first, so only payroll and legal-critical bills were kept.",
        )

    ranked = sorted(
        bills,
        key=lambda bill: (_score_bill(bill, company_category) / bill.amount) if bill.amount else _score_bill(bill, company_category),
        reverse=True,
    )
    selected: list[ScoredBill] = []
    delayed: list[ScoredBill] = []
    running_total = 0.0
    for bill in ranked:
        scored_bill = ScoredBill(bill=bill, score=round(_score_bill(bill, company_category), 3))
        if running_total + bill.amount <= available_cash:
            selected.append(scored_bill)
            running_total += bill.amount
        else:
            delayed.append(scored_bill)

    total = round(sum(item.bill.amount for item in selected), 2)
    runway = ((cash - total) / (monthly_expenses / 30)) if monthly_expenses else 999.0
    strategy = "Penalty-aware optimization" if company_category == RiskCategory.RISKY else "Balanced optimization"
    explanation = (
        "RISKY mode boosted penalty pressure, so the engine paid the bills most likely to hurt runway if delayed."
        if company_category == RiskCategory.RISKY
        else "STABLE mode balanced relationship health, overdue risk, and revenue impact against the cash floor."
    )
    return OptimizationResult(
        strategy=strategy,
        selected_bills=selected,
        delayed_bills=delayed,
        total_selected_amount=total,
        projected_runway_days=round(runway, 1),
        explanation=explanation,
    )
