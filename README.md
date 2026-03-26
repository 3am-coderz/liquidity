# Liquidity Logic Engine

Liquidity Logic Engine is a full-stack cashflow decision system for small businesses. It combines OCR invoice ingestion, a solvency-aware payment engine, bank-data ingestion, and a dashboard that helps users decide which obligations to pay now and which to delay safely.

This project is built as a hackathon-ready product with:

- a `FastAPI` backend for OCR, bank sync, optimization, and user data
- a `Next.js` frontend for the dashboard, upload workflows, and payment decisions
- a solvency engine that separates hard constraints from soft optimization
- Setu Account Aggregator integration with sandbox/mock fallback

## Table Of Contents

- Overview
- Core Features
- Product Flow
- Architecture
- Solvency Engine
- Bank Sync And Reconciliation
- OCR And Upload Flows
- Tech Stack
- Project Structure
- Local Setup
- Environment Variables
- Running The App
- API Overview
- Demo Walkthrough
- Data Model Summary
- Known Limitations
- Troubleshooting

## Overview

The app is designed for businesses that need to preserve liquidity while handling bills, vendor trust, and operational survival. Users can:

- register with a company and initial cash balance
- sync bank data through Setu sandbox or mock data
- upload invoices through OCR
- add payable data manually
- run the solvency engine
- confirm payments
- generate vendor communication for delayed bills

The backend keeps enough structure to support both demo mode and more production-like behavior:

- uploaded invoice files are stored in the database
- bank data is stored as transactions plus a financial summary
- confirmed payments are reconciled against synced bank balances

## Core Features

### 1. OCR Invoice Ingestion

- accepts image-based invoices and screenshots
- extracts:
  - vendor name
  - amount
  - due date
  - inferred category
- assigns payment priority metadata
- supports OCR-based `money in` and `money out` handling on the upload page

### 2. Manual Payable Entry

- create outgoing payables without OCR
- set:
  - vendor name
  - amount
  - due date
  - category
  - trust score

### 3. Solvency Engine

- evaluates company state before optimization
- separates:
  - hard constraints
  - soft constraints
- uses normalized scoring with hard constraints always above soft constraints
- produces:
  - bills to pay
  - bills to delay
  - strategy explanation
  - critical shortfall warnings

### 4. Setu Bank Sync

- initiates Setu consent
- handles consent/session webhook flow
- fetches or mocks bank data
- stores transactions and financial summary
- feeds the engine from bank-derived balance and expenses instead of only manual cash

### 5. Balance Reconciliation

- synced bank balance remains the external source of truth
- confirmed app payments are tracked separately as pending outflows
- dashboard and engine use:
  - `reconciled balance = bank balance - unsettled confirmed payments`
- repeated syncs no longer unrealistically “reset” the balance

### 6. Trust Score Editing

- trust score can be overridden on bill creation
- trust score can be edited later on the dashboard
- delayed non-hard bills can lose trust after engine runs where hard constraints consume liquidity

## Product Flow

### Bill Outflow Flow

1. User syncs bank data.
2. User uploads an invoice or creates a manual payable.
3. OCR/manual flow stores payable data.
4. User runs the engine.
5. Engine recommends pay vs delay.
6. User confirms selected payments.
7. Confirmed payments move into pending-payment reconciliation.

### OCR Money-In Flow

1. User opens upload page.
2. User selects `Money in`.
3. User uploads a receipt or income image.
4. OCR extracts the amount and counterparty.
5. Backend stores a financial transaction.
6. Financial summary updates automatically.

### Bank Sync Flow

1. User clicks `Sync bank`.
2. Backend starts Setu consent.
3. In mock mode:
   - consent auto-completes
   - session is created
   - mock FI data is fetched
4. Transactions and summary are stored.
5. Dashboard and engine use the reconciled balance.

## Architecture

### Frontend

- framework: `Next.js`
- location: `frontend/`
- main responsibilities:
  - login/register
  - dashboard
  - upload flows
  - optimizer interactions
  - displaying OCR and engine outputs

### Backend

