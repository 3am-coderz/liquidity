from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import RiskCategory, ThemePreference


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    opening_cash_balance: float = Field(ge=0)
    company_name: str = Field(default="My Company", min_length=2, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime
    theme_preference: ThemePreference


class AuthResponse(BaseModel):
    user: UserOut
    token: Token


class CompanyMetricsResponse(BaseModel):
    company_name: str
    cash_balance: float
    monthly_income: float
    monthly_expenses: float
    upcoming_bills_total: float
    runway_days: float
    coverage_ratio: float
    cash_flow: float
    risk_category: RiskCategory


class ClassifyCompanyRequest(BaseModel):
    cash_balance: float
    monthly_income: float
    monthly_expenses: float
    upcoming_bills_total: float


class PayableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_name: str
    amount: float
    due_date: date
    category: str
    invoice_url: str | None
    is_critical: bool
    payroll_date: bool
    days_overdue: int
    priority_label: str
    priority_reason: str
    score: float | None = None
    is_hard_constraint: bool | None = None
    survival_impact: float | None = None


class OCRParseSummary(BaseModel):
    vendor_name: str | None = None
    amount: float | None = None
    due_date: date | None = None
    category: str | None = None
    priority_label: str | None = None
    priority_reason: str | None = None
    confidence_notes: list[str] = []


class DecisionOut(BaseModel):
    id: int
    cycle_date: date
    selected_bill_ids: list[int]
    total_paid: float
    cse_category_used: RiskCategory


class OptimizerDecisionResponse(BaseModel):
    category: RiskCategory
    strategy: str
    available_cash: float
    cash_floor: float
    total_selected_amount: float
    projected_runway_days: float
    selected_bills: list[PayableOut]
    delayed_bills: list[PayableOut]
    explanation: str


class ConfirmPaymentsRequest(BaseModel):
    bill_ids: list[int] = Field(min_length=1)


class ConfirmPaymentsResponse(BaseModel):
    paid_bill_ids: list[int]
    total_paid: float
    remaining_cash_balance: float
    remaining_upcoming_bills_total: float
    message: str


class InvoiceUploadRequest(BaseModel):
    vendor_name: str | None = None
    amount: float | None = None
    due_date: date | None = None
    category: str | None = None
    debug_fill: bool = False


class InvoiceUploadResponse(BaseModel):
    payable: PayableOut
    extracted_text: str | None = None
    parsed_invoice: OCRParseSummary | None = None
    source_file_name: str | None = None
    ocr_engine: str


class ConnectBankResponse(BaseModel):
    bank_name: str
    current_balance: float
    synced_at: datetime


class ResetUserDataResponse(BaseModel):
    message: str


class ResetUserDataRequest(BaseModel):
    opening_cash_balance: float = Field(ge=0)


class EmailGenerationRequest(BaseModel):
    bill_id: int
    tone: Literal["empathetic", "firm", "neutral"] = "empathetic"


class EmailGenerationResponse(BaseModel):
    subject: str
    body: str


class DashboardStateResponse(BaseModel):
    company: CompanyMetricsResponse
    accounts_total: float
    payables: list[PayableOut]
    recent_decisions: list[DecisionOut]
    health_badge_color: str
    suggested_action: str
