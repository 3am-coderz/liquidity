from dataclasses import dataclass
from enum import Enum

from ..models import Payable, RiskCategory


class ConstraintType(Enum):
    HARD_EXISTENTIAL = "HARD_EXISTENTIAL"
    HARD_LEGAL = "HARD_LEGAL"
    SOFT_OPTIMIZATION = "SOFT_OPTIMIZATION"


class BillType(Enum):
    PAYROLL = "PAYROLL"
    OPERATING = "OPERATING"


@dataclass
class ScoredBill:
    bill: Payable
    score: float
    is_hard_constraint: bool = False
    survival_impact: float = 0.0
    constraint_type: ConstraintType = ConstraintType.SOFT_OPTIMIZATION


@dataclass
class OptimizationResult:
    strategy: str
    selected_bills: list[ScoredBill]
    delayed_bills: list[ScoredBill]
    total_selected_amount: float
    projected_runway_days: float
    explanation: str


@dataclass
class SolvencyScore:
    priority_value: float
    is_hard_constraint: bool
    survival_impact: float
    constraint_type: ConstraintType


def _normalized(value: float | None, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    return max(value, 0.0)


def _bill_type(bill: Payable) -> BillType:
    if bill.payroll_date or bill.category == "Payroll":
        return BillType.PAYROLL
    return BillType.OPERATING


def _is_critical_path(bill: Payable) -> bool:
    return bill.is_critical or bill.blocks_revenue or bill.category in {"Payroll", "Legal", "Inventory", "Utilities"}


def calculate_solvency_score(bill: Payable, runway_days: float, cash_reserve_ratio: float) -> SolvencyScore:
    if _is_critical_path(bill):
        return SolvencyScore(
            priority_value=10000.0,
            is_hard_constraint=True,
            survival_impact=1.0,
            constraint_type=ConstraintType.HARD_EXISTENTIAL,
        )

    if _bill_type(bill) == BillType.PAYROLL and bill.days_overdue >= 3:
        return SolvencyScore(
            priority_value=9000.0,
            is_hard_constraint=True,
            survival_impact=0.9,
            constraint_type=ConstraintType.HARD_LEGAL,
        )

    if runway_days < 7:
        w_penalty = 0.5
        w_trust = 0.1
        w_revenue = 0.4
    else:
        w_penalty = 0.3
        w_trust = 0.3
        w_revenue = 0.2

    aggression_multiplier = 1.0
    if bill.vendor_aggression == "ADVERSARIAL":
        aggression_multiplier = 1.5
    elif bill.vendor_aggression == "COOPERATIVE":
        aggression_multiplier = 0.8

    penalty_score = _normalized(bill.penalty_risk, 0.35) * aggression_multiplier
    if bill.days_overdue > 7:
        penalty_score *= 1.5

    trust_score = _normalized(bill.trust_score, 0.45) * max(0.0, 1.0 - (bill.days_overdue * 0.05))
    revenue_impact = _normalized(bill.revenue_impact, 0.35) * (1.0 if bill.blocks_revenue else 0.5)
    criticality = _normalized(bill.criticality, 0.3) * 0.1
    reserve_pressure = 1.0 if cash_reserve_ratio < 1 else 0.0

    soft_value = (
        (penalty_score * w_penalty) +
        (trust_score * w_trust) +
        (revenue_impact * w_revenue) +
        criticality +
        reserve_pressure * 0.1
    )
    survival_impact = max(0.0, min(1.0, soft_value))
    return SolvencyScore(
        priority_value=min(soft_value * 100, 5000),
        is_hard_constraint=False,
        survival_impact=survival_impact,
        constraint_type=ConstraintType.SOFT_OPTIMIZATION,
    )


def _to_scored_bill(bill: Payable, solvency_score: SolvencyScore) -> ScoredBill:
    return ScoredBill(
        bill=bill,
        score=round(solvency_score.priority_value, 3),
        is_hard_constraint=solvency_score.is_hard_constraint,
        survival_impact=round(solvency_score.survival_impact, 3),
        constraint_type=solvency_score.constraint_type,
    )


def solve_payment_strategy(
    company_category: RiskCategory,
    bills: list[Payable],
    cash: float,
    monthly_expenses: float,
    cash_floor: float = 2000,
) -> OptimizationResult:
    available_cash = max(cash - cash_floor, 0)
    daily_expense = monthly_expenses / 30 if monthly_expenses else 0
    runway_days = (cash / daily_expense) if daily_expense > 0 else 999.0
    cash_reserve_ratio = (cash / cash_floor) if cash_floor > 0 else 999.0

    scored_pairs = [(bill, calculate_solvency_score(bill, runway_days, cash_reserve_ratio)) for bill in bills]
    hard_pairs = [pair for pair in scored_pairs if pair[1].is_hard_constraint]
    soft_pairs = [pair for pair in scored_pairs if not pair[1].is_hard_constraint]

    hard_pairs = sorted(hard_pairs, key=lambda pair: pair[1].priority_value, reverse=True)
    selected: list[ScoredBill] = []
    delayed: list[ScoredBill] = []
    running_total = 0.0

    for bill, solvency_score in hard_pairs:
        scored_bill = _to_scored_bill(bill, solvency_score)
        if running_total + bill.amount <= available_cash:
            selected.append(scored_bill)
            running_total += bill.amount
        else:
            delayed.append(scored_bill)

    soft_budget = max(available_cash - running_total, 0)
    ranked_soft_pairs = sorted(
        soft_pairs,
        key=lambda pair: (pair[1].priority_value / pair[0].amount) if pair[0].amount else pair[1].priority_value,
        reverse=True,
    )

    soft_running_total = 0.0
    for bill, solvency_score in ranked_soft_pairs:
        scored_bill = _to_scored_bill(bill, solvency_score)
        if soft_running_total + bill.amount <= soft_budget:
            selected.append(scored_bill)
            soft_running_total += bill.amount
        else:
            delayed.append(scored_bill)

    total = round(sum(item.bill.amount for item in selected), 2)
    runway = ((cash - total) / (monthly_expenses / 30)) if monthly_expenses else 999.0
    if company_category == RiskCategory.CRITICAL:
        strategy = "Hard-constraint survival triage"
        explanation = "CRITICAL mode pays existential obligations first, then spends any remaining cash on the highest solvency-preserving soft decisions."
    elif company_category == RiskCategory.RISKY:
        strategy = "Crisis-weighted solvency optimization"
        explanation = "RISKY mode shifts weight toward penalty and revenue continuity while keeping hard constraints ahead of all soft scoring."
    elif company_category == RiskCategory.SAFE:
        strategy = "Full solvency optimization"
        explanation = "SAFE mode still honors hard constraints first, but uses softer relationship and revenue signals because runway pressure is lower."
    else:
        strategy = "Balanced solvency optimization"
        explanation = "STABLE mode separates must-pay obligations from negotiable bills, then ranks the negotiable set by solvency value per rupee."
    return OptimizationResult(
        strategy=strategy,
        selected_bills=selected,
        delayed_bills=delayed,
        total_selected_amount=total,
        projected_runway_days=round(runway, 1),
        explanation=explanation,
    )
