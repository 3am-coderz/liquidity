# 💧 Liquidity Logic Engine

###  Cashflow Decision Engine for Small Businesses

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

### Main Challenges

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

## ⚙️ Core Features

### Feature Breakdown

  Feature           Description            Benefit
  ----------------- ---------------------- ---------------
  OCR Upload        Extract invoice data   Saves time
  Manual Entry      Add bills manually     Flexibility
  Bank Sync         Sync bank data         Real balance
  Reconciliation    Adjust balance         Accurate cash
  Solvency Engine   Pay/Delay decision     Survival
  Dashboard         Financial overview     Clarity

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

## 🧠 Solvency Engine

The solvency engine is the **core decision-making module** of the
system.

It classifies bills into priority levels:

  Bill Type       Priority   Action
  --------------- ---------- ----------
  Salaries        Critical   Pay
  Rent            Critical   Pay
  Taxes           Critical   Pay
  Loan EMI        Critical   Pay
  Vendors         Medium     Optimize
  Subscriptions   Low        Delay

### Decision Factors

The engine uses multiple factors:

  Factor           Why It Matters
  ---------------- --------------------------
  Available cash   Determines affordability
  Due date         Urgency
  Trust score      Vendor relationship
  Penalty risk     Late fee/legal risk
  Revenue impact   Business survival
  Days overdue     Priority

### Engine Output

The engine generates:

  Output       Description
  ------------ ------------------
  Pay List     Bills to pay now
  Delay List   Bills to delay
  Strategy     Explanation
  Warning      Shortfall alert

------------------------------------------------------------------------

## 🏦 Bank Reconciliation

Bank balance alone is not reliable because some payments are already
committed.

### Example

  Item                 Amount
  -------------------- ----------
  Bank Balance         ₹100,000
  Confirmed Payments   ₹30,000
  Available Cash       ₹70,000

**Formula:**

    Available Cash = Bank Balance - Pending Payments

This prevents **false financial decisions**.

------------------------------------------------------------------------

## 📄 OCR System

  Input           Output
  --------------- -------------
  Invoice Image   Payable
  Receipt         Transaction
  Screenshot      Payable
  Bill Photo      Payable

Supported formats:

  Format   Supported
  -------- -----------
  PNG      Yes
  JPG      Yes
  JPEG     Yes
  WEBP     Yes
  TIFF     Yes
  BMP      Yes

------------------------------------------------------------------------

## 🏗️ System Architecture

  Layer      Technology
  ---------- ---------------------
  Frontend   Next.js
  Backend    FastAPI
  OCR        Tesseract
  Bank API   Setu
  Engine     Optimization Engine
  Database   SQLite / PostgreSQL
  Hosting    Vercel / Render

------------------------------------------------------------------------

## 🛠️ Tech Stack

  Category   Technology
  ---------- --------------
  Language   Python
  Backend    FastAPI
  Frontend   Next.js
  OCR        Tesseract
  Database   SQLite
  API        Setu
  Styling    Tailwind CSS

------------------------------------------------------------------------

## 📁 Project Structure

    project/
    ├── backend/
    ├── frontend/
    ├── database/
    ├── docs/
    ├── README.md

  Folder     Description
  ---------- ----------------
  backend    API & Engine
  frontend   User Interface
  database   Database
  docs       Documentation

------------------------------------------------------------------------

## ⚙️ Local Setup

### Backend Setup

    cd backend
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

### Frontend Setup

    cd frontend
    npm install
    npm run dev

------------------------------------------------------------------------

## 🔌 API Overview

  Endpoint             Method   Purpose
  -------------------- -------- ------------------
  /auth/register       POST     Register
  /auth/login          POST     Login
  /upload-invoice      POST     OCR
  /run-optimizer       POST     Run engine
  /confirm-payments    POST     Confirm payments
  /connect-bank        POST     Bank sync
  /financial-summary   GET      Summary

------------------------------------------------------------------------

## 📊 Data Model

  Entity                Description
  --------------------- ------------------
  User                  Account
  Company               Business
  Payable               Bills
  BankTransaction       Transactions
  FinancialSummary      Summary
  Decision              Engine result
  PendingPaymentEvent   Pending payments

------------------------------------------------------------------------

## ⚠️ Known Limitations

  Limitation                Reason
  ------------------------- ---------------
  OCR errors                Image quality
  Mock bank data            Demo mode
  SQLite                    Local DB
  Not accounting software   Decision tool

------------------------------------------------------------------------

## 👥 Team

  Member           Role
  ---------------- ----------
  Dhanush Kathir   Frontend
  Anish Balaji     Frontend
  Ashraf           Backend
  Tejas            backend

------------------------------------------------------------------------

## 🏁 Final Note

Liquidity Logic Engine is built to solve one critical problem:

> **When you don't have enough money to pay everything, what should you
> do first?**
