import re
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path

import pytesseract
from dateutil import parser as date_parser
from PIL import Image
from fastapi import HTTPException, UploadFile

from ..config import settings
from .priorities import infer_priority


SUPPORTED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/tiff": ".tiff",
    "application/octet-stream": "",
}


@dataclass
class OCRExtraction:
    text: str | None
    vendor_name: str | None
    amount: float | None
    due_date: date | None
    category: str | None
    priority_label: str
    priority_reason: str
    confidence_notes: list[str]
    file_bytes: bytes
    content_type: str
    source_file_name: str


def configure_tesseract() -> None:
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def verify_tesseract_available() -> None:
    configure_tesseract()
    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:  # pragma: no cover - depends on local binary
        raise HTTPException(
            status_code=500,
            detail=(
                "Tesseract OCR is not available. Install Tesseract and optionally set "
                "TESSERACT_CMD in backend/.env to the executable path."
            ),
        ) from exc


def _infer_category(text: str) -> str:
    lowered = text.lower()
    category_signals = {
        "Payroll": ["payroll", "salary", "wages", "employee payout", "staff payment"],
        "Rent": ["rent", "landlord", "lease", "premises", "shop rent"],
        "Legal": ["legal", "law", "attorney", "advocate", "compliance notice"],
        "Inventory": ["beans", "inventory", "supplier", "stock", "raw material", "wholesale", "procurement"],
        "Utilities": ["electric", "electricity", "water", "utility", "internet", "broadband", "gas bill"],
        "Tax": ["gst", "tax invoice", "cgst", "sgst", "igst", "tds"],
    }
    for category, signals in category_signals.items():
        if any(signal in lowered for signal in signals):
            return category
    if "payroll" in lowered or "salary" in lowered:
        return "Payroll"
    return "Operations"


