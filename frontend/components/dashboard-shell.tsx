"use client";

import type { ChangeEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

import { api } from "./api";
import type { AuthResponse, DashboardState, EmailDraft, InvoiceUploadResponse, OptimizerResult, RiskCategory } from "./types";

const badgeStyles: Record<RiskCategory, string> = {
  SAFE: "bg-emerald-500/15 text-emerald-200 border-emerald-400/30",
  STABLE: "bg-sky-500/15 text-sky-200 border-sky-400/30",
  RISKY: "bg-orange-500/15 text-orange-100 border-orange-300/40",
  CRITICAL: "bg-rose-500/15 text-rose-100 border-rose-300/40"
};

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0
});

type AuthMode = "login" | "register";

export function DashboardShell() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("My Company");
  const [openingCashBalance, setOpeningCashBalance] = useState("10000");
  const [token, setToken] = useState<string | null>(null);
  const [auth, setAuth] = useState<AuthResponse | null>(null);
  const [dashboard, setDashboard] = useState<DashboardState | null>(null);
  const [optimizerResult, setOptimizerResult] = useState<OptimizerResult | null>(null);
  const [emailDraft, setEmailDraft] = useState<EmailDraft | null>(null);
  const [uploadedInvoice, setUploadedInvoice] = useState<InvoiceUploadResponse | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [selectedPaidBillIds, setSelectedPaidBillIds] = useState<number[]>([]);
  const [trustEdits, setTrustEdits] = useState<Record<number, string>>({});
  const [status, setStatus] = useState("Ready for Sarah's crisis simulation.");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const storedTheme = window.localStorage.getItem("lle-theme") as "light" | "dark" | null;
    if (storedTheme) {
      setTheme(storedTheme);
    }
    const storedToken = window.localStorage.getItem("lle-token");
    const storedAuth = window.localStorage.getItem("lle-auth");
    if (storedToken && storedAuth) {
      setToken(storedToken);
      setAuth(JSON.parse(storedAuth) as AuthResponse);
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("lle-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!token) {
      return;
    }
    void refreshDashboard(token);
  }, [token]);

  const category = dashboard?.company.risk_category ?? optimizerResult?.category;
  const spendableCash = dashboard ? Math.max(dashboard.company.cash_balance - 2000, 0) : 0;
  const hasPayables = (dashboard?.payables.length ?? 0) > 0;
  const canRunEngine = Boolean(token && hasPayables && spendableCash > 0 && !loading);

  const narrative = useMemo(() => {
    if (!dashboard) {
      return "The engine starts with financial context before it decides what to pay.";
    }
    return `${dashboard.company.company_name} is being evaluated against current cash flow, upcoming bills, and risk mode.`;
  }, [dashboard]);

  function formatCurrency(amount: number) {
    return inrFormatter.format(amount);
  }

  function formatScore(score: number | null) {
    return score == null ? "N/A" : score.toFixed(3);
  }

  async function refreshDashboard(nextToken: string) {
    try {
      const data = await api.dashboardState(nextToken);
      setDashboard(data);
      setTrustEdits(Object.fromEntries(data.payables.map((bill) => [bill.id, bill.trust_score.toFixed(2)])));
      setStatus("Dashboard synced with the latest company health snapshot.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to load dashboard.");
    }
  }

  async function handleAuth(kind: AuthMode) {
    if (kind === "register") {
      if (!companyName.trim()) {
        setStatus("Enter a company name before creating an account.");
        return;
      }
      const parsedBalance = Number(openingCashBalance || "0");
      if (Number.isNaN(parsedBalance) || parsedBalance < 0) {
        setStatus("Enter a valid non-negative opening cash balance.");
        return;
      }
    }

    setLoading(true);
    setEmailDraft(null);
    setOptimizerResult(null);
    setUploadedInvoice(null);
    setSelectedPaidBillIds([]);
    try {
      const result =
        kind === "login"
          ? await api.login(email, password)
          : await api.register(email, password, Number(openingCashBalance || "0"), companyName);

      setAuth(result);
      setToken(result.token.access_token);
      window.localStorage.setItem("lle-token", result.token.access_token);
      window.localStorage.setItem("lle-auth", JSON.stringify(result));
      setTheme(result.user.theme_preference);
      setStatus(kind === "login" ? "Authentication complete." : "Account created with your opening cash balance.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleThemeToggle() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    if (token) {
      try {
        await api.updateTheme(token, nextTheme);
      } catch {
        setStatus("Theme changed locally, but the API preference update failed.");
      }
    }
  }

  async function handleBankSync() {
    if (!token) return;
    setLoading(true);
    try {
      await api.connectBank(token);
      await refreshDashboard(token);
      setStatus("Plaid mock sync refreshed Sarah's operating cash.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Bank sync failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleInvoiceUpload(file?: File) {
    if (!token) return;
    setLoading(true);
    try {
      const response = await api.uploadInvoice(token, { file, debugFill: !file });
      setUploadedInvoice(response);
      await refreshDashboard(token);
      setStatus(
        file
          ? `OCR parsed ${response.source_file_name ?? "the uploaded invoice"} and created a payable.`
          : "Debug OCR injected an emergency invoice for the demo."
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Invoice upload failed.");
    } finally {
      setLoading(false);
    }
  }

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  async function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFileName(file.name);
    await handleInvoiceUpload(file);
    event.target.value = "";
  }

  async function handleOptimize() {
    if (!token) return;
    if (!hasPayables) {
      setStatus("Upload or add at least one payable before running the engine.");
      return;
    }
    if (spendableCash <= 0) {
      setStatus(
        `Run engine is blocked because only ${formatCurrency(dashboard?.company.cash_balance ?? 0)} is available and the app must preserve a Rs 2,000 cash floor.`
      );
      return;
    }
    setLoading(true);
    try {
      const result = await api.runOptimizer(token);
      setOptimizerResult(result);
      setSelectedPaidBillIds(result.selected_bills.map((bill) => bill.id));
      await refreshDashboard(token);
      setStatus("Survival engine ran the context-aware payment strategy.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Optimization failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleEmailDraft(billId?: number) {
    const targetBillId = billId ?? dashboard?.payables[0]?.id;
    if (!token || !targetBillId) {
      setStatus("No unpaid bill is available for negotiation email generation.");
      return;
    }
    setLoading(true);
    try {
      const draft = await api.generateEmail(token, targetBillId);
      setEmailDraft(draft);
      setStatus("Vendor email draft generated for the selected unpaid bill.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Email generation failed.");
    } finally {
      setLoading(false);
    }
  }

  function toggleBillSelection(billId: number) {
    setSelectedPaidBillIds((current) =>
      current.includes(billId) ? current.filter((id) => id !== billId) : [...current, billId]
    );
  }

  async function handleTrustScoreSave(billId: number) {
    if (!token) return;
    const parsedValue = Number(trustEdits[billId]);
    if (Number.isNaN(parsedValue) || parsedValue < 0 || parsedValue > 1) {
      setStatus("Trust score must be between 0.00 and 1.00.");
      return;
    }
    setLoading(true);
    try {
      await api.updateTrustScore(token, billId, parsedValue);
      await refreshDashboard(token);
      setStatus("Trust score updated for the selected vendor.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to update trust score.");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmPayments() {
    if (!token || selectedPaidBillIds.length === 0) {
      setStatus("Select at least one bill to confirm payment.");
      return;
    }
    setLoading(true);
    try {
      const result = await api.confirmPayments(token, selectedPaidBillIds);
      setSelectedPaidBillIds([]);
      setOptimizerResult(null);
      setEmailDraft(null);
      await refreshDashboard(token);
      setStatus(
        `${result.message} Paid ${formatCurrency(result.total_paid)}. Remaining balance: ${formatCurrency(result.remaining_cash_balance)}.`
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to confirm bill payments.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteMyData() {
    if (!token) return;
    const enteredAmount = window.prompt("Enter your current cash balance in INR after clearing the old data:", "0");
    if (enteredAmount === null) {
      return;
    }
    const parsedAmount = Number(enteredAmount);
    if (Number.isNaN(parsedAmount) || parsedAmount < 0) {
      setStatus("Please enter a valid non-negative cash balance before deleting data.");
      return;
    }
    setLoading(true);
    try {
      const result = await api.resetUserData(token, parsedAmount);
      setUploadedInvoice(null);
      setOptimizerResult(null);
      setEmailDraft(null);
      setSelectedFileName(null);
      setSelectedPaidBillIds([]);
      await refreshDashboard(token);
      setStatus(result.message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to delete user data.");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setToken(null);
    setAuth(null);
    setDashboard(null);
    setOptimizerResult(null);
    setEmailDraft(null);
    setSelectedFileName(null);
    setSelectedPaidBillIds([]);
    window.localStorage.removeItem("lle-token");
    window.localStorage.removeItem("lle-auth");
    setStatus("Session cleared.");
  }

  if (!token || !auth) {
    return (
      <main className="mx-auto flex min-h-screen max-w-7xl flex-col justify-center px-6 py-10">
        <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="glass rounded-[2rem] p-10">
            <div className="mb-8 flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-[var(--muted)]">Liquidity Logic Engine</p>
                <h1 className="mt-3 max-w-xl text-5xl font-semibold leading-tight">Cash survival decisions for founders operating in the red.</h1>
              </div>
              <button
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-[var(--muted)] transition hover:border-white/20"
                onClick={handleThemeToggle}
                type="button"
              >
                {theme === "dark" ? "Light mode" : "Dark mode"}
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {[
                ["Health First", "CSE classifies the company before optimization."],
                ["Strategy Switch", "SAFE, STABLE, RISKY, and CRITICAL each alter the payment logic."],
                ["Action Ready", "Explain delayed bills instantly with a negotiation draft."]
              ].map(([title, copy]) => (
                <article key={title} className="rounded-3xl border border-white/10 bg-black/10 p-5">
                  <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">{title}</p>
                  <p className="mt-3 text-sm leading-6 text-[var(--text)]/80">{copy}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="glass rounded-[2rem] p-8">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Access</p>
                <h2 className="mt-2 text-3xl font-semibold">{authMode === "login" ? "Login" : "Create your account"}</h2>
              </div>
            </div>

            <div className="mb-5 inline-flex rounded-full border border-white/10 p-1 text-sm">
              {(["login", "register"] as const).map((mode) => (
                <button
                  key={mode}
                  className={`rounded-full px-4 py-2 transition ${authMode === mode ? "bg-white/10 text-[var(--text)]" : "text-[var(--muted)]"}`}
                  onClick={() => setAuthMode(mode)}
                  type="button"
                >
                  {mode === "login" ? "Login" : "Register"}
                </button>
              ))}
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="mb-2 block text-sm text-[var(--muted)]">Email</span>
                <input
                  className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)] outline-none ring-0 transition focus:border-white/20 focus:shadow-[0_0_0_4px_var(--ring)]"
                  onChange={(event) => setEmail(event.target.value)}
                  value={email}
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-sm text-[var(--muted)]">Password</span>
                <input
                  className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)] outline-none ring-0 transition focus:border-white/20 focus:shadow-[0_0_0_4px_var(--ring)]"
                  onChange={(event) => setPassword(event.target.value)}
                  type="password"
                  value={password}
                />
              </label>
              {authMode === "register" ? (
                <>
                  <label className="block">
                    <span className="mb-2 block text-sm text-[var(--muted)]">Company Name</span>
                    <input
                      className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)] outline-none ring-0 transition focus:border-white/20 focus:shadow-[0_0_0_4px_var(--ring)]"
                      onChange={(event) => setCompanyName(event.target.value)}
                      value={companyName}
                    />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm text-[var(--muted)]">Opening Cash Balance (INR)</span>
                    <input
                      className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)] outline-none ring-0 transition focus:border-white/20 focus:shadow-[0_0_0_4px_var(--ring)]"
                      min="0"
                      onChange={(event) => setOpeningCashBalance(event.target.value)}
                      step="0.01"
                      type="number"
                      value={openingCashBalance}
                    />
                  </label>
                </>
              ) : null}
              <button
                className="w-full rounded-2xl bg-teal px-4 py-3 font-medium text-slate-950 transition hover:opacity-90"
                disabled={loading}
                onClick={() => void handleAuth(authMode)}
                type="button"
              >
                {loading ? "Working..." : authMode === "login" ? "Login" : "Create account"}
              </button>
            </div>

            <p className="mt-4 text-sm text-[var(--muted)]">{status}</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-8">
      <section className="mb-6 flex flex-col gap-4 rounded-[2rem] glass p-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-[var(--muted)]">Liquidity Logic Engine</p>
          <h1 className="mt-2 text-4xl font-semibold">Meet Sarah, a cafe owner balancing survival against supplier trust.</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">{narrative}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {category ? (
            <span className={`rounded-full border px-4 py-2 text-sm font-semibold ${badgeStyles[category]}`}>{category}</span>
          ) : null}
          <button
            className="rounded-full border border-white/10 px-4 py-2 text-sm text-[var(--muted)] transition hover:border-white/20"
            onClick={handleThemeToggle}
            type="button"
          >
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <button
            className="rounded-full border border-white/10 px-4 py-2 text-sm text-[var(--muted)] transition hover:border-white/20"
            onClick={logout}
            type="button"
          >
            Logout
          </button>
          <Link
            className="rounded-full border border-white/10 px-4 py-2 text-sm text-[var(--muted)] transition hover:border-white/20"
            href="/upload-data"
          >
            Upload data
          </Link>
          <button
            className="rounded-full border border-rose-400/20 px-4 py-2 text-sm text-rose-200 transition hover:border-rose-400/40"
            onClick={() => void handleDeleteMyData()}
            type="button"
          >
            Delete my data
          </button>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            {dashboard &&
              [
                ["Balance", formatCurrency(dashboard.company.cash_balance)],
                ["Cash Flow", formatCurrency(dashboard.company.cash_flow)],
                ["Bills", formatCurrency(dashboard.company.upcoming_bills_total)]
              ].map(([label, value]) => (
                <article key={label} className="glass rounded-3xl p-5">
                  <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">{label}</p>
                  <p className="mt-4 text-2xl font-semibold">{value}</p>
                </article>
              ))}
          </div>

          <div className="glass rounded-[2rem] p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Command Deck</p>
                <h2 className="mt-2 text-2xl font-semibold">Hackathon demo controls</h2>
              </div>
              <p className="text-sm text-[var(--muted)]">{status}</p>
            </div>

            <div className="grid gap-3 md:grid-cols-4">
              <button className="rounded-3xl bg-sky-500/15 px-4 py-4 text-left transition hover:bg-sky-500/25" onClick={() => void handleBankSync()} type="button">
                <span className="block text-sm uppercase tracking-[0.2em] text-sky-200">Step 1</span>
                <span className="mt-2 block font-medium">Sync bank</span>
              </button>
              <button className="rounded-3xl bg-amber-300/15 px-4 py-4 text-left transition hover:bg-amber-300/25" onClick={openFilePicker} type="button">
                <span className="block text-sm uppercase tracking-[0.2em] text-amber-100">Step 2</span>
                <span className="mt-2 block font-medium">Upload real file</span>
              </button>
              <button
                className="rounded-3xl bg-emerald-500/15 px-4 py-4 text-left transition hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!canRunEngine}
                onClick={() => void handleOptimize()}
                type="button"
              >
                <span className="block text-sm uppercase tracking-[0.2em] text-emerald-100">Step 3</span>
                <span className="mt-2 block font-medium">
                  {!hasPayables ? "Add a bill first" : spendableCash <= 0 ? "Need more cash" : "Run engine"}
                </span>
              </button>
              <button className="rounded-3xl bg-rose-500/15 px-4 py-4 text-left transition hover:bg-rose-500/25" onClick={() => void handleEmailDraft()} type="button">
                <span className="block text-sm uppercase tracking-[0.2em] text-rose-100">Step 4</span>
                <span className="mt-2 block font-medium">Generate email</span>
              </button>
            </div>
            <p className="mt-3 text-sm text-[var(--muted)]">
              {hasPayables
                ? `Spendable cash for the engine: ${formatCurrency(spendableCash)} after preserving the Rs 2,000 safety floor.`
                : "Add a payable to unlock the engine."}
            </p>
            <input
              accept="image/png,image/jpeg,image/jpg,image/webp,image/tiff,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp"
              className="hidden"
              onChange={(event) => void handleFileSelected(event)}
              ref={fileInputRef}
              type="file"
            />
            <p className="mt-3 text-sm text-[var(--muted)]">
              {selectedFileName ? `Selected file: ${selectedFileName}` : "Upload a PNG, JPG, WEBP, TIFF, or BMP invoice for Tesseract OCR."}
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="glass rounded-[2rem] p-6">
              <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Payables</p>
              <h2 className="mt-2 text-2xl font-semibold">Upcoming bills</h2>
              <div className="mt-5 space-y-3">
                {dashboard?.payables.map((bill) => (
                  <article key={bill.id} className="rounded-3xl border border-white/10 bg-black/10 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{bill.vendor_name}</p>
                        <p className="mt-1 text-sm text-[var(--muted)]">{bill.category} due {bill.due_date}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.2em] text-orange-200">{bill.priority_label} priority</p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span className="text-lg font-semibold">{formatCurrency(bill.amount)}</span>
                        <button
                          className="rounded-full border border-amber-200/20 px-3 py-1 text-xs uppercase tracking-[0.2em] text-amber-100 transition hover:border-amber-200/40"
                          onClick={() => void handleEmailDraft(bill.id)}
                          type="button"
                        >
                          Generate mail
                        </button>
                      </div>
                    </div>
                    <p className="mt-3 text-sm text-[var(--muted)]">{bill.priority_reason}</p>
                    <div className="mt-4 flex flex-wrap items-end gap-3">
                      <label className="text-sm text-[var(--muted)]">
                        <span className="mb-2 block">Trust score</span>
                        <input
                          className="w-32 rounded-2xl border border-white/10 bg-black/10 px-3 py-2 text-[var(--text)]"
                          max="1"
                          min="0"
                          onChange={(event) => setTrustEdits((current) => ({ ...current, [bill.id]: event.target.value }))}
                          step="0.01"
                          type="number"
                          value={trustEdits[bill.id] ?? bill.trust_score.toFixed(2)}
                        />
                      </label>
                      <button
                        className="rounded-full border border-white/10 px-3 py-2 text-xs uppercase tracking-[0.2em] text-[var(--muted)] transition hover:border-white/20"
                        disabled={loading}
                        onClick={() => void handleTrustScoreSave(bill.id)}
                        type="button"
                      >
                        Save trust
                      </button>
                    </div>
                  </article>
                ))}
                {dashboard?.payables.length === 0 ? <p className="text-sm text-[var(--muted)]">No bills uploaded yet for this user.</p> : null}
              </div>
            </section>

            <section className="glass rounded-[2rem] p-6">
              <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Decision Output</p>
              <h2 className="mt-2 text-2xl font-semibold">Optimization result</h2>
              {optimizerResult ? (
                <div className="mt-5 space-y-4">
                  <div className="rounded-3xl bg-emerald-500/10 p-4">
                    <p className="text-sm text-emerald-100">Paid this cycle</p>
                    <p className="mt-2 text-2xl font-semibold">{formatCurrency(optimizerResult.total_selected_amount)}</p>
                    <p className="mt-2 text-sm text-[var(--muted)]">{optimizerResult.explanation}</p>
                  </div>
                  <div>
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Bills to pay</p>
                      <button
                        className="rounded-full bg-teal px-4 py-2 text-xs font-semibold text-slate-950 transition hover:opacity-90"
                        disabled={loading}
                        onClick={() => void handleConfirmPayments()}
                        type="button"
                      >
                        Confirm paid
                      </button>
                    </div>
                    <div className="space-y-2">
                      {[...optimizerResult.selected_bills, ...optimizerResult.delayed_bills].map((bill) => (
                        <div key={bill.id} className="rounded-2xl border border-white/10 px-4 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <label className="flex items-center gap-3">
                              <input
                                checked={selectedPaidBillIds.includes(bill.id)}
                                onChange={() => toggleBillSelection(bill.id)}
                                type="checkbox"
                              />
                              <span>{bill.vendor_name} - {formatCurrency(bill.amount)}</span>
                            </label>
                            <span className="text-xs uppercase tracking-[0.2em] text-emerald-200">Score {formatScore(bill.score)}</span>
                          </div>
                          <p className="mt-2 text-xs uppercase tracking-[0.2em] text-[var(--muted)]">{bill.priority_label} priority</p>
                          <p className="mt-2 text-xs text-[var(--muted)]">Trust score {bill.trust_score.toFixed(2)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-2 text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Engine recommendation</p>
                    <div className="space-y-2">
                      {optimizerResult.selected_bills.map((bill) => (
                        <div key={bill.id} className="rounded-2xl border border-white/10 px-4 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <span>{bill.vendor_name} - {formatCurrency(bill.amount)}</span>
                            <span className="text-xs uppercase tracking-[0.2em] text-emerald-200">Recommended pay · Score {formatScore(bill.score)}</span>
                          </div>
                          <p className="mt-2 text-xs text-[var(--muted)]">Trust score {bill.trust_score.toFixed(2)}</p>
                        </div>
                      ))}
                      {optimizerResult.delayed_bills.map((bill) => (
                        <div key={bill.id} className="rounded-2xl border border-white/10 px-4 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <span>{bill.vendor_name} - {formatCurrency(bill.amount)}</span>
                            <span className="text-xs uppercase tracking-[0.2em] text-rose-200">Recommended delay · Score {formatScore(bill.score)}</span>
                          </div>
                          <p className="mt-2 text-xs text-[var(--muted)]">Trust score {bill.trust_score.toFixed(2)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="mt-5 text-sm leading-6 text-[var(--muted)]">Run the engine to see which bills are paid, which are delayed, and how the current CSE category changes the strategy.</p>
              )}
            </section>
          </div>
        </div>

        <div className="space-y-6">
          <section className="glass rounded-[2rem] p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Health Indicator</p>
            <h2 className="mt-2 text-2xl font-semibold">{dashboard?.company.company_name ?? "Waiting for company data"}</h2>
            <div className="mt-5 rounded-[2rem] bg-black/15 p-5">
              <div className="h-3 rounded-full bg-white/10">
                <div
                  className={`h-3 rounded-full ${
                    category === "SAFE" ? "bg-emerald-400 w-full" : category === "STABLE" ? "bg-sky-400 w-3/4" : category === "RISKY" ? "bg-orange-400 w-1/2" : "bg-rose-400 w-1/4"
                  }`}
                />
              </div>
              <p className="mt-4 text-sm leading-6 text-[var(--muted)]">{dashboard?.suggested_action}</p>
            </div>
          </section>

          <section className="glass rounded-[2rem] p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Recent Decisions</p>
            <div className="mt-4 space-y-3">
              {dashboard?.recent_decisions.map((decision) => (
                <article key={decision.id} className="rounded-3xl border border-white/10 bg-black/10 p-4">
                  <p className="font-medium">{decision.cse_category_used} cycle on {decision.cycle_date}</p>
                  <p className="mt-1 text-sm text-[var(--muted)]">Paid {formatCurrency(decision.total_paid)} across {decision.selected_bill_ids.length} bills.</p>
                </article>
              ))}
            </div>
          </section>

          <section className="glass rounded-[2rem] p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Negotiation Draft</p>
            {emailDraft ? (
              <div className="mt-4 rounded-3xl bg-black/15 p-5">
                <p className="text-sm text-[var(--muted)]">{emailDraft.subject}</p>
                <pre className="mt-4 whitespace-pre-wrap font-sans text-sm leading-6 text-[var(--text)]">{emailDraft.body}</pre>
              </div>
            ) : (
              <p className="mt-4 text-sm leading-6 text-[var(--muted)]">Generate an email after optimization and the app will draft a supplier note for the first delayed bill.</p>
            )}
          </section>

          <section className="glass rounded-[2rem] p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">OCR Result</p>
            {uploadedInvoice ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-3xl bg-black/15 p-5">
                  <p className="text-sm text-[var(--muted)]">
                    {uploadedInvoice.ocr_engine.toUpperCase()} parsed {uploadedInvoice.source_file_name ?? uploadedInvoice.payable.vendor_name}
                  </p>
                  <p className="mt-3 text-lg font-semibold">{uploadedInvoice.payable.vendor_name}</p>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    {formatCurrency(uploadedInvoice.payable.amount)} due {uploadedInvoice.payable.due_date}
                  </p>
                </div>
                {uploadedInvoice.parsed_invoice ? (
                  <div className="rounded-3xl border border-white/10 p-4 text-sm text-[var(--muted)]">
                    <p>Detected category: {uploadedInvoice.parsed_invoice.category ?? "Unknown"}</p>
                    <p className="mt-2">Detected priority: {uploadedInvoice.parsed_invoice.priority_label ?? "Unknown"}</p>
                    <p className="mt-2">Priority reason: {uploadedInvoice.parsed_invoice.priority_reason ?? "Unknown"}</p>
                    <p className="mt-2">Detected amount: {uploadedInvoice.parsed_invoice.amount != null ? formatCurrency(uploadedInvoice.parsed_invoice.amount) : "Unknown"}</p>
                    <p className="mt-2">Detected due date: {uploadedInvoice.parsed_invoice.due_date ?? "Unknown"}</p>
                    {uploadedInvoice.parsed_invoice.confidence_notes.length > 0 ? (
                      <p className="mt-2">Notes: {uploadedInvoice.parsed_invoice.confidence_notes.join(" ")}</p>
                    ) : null}
                  </div>
                ) : null}
                {uploadedInvoice.extracted_text ? (
                  <div className="rounded-3xl border border-white/10 p-4">
                    <p className="mb-2 text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Extracted text</p>
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-6 text-[var(--text)]">
                      {uploadedInvoice.extracted_text}
                    </pre>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="mt-4 text-sm leading-6 text-[var(--muted)]">Upload a real invoice image and the parsed OCR output will appear here.</p>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
