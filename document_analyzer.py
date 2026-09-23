"""
document_analyzer.py
----------------------
The "intelligence" layer of LifeDesk. Turns raw extracted text into a
structured understanding of a document: its type, key dates, amounts,
contacts, and involved parties — using keyword scoring and regular
expressions rather than an external AI API, so the core product works
fully offline and deterministically.

Re-exports Document, Reminder, DocumentExtractor and DocumentRepository
so a caller can `from document_analyzer import *` and get the whole
"document intelligence" family of classes in one place, as the spec
describes (Document, DocumentAnalyzer, DocumentExtractor, Reminder,
DocumentRepository).
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

from models import Document, DocumentType, NOT_DETECTED
from document_extractor import DocumentExtractor  # noqa: F401  (re-export)
from database import DocumentRepository  # noqa: F401  (re-export)
from models import Reminder  # noqa: F401  (re-export)


# Keyword weight table used for classification
CLASSIFICATION_KEYWORDS: Dict[str, List[str]] = {
    DocumentType.WARRANTY.value: [
        "warranty", "guarantee", "valid until", "warranty period", "warranty card",
    ],
    DocumentType.INVOICE.value: [
        "invoice", "tax invoice", "bill to", "total due", "amount due", "invoice number",
        "vat", "subtotal",
    ],
    DocumentType.RECEIPT.value: [
        "receipt", "cash receipt", "payment received", "thank you for your purchase",
    ],
    DocumentType.SUBSCRIPTION.value: [
        "subscription", "renewal", "monthly plan", "auto-renew", "billing cycle", "membership",
    ],
    DocumentType.UNIVERSITY.value: [
        "university", "course", "student", "semester", "faculty", "gpa", "transcript",
        "enrollment", "academic",
    ],
    DocumentType.CERTIFICATE.value: [
        "certificate", "certification", "issued", "this is to certify", "awarded to",
    ],
    DocumentType.IDENTIFICATION.value: [
        "passport", "national id", "identification number", "date of birth", "nationality",
        "driver's license", "driving license",
    ],
    DocumentType.MEDICAL.value: [
        "diagnosis", "prescription", "patient", "physician", "clinic", "hospital", "medical report",
    ],
    DocumentType.CONTRACT.value: [
        "agreement", "contract", "terms and conditions", "party of the first part", "hereby agree",
        "signed by",
    ],
    DocumentType.PAYMENT.value: [
        "payment confirmation", "transaction id", "paid", "payment method", "card ending",
    ],
    DocumentType.INSURANCE.value: [
        "insurance", "policy number", "insured", "coverage", "premium", "claim",
    ],
}

DATE_PATTERNS = [
    r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",       # 2027-09-18 or 2027/09/18
    r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",       # 18-09-2027 or 09/18/2027
    r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b",
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})\b",
]

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

EXPIRY_CONTEXT = ["expir", "valid until", "valid till", "until", "expiry"]
RENEWAL_CONTEXT = ["renew", "renewal", "next billing", "due date"]
PURCHASE_CONTEXT = ["purchase", "purchased on", "bought", "order date"]
ISSUE_CONTEXT = ["issued", "issue date", "date issued", "certified on"]

CURRENCY_SYMBOLS = {
    "$": "USD", "€": "EUR", "£": "GBP", "egp": "EGP", "e£": "EGP",
    "usd": "USD", "eur": "EUR", "gbp": "GBP", "sar": "SAR", "aed": "AED",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{7,14}\d)")
AMOUNT_RE = re.compile(
    r"(?:(?:USD|EUR|GBP|EGP|SAR|AED|\$|€|£|E£)\s?)?"
    r"(\d{1,3}(?:[,\.]\d{3})*(?:\.\d{1,2})?)\s?"
    r"(?:USD|EUR|GBP|EGP|SAR|AED|\$|€|£|E£)?",
    re.IGNORECASE,
)
INVOICE_NUM_RE = re.compile(
    r"invoice[ \t]*(?:no\.?|number|#)[ \t]*[:\-]?[ \t]*([A-Za-z0-9\-\/]{3,20})"
    r"|invoice[ \t]*[:\-][ \t]*([A-Za-z0-9\-\/]{3,20})",
    re.IGNORECASE,
)
ORG_HINTS_RE = re.compile(r"\b([A-Z][A-Za-z&]+(?:\s[A-Z][A-Za-z&]+){0,2})\s?(Inc\.?|LLC|Ltd\.?|Corporation|Corp\.?|Company|University|Group)\b")
NAME_LINE_RE = re.compile(r"(?:name|customer|student|patient|insured)[ \t]*[:\-][ \t]*([A-Za-z][A-Za-z ]{2,39})", re.IGNORECASE)


class DocumentAnalyzer:
    """Analyzes extracted text and produces a structured understanding."""

    # --------------------------------------------------------- classify ---
    def classify_document(self, text: str) -> str:
        if not text:
            return DocumentType.OTHER.value
        lower = text.lower()
        scores = {}
        for doc_type, keywords in CLASSIFICATION_KEYWORDS.items():
            score = sum(lower.count(kw) for kw in keywords)
            if score:
                scores[doc_type] = score
        if not scores:
            return DocumentType.OTHER.value
        return max(scores, key=scores.get)

    # ------------------------------------------------------------ dates ---
    def extract_dates(self, text: str) -> Dict[str, Optional[str]]:
        """Returns a dict with purchase/issue/expiration/renewal dates
        detected via nearby keyword context, each as 'YYYY-MM-DD' or None."""
        result = {"purchase_date": None, "issue_date": None, "expiration_date": None, "renewal_date": None}
        if not text:
            return result

        found = []  # list of (position, iso_date_string)
        for pattern in DATE_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                iso = self._parse_date_match(m)
                if iso:
                    found.append((m.start(), iso))

        if not found:
            return result

        lower = text.lower()
        for pos, iso in found:
            context = lower[max(0, pos - 40):pos]
            if any(k in context for k in EXPIRY_CONTEXT) and not result["expiration_date"]:
                result["expiration_date"] = iso
            elif any(k in context for k in RENEWAL_CONTEXT) and not result["renewal_date"]:
                result["renewal_date"] = iso
            elif any(k in context for k in PURCHASE_CONTEXT) and not result["purchase_date"]:
                result["purchase_date"] = iso
            elif any(k in context for k in ISSUE_CONTEXT) and not result["issue_date"]:
                result["issue_date"] = iso

        # If no contextual expiration was found, assume the latest future
        # date in the document is the expiration (common on warranties).
        if not result["expiration_date"]:
            today = datetime.today().date()
            future = [iso for _, iso in found if self._safe_date(iso) and self._safe_date(iso) > today]
            if future:
                result["expiration_date"] = max(future)

        # If nothing else was tagged, treat the earliest date as purchase/issue
        if not result["purchase_date"] and not result["issue_date"] and found:
            earliest = min(found, key=lambda t: t[0])[1]
            if earliest != result.get("expiration_date"):
                result["issue_date"] = earliest

        return result

    def _parse_date_match(self, m: re.Match) -> Optional[str]:
        groups = m.groups()
        try:
            if groups[0] and groups[0].isdigit() and len(groups[0]) == 4:
                y, mo, d = int(groups[0]), int(groups[1]), int(groups[2])
            elif groups[2] and groups[2].isdigit() and len(groups[2]) == 4 and groups[0].isdigit():
                # ambiguous D-M-Y vs M-D-Y — default to D-M-Y (international convention)
                a, b, y = int(groups[0]), int(groups[1]), int(groups[2])
                mo, d = b, a
                if mo > 12:
                    mo, d = d, mo
            elif groups[1] and groups[1].lower()[:3] in MONTHS:
                d, mo, y = int(groups[0]), MONTHS[groups[1].lower()[:3]], int(groups[2])
            elif groups[0] and groups[0].lower()[:3] in MONTHS:
                mo, d, y = MONTHS[groups[0].lower()[:3]], int(groups[1]), int(groups[2])
            else:
                return None
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except (ValueError, TypeError, KeyError):
            return None

    @staticmethod
    def _safe_date(iso: str):
        try:
            return datetime.strptime(iso, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    # ---------------------------------------------------------- amounts ---
    def extract_amounts(self, text: str) -> Dict[str, Optional[str]]:
        if not text:
            return {"amount": None, "currency": None}
        lower = text.lower()
        currency = None
        for sym, code in CURRENCY_SYMBOLS.items():
            if sym in lower:
                currency = code
                break

        candidates = []
        for m in AMOUNT_RE.finditer(text):
            raw = m.group(1)
            if not raw:
                continue
            cleaned = raw.replace(",", "")
            try:
                val = float(cleaned)
            except ValueError:
                continue
            if val <= 0 or val > 100_000_000:
                continue
            candidates.append(val)

        amount = max(candidates) if candidates else None
        return {"amount": amount, "currency": currency}

    # ------------------------------------------------------------ email ---
    def extract_emails(self, text: str) -> Optional[str]:
        if not text:
            return None
        m = EMAIL_RE.search(text)
        return m.group(0) if m else None

    # ------------------------------------------------------------ phone ---
    def extract_phone_numbers(self, text: str) -> Optional[str]:
        if not text:
            return None
        for m in PHONE_RE.finditer(text):
            digits = re.sub(r"\D", "", m.group(1))
            if 8 <= len(digits) <= 15:
                return m.group(1).strip()
        return None

    # --------------------------------------------------------- entities ---
    def extract_entities(self, text: str) -> Dict[str, Optional[str]]:
        result = {"organization": None, "person_name": None, "invoice_number": None}
        if not text:
            return result

        org_match = ORG_HINTS_RE.search(text)
        if org_match:
            result["organization"] = f"{org_match.group(1)} {org_match.group(2)}".strip()

        name_match = NAME_LINE_RE.search(text)
        if name_match:
            result["person_name"] = name_match.group(1).strip().title()

        inv_match = INVOICE_NUM_RE.search(text)
        if inv_match:
            value = inv_match.group(1) or inv_match.group(2)
            if value:
                result["invoice_number"] = value.strip()

        return result

    # -------------------------------------------------------------- all ---
    def analyze(self, text: str, filename: str = "") -> dict:
        """Runs the full pipeline and returns a structured dict, never
        raising — missing fields are simply None / 'Not detected'."""
        text = text or ""
        doc_type = self.classify_document(text)
        dates = self.extract_dates(text)
        amounts = self.extract_amounts(text)
        entities = self.extract_entities(text)
        email = self.extract_emails(text)
        phone = self.extract_phone_numbers(text)

        title = entities.get("organization") or self._guess_title(filename, doc_type)

        # top keyword hits, for a lightweight "keywords" field
        lower = text.lower()
        hits = []
        for kws in CLASSIFICATION_KEYWORDS.values():
            for kw in kws:
                if kw in lower and kw not in hits:
                    hits.append(kw)
        keywords = ", ".join(hits[:8])

        return {
            "title": title,
            "document_type": doc_type,
            "category": doc_type,
            "organization": entities.get("organization") or NOT_DETECTED,
            "person_name": entities.get("person_name") or NOT_DETECTED,
            "product_name": self._guess_product(filename) or NOT_DETECTED,
            "purchase_date": dates.get("purchase_date"),
            "issue_date": dates.get("issue_date"),
            "expiration_date": dates.get("expiration_date"),
            "renewal_date": dates.get("renewal_date"),
            "amount": amounts.get("amount"),
            "currency": amounts.get("currency") or NOT_DETECTED,
            "invoice_number": entities.get("invoice_number") or NOT_DETECTED,
            "email": email or NOT_DETECTED,
            "phone": phone or NOT_DETECTED,
            "keywords": keywords,
        }

    @staticmethod
    def _guess_title(filename: str, doc_type: str) -> str:
        stem = filename.rsplit(".", 1)[0] if filename else ""
        stem = re.sub(r"[_\-]+", " ", stem).strip()
        if stem and not stem.isdigit():
            return stem.title()
        return doc_type

    @staticmethod
    def _guess_product(filename: str) -> Optional[str]:
        stem = filename.rsplit(".", 1)[0] if filename else ""
        stem = re.sub(r"[_\-]+", " ", stem).strip()
        return stem.title() if stem else None
