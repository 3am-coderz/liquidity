import type { AuthResponse, ConfirmPaymentsResponse, DashboardState, EmailDraft, InvoiceUploadResponse, OptimizerResult, User } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const rawBody = await response.text();
    let message = rawBody || `Request failed: ${response.status}`;

    try {
      const parsed = JSON.parse(rawBody) as { detail?: string | { msg?: string }[] };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      } else if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
        message = parsed.detail.map((item) => item.msg ?? "Request validation failed.").join(" ");
      }
    } catch {
      // Keep the raw text when the backend didn't send JSON.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    }),
  register: (email: string, password: string, openingCashBalance: number, companyName: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, opening_cash_balance: openingCashBalance, company_name: companyName })
    }),
  me: (token: string) => request<User>("/auth/me", undefined, token),
  updateTheme: (token: string, theme: "light" | "dark") =>
    request<User>("/auth/theme", {
      method: "POST",
      body: JSON.stringify({ theme })
    }, token),
  dashboardState: (token: string) => request<DashboardState>("/dashboard-state", undefined, token),
  connectBank: (token: string) => request("/connect-bank", { method: "POST" }, token),
  resetUserData: (token: string, openingCashBalance: number) =>
    request<{ message: string }>(
      "/user-data",
      {
        method: "DELETE",
        body: JSON.stringify({ opening_cash_balance: openingCashBalance })
      },
      token
    ),
  uploadInvoice: (token: string, payload: { file?: File; debugFill?: boolean }) => {
    const formData = new FormData();
    if (payload.file) {
      formData.append("file", payload.file);
    }
    formData.append("debug_fill", String(Boolean(payload.debugFill)));
    return request<InvoiceUploadResponse>("/upload-invoice", {
      method: "POST",
      body: formData
    }, token);
  },
  runOptimizer: (token: string) => request<OptimizerResult>("/run-optimizer", { method: "POST" }, token),
  confirmPayments: (token: string, billIds: number[]) =>
    request<ConfirmPaymentsResponse>("/confirm-payments", {
      method: "POST",
      body: JSON.stringify({ bill_ids: billIds })
    }, token),
  generateEmail: (token: string, billId: number) =>
    request<EmailDraft>("/generate-email", {
      method: "POST",
      body: JSON.stringify({ bill_id: billId, tone: "empathetic" })
    }, token)
};
