"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { api } from "./api";
import type { AuthResponse, InvoiceUploadResponse } from "./types";

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0
});

const categories = ["Operations", "Inventory", "Utilities", "Payroll", "Legal", "Rent", "Tax"] as const;

export function UploadDataShell() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [vendorName, setVendorName] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [category, setCategory] = useState<(typeof categories)[number]>("Operations");
  const [fileTrustScore, setFileTrustScore] = useState("");
  const [manualTrustScore, setManualTrustScore] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("Upload an invoice image or enter a payable manually.");
  const [result, setResult] = useState<InvoiceUploadResponse | null>(null);

  const token = useMemo(() => {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem("lle-token");
  }, []);

  const auth = useMemo(() => {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem("lle-auth");
    if (!raw) return null;
    try {
      return JSON.parse(raw) as AuthResponse;
    } catch {
      return null;
    }
  }, []);

  async function handleFileUpload() {
    if (!token || !selectedFile) return;
    const parsedTrustScore = fileTrustScore.trim() === "" ? undefined : Number(fileTrustScore);
    if (parsedTrustScore != null && (Number.isNaN(parsedTrustScore) || parsedTrustScore < 0 || parsedTrustScore > 1)) {
      setStatus("Trust score must be between 0.00 and 1.00.");
      return;
    }
    setLoading(true);
    try {
      const response = await api.uploadInvoice(token, { file: selectedFile, trustScore: parsedTrustScore });
      setResult(response);
      setStatus(`OCR parsed ${response.source_file_name ?? selectedFile.name} and created a payable.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "File upload failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleManualSubmit() {
    if (!token) return;
    const parsedAmount = Number(amount);
    if (!vendorName.trim()) {
      setStatus("Enter a vendor name for the manual bill.");
      return;
    }
    if (Number.isNaN(parsedAmount) || parsedAmount <= 0) {
      setStatus("Enter a valid amount greater than zero.");
      return;
    }
    if (!dueDate) {
      setStatus("Choose a due date for the manual bill.");
      return;
    }
    const parsedTrustScore = manualTrustScore.trim() === "" ? undefined : Number(manualTrustScore);
    if (parsedTrustScore != null && (Number.isNaN(parsedTrustScore) || parsedTrustScore < 0 || parsedTrustScore > 1)) {
      setStatus("Trust score must be between 0.00 and 1.00.");
      return;
    }

    setLoading(true);
    try {
      const response = await api.uploadInvoice(token, {
        vendorName: vendorName.trim(),
        amount: parsedAmount,
        dueDate,
        category,
        trustScore: parsedTrustScore
      });
      setResult(response);
      setStatus(`Manual payable created for ${response.payable.vendor_name}.`);
      setVendorName("");
      setAmount("");
      setDueDate("");
      setCategory("Operations");
      setManualTrustScore("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Manual entry failed.");
    } finally {
      setLoading(false);
    }
  }

  if (!token || !auth) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl items-center px-6 py-10">
        <section className="glass w-full rounded-[2rem] p-8">
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Data Upload</p>
          <h1 className="mt-3 text-3xl font-semibold">Login required</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
            Open the dashboard first, sign in, and then return here to upload invoice files or enter payable data manually.
          </p>
          <Link className="mt-6 inline-flex rounded-2xl bg-teal px-4 py-3 font-medium text-slate-950" href="/">
            Back to dashboard
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-8">
      <section className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-[2rem] glass p-6">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Data Upload</p>
          <h1 className="mt-2 text-4xl font-semibold">Add payables your way</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Signed in as {auth.user.email}. Upload an invoice image for OCR or enter a bill manually when you already know the amount.
          </p>
        </div>
        <Link className="rounded-full border border-white/10 px-4 py-2 text-sm text-[var(--muted)] transition hover:border-white/20" href="/">
          Back to dashboard
        </Link>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="glass rounded-[2rem] p-6">
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">OCR Upload</p>
          <h2 className="mt-2 text-2xl font-semibold">Upload invoice file</h2>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
            Best for invoice photos, screenshots, and scans where you want the app to extract vendor, amount, due date, and category.
            The trust score starts at the engine default and you can override it before saving.
          </p>
          <input
            accept="image/png,image/jpeg,image/jpg,image/webp,image/tiff,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp"
            className="mt-6 block w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-sm text-[var(--text)]"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <label className="mt-4 block text-sm text-[var(--muted)]">
            <span className="mb-2 block">Trust score (0 to 1)</span>
            <input
              className="block w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-sm text-[var(--text)]"
              max="1"
              min="0"
              onChange={(event) => setFileTrustScore(event.target.value)}
              placeholder="Use default"
              step="0.01"
              type="number"
              value={fileTrustScore}
            />
          </label>
          <button
            className="mt-4 rounded-2xl bg-amber-300/90 px-4 py-3 font-medium text-slate-950 transition hover:opacity-90 disabled:opacity-60"
            disabled={loading || !selectedFile}
            onClick={() => void handleFileUpload()}
            type="button"
          >
            {loading ? "Uploading..." : "Upload file"}
          </button>
          <p className="mt-3 text-sm text-[var(--muted)]">{selectedFile ? `Selected: ${selectedFile.name}` : "No file selected yet."}</p>
        </article>

        <article className="glass rounded-[2rem] p-6">
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Manual Entry</p>
          <h2 className="mt-2 text-2xl font-semibold">Enter bill details</h2>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
            Best when you already know the payable information and want to add it directly without relying on OCR.
          </p>
          <div className="mt-6 space-y-4">
            <input
              className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)]"
              onChange={(event) => setVendorName(event.target.value)}
              placeholder="Vendor name"
              value={vendorName}
            />
            <input
              className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)]"
              min="0"
              onChange={(event) => setAmount(event.target.value)}
              placeholder="Amount"
              step="0.01"
              type="number"
              value={amount}
            />
            <input
              className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)]"
              onChange={(event) => setDueDate(event.target.value)}
              type="date"
              value={dueDate}
            />
            <select
              className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)]"
              onChange={(event) => setCategory(event.target.value as (typeof categories)[number])}
              value={category}
            >
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <input
              className="w-full rounded-2xl border border-white/10 bg-black/10 px-4 py-3 text-[var(--text)]"
              max="1"
              min="0"
              onChange={(event) => setManualTrustScore(event.target.value)}
              placeholder="Trust score (0 to 1, blank = default)"
              step="0.01"
              type="number"
              value={manualTrustScore}
            />
          </div>
          <button
            className="mt-4 rounded-2xl bg-teal px-4 py-3 font-medium text-slate-950 transition hover:opacity-90 disabled:opacity-60"
            disabled={loading}
            onClick={() => void handleManualSubmit()}
            type="button"
          >
            {loading ? "Saving..." : "Create manual payable"}
          </button>
        </article>
      </section>

      <section className="mt-6 glass rounded-[2rem] p-6">
        <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Status</p>
        <p className="mt-3 text-sm leading-6 text-[var(--text)]/85">{status}</p>

        {result ? (
          <div className="mt-5 rounded-3xl border border-white/10 bg-black/10 p-5">
            <p className="text-sm text-[var(--muted)]">Latest payable</p>
            <p className="mt-2 text-xl font-semibold">{result.payable.vendor_name}</p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {inrFormatter.format(result.payable.amount)} due {result.payable.due_date} in {result.payable.category}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">Trust score: {result.payable.trust_score.toFixed(2)}</p>
            {result.parsed_invoice ? (
              <p className="mt-3 text-sm text-[var(--muted)]">
                OCR priority: {result.parsed_invoice.priority_label ?? "Unknown"}.
              </p>
            ) : null}
          </div>
        ) : null}
      </section>
    </main>
  );
}
