from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .auth import hash_password
from .config import settings
from .models import Account, Company, Decision, Payable, User
from .services.cse import classify_company


def seed_demo_data(db: Session) -> None:
    existing_user = db.query(User).filter(User.email == settings.demo_user_email).first()
    if existing_user:
        return

    demo_user = User(
        email=settings.demo_user_email,
        password_hash=hash_password(settings.demo_user_password),
    )
    db.add(demo_user)
    db.flush()

    cash_balance = 24000.0
    monthly_income = 52000.0
    monthly_expenses = 20500.0
    upcoming_bills_total = 30000.0
    metrics = classify_company(cash_balance, monthly_income, monthly_expenses, upcoming_bills_total)

    company = Company(
        user_id=demo_user.id,
        company_name="Sarah's Corner Cafe",
        cash_balance=cash_balance,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        upcoming_bills_total=upcoming_bills_total,
        runway_days=metrics.runway_days,
        coverage_ratio=metrics.coverage_ratio,
        cash_flow=metrics.cash_flow,
        risk_category=metrics.risk_category,
        last_updated=datetime.utcnow(),
    )
    db.add(company)
    db.add(Account(user_id=demo_user.id, current_balance=cash_balance, bank_name="Plaid Mock Bank"))

    db.add_all(
        [
            Payable(
                user_id=demo_user.id,
                vendor_name="Main Street Landlord",
                amount=11000,
                due_date=date.today() + timedelta(days=1),
                category="Rent",
                invoice_url="/demo/rent.pdf",
                trust_score=0.8,
                penalty_risk=0.9,
                criticality=0.8,
                revenue_impact=0.7,
                is_critical=False,
                payroll_date=False,
                days_overdue=0,
            ),
            Payable(
                user_id=demo_user.id,
                vendor_name="Blue Bottle Beans",
                amount=7000,
                due_date=date.today() + timedelta(days=3),
                category="Inventory",
                invoice_url="/demo/beans.pdf",
                trust_score=0.7,
                penalty_risk=0.3,
                criticality=0.6,
                revenue_impact=0.9,
                is_critical=False,
                payroll_date=False,
                days_overdue=0,
            ),
            Payable(
                user_id=demo_user.id,
                vendor_name="Cafe Payroll",
                amount=12000,
                due_date=date.today(),
                category="Payroll",
                invoice_url="/demo/payroll.pdf",
                trust_score=1.0,
                penalty_risk=1.0,
                criticality=1.0,
                revenue_impact=1.0,
                is_critical=True,
                payroll_date=True,
                days_overdue=0,
            ),
        ]
    )

    db.add(
        Decision(
            user_id=demo_user.id,
            cycle_date=date.today() - timedelta(days=1),
            selected_bill_ids="1,3",
            total_paid=23000,
            cse_category_used=metrics.risk_category,
        )
    )

    db.commit()