- framework: `FastAPI`
- location: `backend/`
- main responsibilities:
  - auth
  - OCR parsing
  - payables
  - Setu integration
  - financial summaries
  - solvency engine execution
  - payment confirmation

### Persistence

- default DB: SQLite
- PostgreSQL-ready through SQLAlchemy
- uploaded invoice binaries stored in database

## Solvency Engine

The engine itself lives in:

- [backend/app/services/optimizer.py](/Users/Kathir/Downloads/project/backend/app/services/optimizer.py)

The engine is intentionally separated from OCR and Setu ingestion.

### Current Logic

- hard existential constraints remain top priority
- hard legal constraints come next
- facilities and rent escalate based on overdue duration
- soft bills are ranked by solvency value density
- if hard constraints cannot all fit:
  - the engine marks a critical shortfall
  - delayed hard bills get affordability warnings

### Inputs Used By The Engine

- reconciled available cash
- monthly expense
- unpaid payables
- payable attributes such as:
  - trust score
  - penalty risk
  - criticality
  - revenue impact
  - vendor aggression
  - days overdue

### Important Rule

The engine does **not** directly own bank syncing or OCR parsing. Those are upstream data sources. This keeps optimization logic isolated and easier to evolve.

## Bank Sync And Reconciliation

Bank sync and summaries are handled through:

- [backend/app/services/setu_consent_service.py](/Users/Kathir/Downloads/project/backend/app/services/setu_consent_service.py)
- [backend/app/services/setu_webhook_service.py](/Users/Kathir/Downloads/project/backend/app/services/setu_webhook_service.py)
- [backend/app/services/setu_data_service.py](/Users/Kathir/Downloads/project/backend/app/services/setu_data_service.py)
- [backend/app/services/financial_summary_service.py](/Users/Kathir/Downloads/project/backend/app/services/financial_summary_service.py)

### Why Reconciliation Exists

If the app only stored one balance value, every fresh bank sync would overwrite local confirmed payments. To avoid that:

- bank sync updates the raw synced bank balance
- confirmed payments create `PendingPaymentEvent` records
- the app computes a reconciled balance for display and optimization

### Reconciled Balance Formula

`reconciled balance = synced bank balance - pending confirmed payments`

This makes demo behavior much more realistic while still preserving the bank feed as a separate source.

## OCR And Upload Flows

OCR service lives in:

- [backend/app/services/ocr.py](/Users/Kathir/Downloads/project/backend/app/services/ocr.py)

### Supported File Types

- `png`
- `jpg`
- `jpeg`
- `webp`
- `tiff`
- `bmp`

### OCR Upload Modes

On the upload page:

- `Money out`
  - creates a payable
- `Money in`
  - creates a financial transaction from OCR output

### Manual Entry

Manual entry is payable-only and is used for outgoing bills where OCR is unnecessary.

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Uvicorn
- Tesseract OCR via `pytesseract`
- `httpx` for Setu HTTP integration

### Frontend

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS

### Storage

- SQLite by default
- PostgreSQL supported

## Project Structure

```text
project/
├─ backend/
│  ├─ app/
│  │  ├─ services/
│  │  │  ├─ cse.py
│  │  │  ├─ financial_summary_service.py
│  │  │  ├─ ocr.py
│  │  │  ├─ optimizer.py
│  │  │  ├─ priorities.py
│  │  │  ├─ setu_consent_service.py
│  │  │  ├─ setu_data_service.py
│  │  │  └─ setu_webhook_service.py
│  │  ├─ auth.py
│  │  ├─ config.py
│  │  ├─ db.py
│  │  ├─ main.py
│  │  ├─ models.py
│  │  └─ schemas.py
│  ├─ .env.example
│  ├─ requirements.txt
│  └─ lle.db
├─ frontend/
│  ├─ app/
│  ├─ components/
│  ├─ .env.local.example
│  └─ package.json
├─ start-backend.cmd
├─ start-frontend.cmd
└─ README.md
```

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Tesseract OCR installed locally for real OCR uploads

### Windows Tesseract Example

Set this in `backend/.env` if Tesseract is not on `PATH`:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Backend Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

