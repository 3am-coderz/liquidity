from dataclasses import dataclass

from ..models import RiskCategory


@dataclass
class CompanyMetrics:
    runway_days: float
    coverage_ratio: float
    cash_flow: float
    risk_category: RiskCategory


def classify_company(cash: float, monthly_income: float, monthly_expenses: float, upcoming_bills: float) -> CompanyMetrics:
    daily_expense = monthly_expenses / 30 if monthly_expenses else 0
    runway = cash / daily_expense if daily_expense > 0 else 999.0
    coverage = cash / upcoming_bills if upcoming_bills > 0 else 999.0
    cashflow = monthly_income - monthly_expenses

    if coverage > 1.5 and runway > 90 and cashflow > 0:
        category = RiskCategory.SAFE
    elif coverage > 1 and runway > 60:
        category = RiskCategory.STABLE
    elif coverage > 0.5 and runway > 30:
        category = RiskCategory.RISKY
    else:
        category = RiskCategory.CRITICAL

    return CompanyMetrics(
        runway_days=round(runway, 1),
        coverage_ratio=round(coverage, 2),
        cash_flow=round(cashflow, 2),
        risk_category=category,
    )
