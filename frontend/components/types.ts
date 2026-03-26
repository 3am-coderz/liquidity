export type RiskCategory = "SAFE" | "STABLE" | "RISKY" | "CRITICAL";

export type User = {
  id: number;
  email: string;
  created_at: string;
  theme_preference: "light" | "dark";
};

export type AuthResponse = {
  user: User;
  token: {
    access_token: string;
    token_type: string;
  };
};

export type Company = {
  company_name: string;
  cash_balance: number;
  monthly_income: number;
  monthly_expenses: number;
  upcoming_bills_total: number;
  runway_days: number;
  coverage_ratio: number;
  cash_flow: number;
  risk_category: RiskCategory;
};

export type Payable = {
  id: number;
  vendor_name: string;
  amount: number;
  due_date: string;
  category: string;
  invoice_url: string | null;
  is_critical: boolean;
  payroll_date: boolean;
  days_overdue: number;
  priority_label: string;
  priority_reason: string;
  trust_score: number;
  score: number | null;
  is_hard_constraint?: boolean | null;
  survival_impact?: number | null;
};

export type OCRParseSummary = {
  vendor_name: string | null;
  amount: number | null;
  due_date: string | null;
  category: string | null;
  priority_label: string | null;
  priority_reason: string | null;
  confidence_notes: string[];
};

export type InvoiceUploadResponse = {
  payable: Payable | null;
  manual_transaction?: ManualTransactionResult | null;
  extracted_text: string | null;
  parsed_invoice: OCRParseSummary | null;
  source_file_name: string | null;
  ocr_engine: string;
};

export type ManualTransactionResult = {
  transaction_id: string;
  direction: "money_in" | "money_out";
  amount: number;
  balance: number;
  monthly_income: number;
  monthly_expense: number;
};

export type Decision = {
  id: number;
  cycle_date: string;
  selected_bill_ids: number[];
  total_paid: number;
  cse_category_used: RiskCategory;
};

export type DashboardState = {
  company: Company;
  accounts_total: number;
  payables: Payable[];
  recent_decisions: Decision[];
  health_badge_color: string;
  suggested_action: string;
};

export type ConnectBankResult = {
  bank_name: string;
  current_balance: number | null;
  synced_at: string | null;
  consent_id: string | null;
  approval_url: string | null;
  status: string;
  source: string;
};

export type OptimizerResult = {
  category: RiskCategory;
  strategy: string;
  available_cash: number;
  cash_floor: number;
  total_selected_amount: number;
  projected_runway_days: number;
  selected_bills: Payable[];
  delayed_bills: Payable[];
  explanation: string;
};

export type ConfirmPaymentsResponse = {
  paid_bill_ids: number[];
  total_paid: number;
  remaining_cash_balance: number;
  remaining_upcoming_bills_total: number;
  message: string;
};

export type EmailDraft = {
  subject: string;
  body: string;
};
