"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "./api";
import type { PaidBillOut } from "./types";

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0
});

export function HistoryPage() {
  const [bills, setBills] = useState<PaidBillOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = window.localStorage.getItem("lle-token");
    if (!token) {
      window.location.href = "/";
      return;
    }
    
    api.getPaidBills(token)
      .then(setBills)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load history"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-8">
      <section className="mb-6 flex flex-col gap-4 rounded-[2rem] glass p-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <p className="text-sm uppercase tracking-[0.3em] text-[var(--muted)]">Liquidity Logic Engine</p>
          <Link href="/" className="text-sm uppercase tracking-[0.1em] text-[var(--muted)] hover:text-white transition-colors">
            Dashboard
          </Link>
        </div>
      </section>

      <section className="rounded-[2rem] glass p-8">
        <h1 className="text-3xl font-semibold mb-6">Paid Bills History</h1>
        
        {loading ? (
          <p className="text-[var(--muted)]">Loading...</p>
        ) : error ? (
          <p className="text-rose-400">{error}</p>
        ) : bills.length === 0 ? (
          <p className="text-[var(--muted)]">No paid bills found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-[var(--muted)]">
                  <th className="pb-3 font-medium">Date</th>
                  <th className="pb-3 font-medium">Vendor</th>
                  <th className="pb-3 font-medium text-right">Amount</th>
                  <th className="pb-3 font-medium pl-6">Category</th>
                  <th className="pb-3 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {bills.map((bill) => (
                  <tr key={bill.id} className="transition hover:bg-white/5">
                    <td className="py-4 text-[var(--muted)]">{bill.date}</td>
                    <td className="py-4 font-medium">{bill.vendor_name}</td>
                    <td className="py-4 text-emerald-400 text-right">{inrFormatter.format(bill.amount)}</td>
                    <td className="py-4 text-[var(--muted)] pl-6">{bill.category || "—"}</td>
                    <td className="py-4 text-[var(--muted)]">{bill.reason || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
