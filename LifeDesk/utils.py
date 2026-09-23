"""
utils.py
---------
Small shared helpers: safe filenames, date formatting, and the
"Load Demo Data" generator used to populate LifeDesk for a presentation
without requiring real uploaded files.
"""

import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from models import Document, DocumentType

DOCS_DIR = Path("data/documents")


def ensure_dirs():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(original_name: str) -> str:
    """Produces a collision-free, filesystem-safe filename."""
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9_\-]+", "_", stem).strip("_") or "file"
    unique = uuid.uuid4().hex[:8]
    return f"{stem}_{unique}{suffix}"


def format_date(value: str) -> str:
    if not value:
        return "Not detected"
    try:
        d = datetime.strptime(value, "%Y-%m-%d")
        return d.strftime("%d %b %Y")
    except (ValueError, TypeError):
        return value


def format_amount(amount, currency) -> str:
    if amount is None:
        return "Not detected"
    currency = currency if currency and currency != "Not detected" else ""
    try:
        return f"{amount:,.2f} {currency}".strip()
    except (TypeError, ValueError):
        return f"{amount} {currency}".strip()


def _d(days_offset: int) -> str:
    return (datetime.today().date() + timedelta(days=days_offset)).strftime("%Y-%m-%d")


def generate_demo_documents() -> List[Document]:
    """Returns a list of realistic, fully-populated demo Document objects
    (not saved to disk — no real files back these records)."""
    demo = [
        Document(
            filename="dell_laptop_warranty_demo.pdf",
            title="Dell Laptop Warranty",
            document_type=DocumentType.WARRANTY.value,
            category=DocumentType.WARRANTY.value,
            organization="Dell Inc.",
            person_name="Not detected",
            product_name="Dell XPS 15 Laptop",
            purchase_date=_d(-350),
            expiration_date=_d(7),
            amount=32000,
            currency="EGP",
            invoice_number="DL-2026-4471",
            email="support@dell.com",
            phone="Not detected",
            keywords="warranty, valid until",
            file_path="", extracted_text="[Demo record — no source file]",
            extraction_note="Demo data", is_demo=1,
        ),
        Document(
            filename="university_certificate_demo.pdf",
            title="Bachelor of Computer Science Certificate",
            document_type=DocumentType.CERTIFICATE.value,
            category=DocumentType.CERTIFICATE.value,
            organization="Mansoura University",
            person_name="Ahmed Fathy",
            product_name="Not detected",
            issue_date=_d(-60),
            expiration_date=_d(14),
            amount=None, currency="Not detected",
            invoice_number="Not detected",
            email="registrar@mans.edu.eg",
            phone="Not detected",
            keywords="certificate, issued, university",
            file_path="", extracted_text="[Demo record — no source file]",
            extraction_note="Demo data", is_demo=1,
        ),
        Document(
            filename="internet_subscription_demo.pdf",
            title="Home Internet Subscription",
            document_type=DocumentType.SUBSCRIPTION.value,
            category=DocumentType.SUBSCRIPTION.value,
            organization="WE Telecom",
            person_name="Not detected",
            product_name="Fiber 100 Mbps Plan",
            renewal_date=_d(1),
            amount=450, currency="EGP",
            invoice_number="WE-99213",
            email="billing@te.eg",
            phone="19777",
            keywords="subscription, renewal, monthly",
            file_path="", extracted_text="[Demo record — no source file]",
            extraction_note="Demo data", is_demo=1,
        ),
        Document(
            filename="phone_invoice_demo.pdf",
            title="Phone Purchase Invoice",
            document_type=DocumentType.INVOICE.value,
            category=DocumentType.INVOICE.value,
            organization="2B Electronics",
            person_name="Not detected",
            product_name="Samsung Galaxy S25",
            purchase_date=_d(-20),
            amount=28500, currency="EGP",
            invoice_number="2B-INV-88213",
            email="sales@2b.com.eg",
            phone="16556",
            keywords="invoice, total, tax",
            file_path="", extracted_text="[Demo record — no source file]",
            extraction_note="Demo data", is_demo=1,
        ),
        Document(
            filename="online_course_certificate_demo.pdf",
            title="Data Analysis Professional Certificate",
            document_type=DocumentType.CERTIFICATE.value,
            category=DocumentType.CERTIFICATE.value,
            organization="Coursera",
            person_name="Ahmed Fathy",
            product_name="Not detected",
            issue_date=_d(-10),
            amount=None, currency="Not detected",
            invoice_number="Not detected",
            email="no-reply@coursera.org",
            phone="Not detected",
            keywords="certificate, issued, course",
            file_path="", extracted_text="[Demo record — no source file]",
            extraction_note="Demo data", is_demo=1,
        ),
        Document(
            filename="car_insurance_demo.pdf",
            title="Car Insurance Policy",
            document_type=DocumentType.INSURANCE.value,
            category=DocumentType.INSURANCE.value,
            organization="Misr Insurance",
            person_name="Ahmed Fathy",
            product_name="Comprehensive Coverage",
            purchase_date=_d(-200),
            expiration_date=_d(45),
            amount=6200, currency="EGP",
            invoice_number="MI-771029",
            email="claims@misrinsurance.com.eg",
            phone="16121",
            keywords="insurance, policy number, premium",
            file_path="", extracted_text="[Demo record — no source file]",
            extraction_note="Demo data", is_demo=1,
        ),
        Document(
            filename="expired_gym_membership_demo.pdf",
            title="Gym Membership",
            document_type=DocumentType.SUBSCRIPTION.value,
            category=DocumentType.SUBSCRIPTION.value,
            organization="FitZone Gym",
            person_name="Not detected",
            product_name="Annual Membership",
            expiration_date=_d(-15),
            amount=3600, currency="EGP",
            invoice_number="FZ-2233",
            email="info@fitzone.eg",
            phone="Not detected",
            keywords="subscription, membership",
            file_path="", extracted_text="[Demo record — no source file]",
            extraction_note="Demo data", is_demo=1,
        ),
    ]
    return demo
