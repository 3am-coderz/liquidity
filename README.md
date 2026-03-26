# 💧 Liquidity Logic Engine

### Solvency & Cashflow Decision Engine for Small Businesses

> *"Don't just track your cash. Decide with it."*

![Phase](https://img.shields.io/badge/Phase-Development-orange)
![Project](https://img.shields.io/badge/Project-Liquidity%20Logic%20Engine-blue)
![Status](https://img.shields.io/badge/Status-Active-green)

------------------------------------------------------------------------

## 📌 Overview

Liquidity Logic Engine is a **solvency-aware cashflow decision system**
that helps businesses decide:

-   Which bills to pay now
-   Which bills to delay safely
-   How to survive cash shortages
-   How to maximize financial runway

This system combines: - OCR invoice processing - Bank transaction
syncing - Cash reconciliation - Solvency scoring - Knapsack
optimization - Financial dashboard

> **Liquidity Logic Engine is not a simple optimizer --- it is a
> solvency-aware constrained optimization system designed to maximize
> business survival runway, not just minimize costs.**

------------------------------------------------------------------------

## ❗ The Problem

Small businesses don't fail because they are unprofitable.\
They fail because they **run out of cash at the wrong time**.

  Challenge           Result
  ------------------- --------------------
  Too many bills      Confusion
  Limited cash        Poor decisions
  Vendor pressure     Trust loss
  Legal penalties     Fines
  No prioritization   Cash mismanagement

Most tools track money.\
**This system decides what to do when money is not enough.**

------------------------------------------------------------------------

## 💡 The Solution

  Module            Function
  ----------------- ---------------------------
  OCR               Reads invoices
  Bank Sync         Fetches transactions
  Reconciliation    Calculates available cash
  Solvency Engine   Decides pay vs delay
  Dashboard         Shows financial health

------------------------------------------------------------------------

## 🔄 System Workflow

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

# 🧠 Solvency Engine (Core Innovation)

The Solvency Engine decides payments using:

-   Hard Constraints
-   Soft Constraints
-   Solvency Score
-   Knapsack Optimization
-   Runway-Based Strategy

------------------------------------------------------------------------

## 1. Constraint Classification

  ----------------------------------------------------------------------------
  Constraint Type       Description      Examples        Engine Behavior
  --------------------- ---------------- --------------- ---------------------
  Hard Existential      Business stops   Inventory,      Must pay
                        if unpaid        Critical        
                                         suppliers       

  Hard Legal            Legal action     Salaries,       Must pay
                        risk             Taxes, Rent     

  Soft Optimization     Can delay        Vendors,        Optimize
                                         Subscriptions   
  ----------------------------------------------------------------------------

------------------------------------------------------------------------

## 2. Quasi-Hard Constraints (Rent / Facilities)

  Days Overdue   Constraint Type
  -------------- ----------------------
  \< 30 days     Soft (High Priority)
  30--60 days    Escalating Risk
  ≥ 60 days      Hard Legal

This prevents eviction risk while still allowing optimization
flexibility.

------------------------------------------------------------------------

## 3. Solvency Score System

Each bill gets a **Solvency Score**.

  Factor              Impact
  ------------------- --------
  Revenue Impact      High
  Penalty Risk        High
  Trust Score         Medium
  Vendor Aggression   Medium
  Days Overdue        High
  Criticality         High

### Concept Formula

    Solvency Score =
    Revenue Impact +
    Penalty Risk +
    Trust Score +
    Urgency +
    Vendor Aggression

Higher score = higher priority.

------------------------------------------------------------------------

## 4. Hard Constraint Optimization

Hard constraints are sorted by:

1.  Survival Impact (descending)
2.  Bill Amount (ascending)

This ensures the system **saves the business first**, not just pays the
biggest bill.

If hard constraints cannot be paid → system flags:

**Critical Insolvency Risk**

------------------------------------------------------------------------

## 5. Soft Constraint Optimization (Knapsack Problem)

This is modeled as a **0/1 Knapsack Problem**:

  Knapsack Term   Our System
  --------------- ----------------
  Capacity        Available Cash
  Weight          Bill Amount
  Value           Solvency Score
  Items           Bills

### Priority Density Formula

    Priority Density = Score / Amount

The system selects bills that give **maximum survival value per rupee**.

------------------------------------------------------------------------

## 6. Runway-Based Strategy Modes

  Runway Days   Mode           Strategy
  ------------- -------------- ---------------------------
  \< 7 days     Crisis Mode    Revenue + penalties first
  7--30 days    Caution Mode   Balanced
  \> 30 days    Stable Mode    Trust + optimization

------------------------------------------------------------------------

## 7. Engine Decision Flow

    Step 1 — Calculate Available Cash
    Step 2 — Classify Bills (Hard / Soft)
    Step 3 — Sort Hard Bills by Survival Impact
    Step 4 — Pay Hard Bills First
    Step 5 — If Hard Bills can't be paid → Critical Warning
    Step 6 — Use Knapsack on Soft Bills
    Step 7 — Generate Pay List and Delay List
    Step 8 — Calculate Remaining Runway
    Step 9 — Generate Strategy Explanation

------------------------------------------------------------------------

## 🏦 Bank Reconciliation

  Item               Amount
  ------------------ ----------
  Bank Balance       ₹100,000
  Pending Payments   ₹30,000
  Available Cash     ₹70,000

**Formula:**

    Available Cash = Bank Balance - Pending Payments

------------------------------------------------------------------------

## 📄 OCR System

  Input        Output
  ------------ -------------
  Invoice      Payable
  Receipt      Transaction
  Screenshot   Payable

Supported formats: PNG, JPG, JPEG, WEBP, TIFF, BMP

------------------------------------------------------------------------

## 🏗️ System Architecture

  Layer          Technology
  -------------- ---------------------
  Frontend       Next.js
  Backend        FastAPI
  OCR            Tesseract
  Bank API       Setu
  Optimization   OR-Tools Knapsack
  Database       SQLite / PostgreSQL
  Hosting        Vercel / Render

------------------------------------------------------------------------

## 🛠️ Tech Stack

  Category       Technology
  -------------- --------------
  Language       Python
  Backend        FastAPI
  Frontend       Next.js
  OCR            Tesseract
  Optimization   OR-Tools
  Database       SQLite
  API            Setu
  Styling        Tailwind CSS

------------------------------------------------------------------------

## 📁 Project Structure

    project/
    ├── backend/
    ├── frontend/
    ├── database/
    ├── docs/
    ├── README.md

------------------------------------------------------------------------

## ⚙️ Local Setup

### Backend

    cd backend
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

### Frontend

    cd frontend
    npm install
    npm run dev

------------------------------------------------------------------------

## 👥 Team

  Member           Role
  ---------------- ----------
  Dhanush Kathir   Frontend
  Anish Balaji     Frontend
  Ashraf           Backend
  Tejas            ML

------------------------------------------------------------------------

## 🏁 Final Note

> When cash is limited, survival depends on paying the right bill at the
> right time.\
> Liquidity Logic Engine makes that decision.
