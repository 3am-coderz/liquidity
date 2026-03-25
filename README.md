
# Liquidity Logic Engine Hackathon MVP

This workspace contains a solo-hackathon MVP split into:

- `backend/`: FastAPI API with JWT auth, clean user onboarding, Company Segregation Engine logic, payment strategy selection, OCR-driven invoice priority, and email flows.
- `frontend/`: Next.js dashboard with dark mode, demo login, company health indicator, optimizer output, and negotiation draft UI.

## Backend

1. Create a virtual environment.
2. Install dependencies with `pip install -r backend/requirements.txt`.
3. Copy `backend/.env.example` to `backend/.env` if you want custom settings.
4. Optional: point `DATABASE_URL` at PostgreSQL with a URL like `postgresql+psycopg://postgres:postgres@localhost:5432/liquidity`.
5. Run `uvicorn app.main:app --reload` from `backend/`.

For real invoice OCR uploads, install the Tesseract binary on your machine:

- Windows: install Tesseract OCR and set `TESSERACT_CMD` in `backend/.env` if it is not already on your `PATH`.
- Example: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

New users register with their own opening cash balance. No random financial records are created for them.

## Frontend

1. Install dependencies with `npm install` inside `frontend/`.
2. Copy `frontend/.env.local.example` to `frontend/.env.local`.
3. Run `npm run dev` from `frontend/`.

The frontend expects the backend at `http://127.0.0.1:8000` by default.

## Demo Path

1. Register with company name and opening cash balance.
2. Upload a real invoice image.
3. Let OCR assign category and payment priority.
4. Run the engine.
5. Generate email.

## OCR Upload Notes

- The real upload flow currently supports image invoices: `png`, `jpg`, `jpeg`, `webp`, `tiff`, and `bmp`.
- Uploaded invoice files are stored directly in the database as binary data instead of being written to `backend/uploads/`.
- If Tesseract is missing, the API returns a clear error telling you to install it or set `TESSERACT_CMD`.

## Resetting Old Demo Data

If you previously ran an older version of this project with seeded demo data, either:

- use the in-app `Delete my data` action after logging in, or
- stop the backend and delete `backend/lle.db`, then start the backend again for a clean database.

