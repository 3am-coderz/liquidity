from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ThemePreference(str, Enum):
    light = "light"
    dark = "dark"


class RiskCategory(str, Enum):
    SAFE = "SAFE"
    STABLE = "STABLE"
    RISKY = "RISKY"
    CRITICAL = "CRITICAL"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    theme_preference: Mapped[ThemePreference] = mapped_column(SqlEnum(ThemePreference), default=ThemePreference.dark)

    companies: Mapped[list["Company"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    accounts: Mapped[list["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payables: Mapped[list["Payable"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    cash_balance: Mapped[float] = mapped_column(Float, default=0)
    monthly_income: Mapped[float] = mapped_column(Float, default=0)
    monthly_expenses: Mapped[float] = mapped_column(Float, default=0)
    upcoming_bills_total: Mapped[float] = mapped_column(Float, default=0)
    runway_days: Mapped[float] = mapped_column(Float, default=0)
    coverage_ratio: Mapped[float] = mapped_column(Float, default=0)
    cash_flow: Mapped[float] = mapped_column(Float, default=0)
    risk_category: Mapped[RiskCategory] = mapped_column(SqlEnum(RiskCategory), default=RiskCategory.CRITICAL)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="companies")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    current_balance: Mapped[float] = mapped_column(Float, default=0)
    bank_name: Mapped[str] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="accounts")


class Payable(Base):
    __tablename__ = "payables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    vendor_name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float)
    due_date: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(100))
    invoice_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    penalty_risk: Mapped[float] = mapped_column(Float, default=0.5)
    criticality: Mapped[float] = mapped_column(Float, default=0.5)
    revenue_impact: Mapped[float] = mapped_column(Float, default=0.5)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    payroll_date: Mapped[bool] = mapped_column(Boolean, default=False)
    days_overdue: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="payables")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    cycle_date: Mapped[date] = mapped_column(Date, default=date.today)
    selected_bill_ids: Mapped[str] = mapped_column(Text)
    total_paid: Mapped[float] = mapped_column(Float, default=0)
    cse_category_used: Mapped[RiskCategory] = mapped_column(SqlEnum(RiskCategory))

    user: Mapped["User"] = relationship(back_populates="decisions")
