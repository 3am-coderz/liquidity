# 💧 Liquidity Logic Engine

### AI-Powered Cashflow Decision Engine for Small Businesses

> *"Don't just track your cash. Decide with it."*

![Phase](https://img.shields.io/badge/Phase-Development-orange)
![Project](https://img.shields.io/badge/Project-Liquidity%20Logic%20Engine-blue)
![Status](https://img.shields.io/badge/Status-Active-green)

------------------------------------------------------------------------

## 📌 Overview

Liquidity Logic Engine is a **cashflow decision system** designed for
small businesses that struggle with liquidity management.\
Instead of just tracking income and expenses, the system **decides which
bills should be paid now and which can be delayed safely**.

It combines: - OCR invoice processing - Bank transaction syncing - Cash
reconciliation - A solvency decision engine - A financial dashboard

------------------------------------------------------------------------

## ❗ The Problem

Small businesses often fail not because they are unprofitable, but
because they **run out of cash at the wrong time**.

  Challenge           Result
  ------------------- --------------------------
  Too many bills      Confusion on what to pay
  Limited cash        Poor prioritization
  Vendor pressure     Trust issues
  Legal penalties     Late payments
  No decision tools   Financial stress

Most software shows **what you spent**.\
Liquidity Logic Engine shows **what you should do next**.

------------------------------------------------------------------------

## 💡 The Solution

Liquidity Logic Engine acts like a **financial decision assistant**.

  Module            Function
  ----------------- --------------------------------
  OCR               Reads invoices and receipts
  Bank Sync         Fetches bank transactions
  Reconciliation    Calculates real available cash
  Solvency Engine   Decides pay vs delay
  Dashboard         Shows financial health

------------------------------------------------------------------------

## 🔄 How The System Works

    Upload Invoice / Add Bill
                ↓
            OCR Processing
                ↓
            Store Payable
                ↓
            Sync Bank Data
                ↓
        Calculate Available Cash
                ↓
            Run Solvency Engine
                ↓
        Pay / Delay Recommendation
                ↓
            User Confirms
                ↓
            Balance Reconciled
                ↓
            Dashboard Updated

------------------------------------------------------------------------

## 🧠 Solvency Engine (Core Logic)

The Solvency Engine is the **decision-making brain** of the Liquidity
Logic Engine.\
It determines which bills should be paid using **Hard Constraints + Soft
Constraints + Knapsack Optimization**.

------------------------------------------------------------------------

### 1. Hard vs Soft Constraints

  -----------------------------------------------------------------------
  Constraint Type                      Examples              Rule
  ------------------------------------ --------------------- ------------
  Hard Constraints                     Salaries, Rent,       Must be paid
                                       Taxes, Loan EMI       

  Soft Constraints                     Vendors,              Can be
                                       Subscriptions,        delayed
                                       Utilities             

  Strategic Bills                      Revenue generating    High
                                       expenses              priority

  Optional Bills                       Low impact expenses   Delay first
  -----------------------------------------------------------------------

**Rule:** Hard constraints are always satisfied first before
optimization begins.

------------------------------------------------------------------------

### 2. Score Decider System

Each bill is given a **Solvency Score** based on multiple business risk
factors.

  Factor              Description               Impact
  ------------------- ------------------------- --------
  Due Date            Urgency                   High
  Trust Score         Vendor relationship       Medium
  Penalty Risk        Late fee/legal risk       High
  Revenue Impact      Affects business income   High
  Vendor Aggression   Supplier strictness       Medium
  Days Overdue        Delay severity            High

### Score Formula (Concept)

    Bill Score = 
    (Revenue Impact × Weight) +
    (Penalty Risk × Weight) +
    (Trust Score × Weight) +
    (Urgency × Weight) +
    (Vendor Aggression × Weight)

Bills with higher score = higher priority.

------------------------------------------------------------------------

### 3. Knapsack Optimization

After hard constraints are paid, the remaining money is allocated using
a **Knapsack Optimization Algorithm**.

**Problem Type:**\
This is similar to the **0/1 Knapsack Problem**:

  Knapsack Term   Our System
  --------------- ----------------
  Weight          Bill Amount
  Value           Bill Score
  Capacity        Available Cash
  Items           Bills

**Goal:** Maximize total score while staying within available cash.

So the system: - Selects the combination of bills - That maximizes
business survival value - Without exceeding available cash

This ensures **optimal use of limited money**.

------------------------------------------------------------------------

### 4. Engine Output

  Output              Description
  ------------------- -----------------------------------------
  Pay List            Bills to pay now
  Delay List          Bills to delay
  Strategy            Explanation
  Shortfall Warning   If cash not enough for hard constraints

------------------------------------------------------------------------

## 🏦 Bank Reconciliation

  Item                 Amount
  -------------------- ----------
  Bank Balance         ₹100,000
  Confirmed Payments   ₹30,000
  Available Cash       ₹70,000

**Formula:**

    Available Cash = Bank Balance - Pending Payments

------------------------------------------------------------------------

## 📄 OCR System

  Input           Output
  --------------- -------------
  Invoice Image   Payable
  Receipt         Transaction
  Screenshot      Payable
  Bill Photo      Payable

Supported formats: PNG, JPG, JPEG, WEBP, TIFF, BMP

------------------------------------------------------------------------

## 🏗️ System Architecture

  Layer      Technology
  ---------- -----------------------
  Frontend   Next.js
  Backend    FastAPI
  OCR        Tesseract
  Bank API   Setu
  Engine     Knapsack Optimization
  Database   SQLite / PostgreSQL
  Hosting    Vercel / Render

------------------------------------------------------------------------

## 🛠️ Tech Stack

  Category       Technology
  -------------- -------------------
  Language       Python
  Backend        FastAPI
  Frontend       Next.js
  OCR            Tesseract
  Optimization   OR-Tools Knapsack
  Database       SQLite
  API            Setu
  Styling        Tailwind CSS

------------------------------------------------------------------------

## 👥 Team

  Member           Role
  ---------------- ----------
  Dhanush Kathir   Frontend
  Yuvashankar      Frontend
  Ashraf           Backend
  Srinath          ML

------------------------------------------------------------------------

## 🏁 Final Note

> When you don't have enough money to pay everything, the system decides
> the best way to survive.