### Frontend Setup

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

### Quick Start With Included Scripts

From the repo root:

```powershell
start-backend.cmd
start-frontend.cmd
```

## Environment Variables

Backend example file:

- [backend/.env.example](/Users/Kathir/Downloads/project/backend/.env.example)

### Core

```env
SECRET_KEY=hackathon-secret-key
DATABASE_URL=sqlite:///./lle.db
FRONTEND_ORIGIN=http://localhost:3000
TESSERACT_CMD=
```

### Setu

```env
SETU_BASE_URL=https://aa-sandbox.setu.co
SETU_CLIENT_ID=
SETU_CLIENT_SECRET=
SETU_PRODUCT_INSTANCE_ID=
SETU_REDIRECT_URL=http://localhost:3000/setu/consent/callback
SETU_MOCK_ENABLED=true
```

### Notes

- if Setu credentials are missing and `SETU_MOCK_ENABLED=true`, the app uses mock bank data
- PostgreSQL can be used via:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/liquidity
```

## Running The App

After starting both services:

- frontend: [http://localhost:3000](http://localhost:3000)
- backend docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API Overview

This is not a full API reference, but these are the important endpoints.

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/theme`

### Dashboard And Company

- `GET /dashboard-state`
- `GET /company-status`
- `DELETE /user-data`

### OCR And Payables

- `POST /upload-invoice`
- `PATCH /payables/{bill_id}/trust-score`
- `GET /payables/{bill_id}/invoice`

### Optimization

- `POST /run-optimizer`
- `POST /confirm-payments`
- `POST /generate-email`

### Bank And Financial Data

- `POST /connect-bank`
- `POST /setu/consent/initiate`
- `POST /setu/webhook`
- `GET /financial-summary/{user_id}`
- `POST /financial-transactions/manual`

## Demo Walkthrough

### Standard Outflow Demo

1. Register a user.
2. Click `Sync bank`.
3. Upload an outgoing invoice.
4. Run the engine.
5. Confirm a payment.
6. Sync bank again and observe that the reconciled balance stays stable.

### OCR Money-In Demo

1. Open `/upload-data`.
2. Choose `Money in` under OCR upload.
3. Upload a receipt or income image.
4. Review the updated balance and summary.

### Manual Bill Demo

1. Open `/upload-data`.
2. Use manual payable entry.
3. Set trust score if needed.
4. Save bill and run the engine from the dashboard.

## Data Model Summary

Key persisted objects include:

- `User`
- `Company`
- `Account`
- `Payable`
- `Decision`
- `SetuConsent`
- `SetuDataSession`
- `BankTransaction`
- `FinancialSummary`
- `PendingPaymentEvent`

## Known Limitations

- OCR is only as good as the input image quality
- Setu integration defaults to mock mode unless sandbox credentials are configured
- mock bank data is deterministic, so it is best suited for demo and local development
- the frontend currently focuses on the main dashboard and upload workflow, not full banking-history views
- some legacy fields like runway and coverage still exist in the backend model even if they are hidden in parts of the UI

## Troubleshooting

### OCR Fails

Check:

- Tesseract is installed
- `TESSERACT_CMD` is correct
- the uploaded file is a supported image type

### Localhost Refused To Connect

Check:

- backend is running on `127.0.0.1:8000`
- frontend is running on `localhost:3000`

### Bank Sync Looks Wrong

Remember:

- raw bank balance and reconciled balance are different
- confirmed payments stay as pending outflows until reconciled
- repeated sync should not erase pending confirmed payments anymore

### Database Looks Corrupted Or Stale

For a clean local reset:

1. stop backend
2. delete `backend/lle.db`
3. restart backend

Or use the in-app `Delete my data` action for a single user.

## Final Notes

This project is intentionally modular:

- OCR ingestion can evolve independently
- Setu sync can be swapped from mock to sandbox or real credentials
- the optimizer remains isolated from financial-ingestion concerns
- reconciliation keeps synced bank truth and app-confirmed outflows separate

That separation is what keeps the project workable as both a demo and a serious prototype.