def _normalize_ocr_text(text: str) -> str:
    replacements = {
        "₹": "Rs ",
        "rs.": "Rs ",
        "rs ": "Rs ",
        "inr ": "INR ",
        "|": "I",
        "—": "-",
    }
    normalized = text
    for source, target in replacements.items():
        normalized = re.sub(re.escape(source), target, normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized


def _extract_amount(text: str) -> float | None:
    preferred_patterns = [
        r"(?:grand total|invoice value|total amount|amount payable|net amount|balance due)\s*[:\-]?\s*(?:Rs|INR)?\.?\s*([0-9][0-9,]*(?:\.[0-9]{2})?)",
        r"(?:Rs|INR)\.?\s*([0-9][0-9,]*(?:\.[0-9]{2})?)",
    ]
    for pattern in preferred_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            values = [float(match.replace(",", "")) for match in matches]
            return round(max(values), 2)

    generic_matches = re.findall(r"\b([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{2})?|[0-9]{3,}(?:\.[0-9]{2})?)\b", text)
    if generic_matches:
        values = []
        for match in generic_matches:
            parsed = float(match.replace(",", ""))
            if parsed >= 100:
                values.append(parsed)
        if values:
            return round(max(values), 2)
    return None


def _extract_due_date(text: str) -> date | None:
    patterns = [
        r"(?:due date|payment due|bill due|due on)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
        r"(?:due date|payment due|bill due|due on)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:invoice date|bill date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:due date|payment due|bill due|due on)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return date_parser.parse(match.group(1), fuzzy=True, dayfirst=True).date()
            except (ValueError, OverflowError):
                continue

    date_matches = re.findall(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
    for item in date_matches:
        try:
            return date_parser.parse(item, fuzzy=True, dayfirst=True).date()
        except (ValueError, OverflowError):
            continue
    return None


def _looks_like_vendor_line(line: str) -> bool:
    lowered = line.lower()
    blocked_tokens = [
        "invoice",
        "bill to",
        "ship to",
        "due date",
        "amount",
        "total",
        "qty",
        "quantity",
        "rate",
        "gst",
        "cgst",
        "sgst",
        "igst",
        "hsn",
        "sac",
        "tax",
        "phone",
        "mobile",
        "email",
        "www.",
        "www",
        "address",
        "pin code",
    ]
    if any(token in lowered for token in blocked_tokens):
        return False
    if re.search(r"\d{6}", line):
        return False
    return len(line.strip()) > 3


def _extract_vendor_name(text: str, fallback_name: str) -> str | None:
    lines = [line.strip(" -:|") for line in text.splitlines() if line.strip()]
    for line in lines[:10]:
        if _looks_like_vendor_line(line):
            return line[:255]

    match = re.search(r"(?:from|supplier|vendor)\s*[:\-]?\s*([A-Za-z0-9 &.,'-]{4,255})", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()[:255]

    stem = Path(fallback_name).stem.replace("_", " ").replace("-", " ").strip()
    return stem.title() if stem else None


def _extract_invoice_number(text: str) -> str | None:
    patterns = [
        r"(?:invoice no|invoice number|inv no|bill no)\s*[:\-]?\s*([A-Za-z0-9/-]+)",
        r"(?:receipt no|voucher no)\s*[:\-]?\s*([A-Za-z0-9/-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_gstin(text: str) -> str | None:
    match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d[A-Z0-9]{1}Z[A-Z0-9]{1}\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return None


def _build_confidence_notes(text: str, amount: float | None, due_date: date | None, invoice_number: str | None, gstin: str | None) -> list[str]:
    notes: list[str] = []
    lowered = text.lower()
    if "rs" in lowered or "inr" in lowered:
        notes.append("Detected rupee-denominated invoice text.")
    if "gst" in lowered:
        notes.append("GST markers detected in the invoice.")
    if amount is None:
        notes.append("Could not confidently detect an invoice amount.")
    if due_date is None:
        notes.append("Could not confidently detect a due date.")
    if invoice_number is None:
        notes.append("Invoice number was not confidently detected.")
    if gstin:
        notes.append(f"GSTIN detected: {gstin}.")
    if not text:
        notes.append("OCR produced very little text. Try a clearer image.")
    return notes


def _extract_amount_candidates(text: str) -> float | None:
    currency_matches = re.findall(r"(?:Rs|INR)\.?\s*([0-9][0-9,]*(?:\.[0-9]{2})?)", text, flags=re.IGNORECASE)
    if currency_matches:
        values = [float(match.replace(",", "")) for match in currency_matches]
        return round(max(values), 2)
    return None


def _read_upload_bytes(file: UploadFile) -> tuple[bytes, str]:
    suffix = Path(file.filename or "").suffix.lower()
    if not suffix:
        suffix = SUPPORTED_IMAGE_TYPES.get(file.content_type or "", "")
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp", ""}:
        raise HTTPException(status_code=400, detail="Only image invoice uploads are supported for OCR right now.")

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded invoice file is empty.")

    content_type = file.content_type or "application/octet-stream"
    return file_bytes, content_type


def extract_invoice_data(file: UploadFile) -> OCRExtraction:
    verify_tesseract_available()
    file_bytes, content_type = _read_upload_bytes(file)

    try:
        image = Image.open(BytesIO(file_bytes))
        extracted_text = pytesseract.image_to_string(image, config="--oem 3 --psm 6")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to read the uploaded file as an image invoice.") from exc

    extracted_text = _normalize_ocr_text(extracted_text).strip()
    vendor_name = _extract_vendor_name(extracted_text, file.filename or "uploaded-invoice")
    amount = _extract_amount(extracted_text) or _extract_amount_candidates(extracted_text)
    due_date = _extract_due_date(extracted_text)
    category = _infer_category(extracted_text)
    priority_label, priority_reason = infer_priority(category, due_date, amount or 0, extracted_text)
    invoice_number = _extract_invoice_number(extracted_text)
    gstin = _extract_gstin(extracted_text)
    notes = _build_confidence_notes(extracted_text, amount, due_date, invoice_number, gstin)

    return OCRExtraction(
        text=extracted_text or None,
        vendor_name=vendor_name,
        amount=amount,
        due_date=due_date,
        category=category,
        priority_label=priority_label,
        priority_reason=priority_reason,
        confidence_notes=notes,
        file_bytes=file_bytes,
        content_type=content_type,
        source_file_name=file.filename or "uploaded-invoice",
    )
