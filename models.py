"""
models.py
---------
Core data models for LifeDesk.

Demonstrates OOP concepts:
- dataclasses for clean, encapsulated data records
- Enums for controlled vocabularies (type safety instead of raw strings)
- Simple computed properties (encapsulation of derived logic)
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class DocumentType(str, Enum):
    WARRANTY = "Warranty"
    INVOICE = "Invoice"
    RECEIPT = "Receipt"
    SUBSCRIPTION = "Subscription"
    UNIVERSITY = "University Document"
    CERTIFICATE = "Certificate"
    IDENTIFICATION = "Identification Document"
    MEDICAL = "Medical Document"
    CONTRACT = "Contract"
    PAYMENT = "Payment Document"
    INSURANCE = "Insurance"
    OTHER = "Other"


# Icon shown per document type in the UI
TYPE_ICONS = {
    DocumentType.WARRANTY: "🛡️",
    DocumentType.INVOICE: "🧾",
    DocumentType.RECEIPT: "🧻",
    DocumentType.SUBSCRIPTION: "🔁",
    DocumentType.UNIVERSITY: "🎓",
    DocumentType.CERTIFICATE: "📜",
    DocumentType.IDENTIFICATION: "🪪",
    DocumentType.MEDICAL: "🩺",
    DocumentType.CONTRACT: "📑",
    DocumentType.PAYMENT: "💳",
    DocumentType.INSURANCE: "🏥",
    DocumentType.OTHER: "📄",
}


class DocumentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRING_SOON = "EXPIRING SOON"
    EXPIRED = "EXPIRED"
    NO_DATE = "NO DATE"


STATUS_COLORS = {
    DocumentStatus.ACTIVE: "#1E9E5A",
    DocumentStatus.EXPIRING_SOON: "#E07B0F",
    DocumentStatus.EXPIRED: "#D6423C",
    DocumentStatus.NO_DATE: "#6B7280",
}

STATUS_EMOJI = {
    DocumentStatus.ACTIVE: "🟢",
    DocumentStatus.EXPIRING_SOON: "🟠",
    DocumentStatus.EXPIRED: "🔴",
    DocumentStatus.NO_DATE: "⚪",
}


class Priority(str, Enum):
    URGENT = "Urgent"
    SOON = "Soon"
    NORMAL = "Normal"


PRIORITY_EMOJI = {
    Priority.URGENT: "🔴",
    Priority.SOON: "🟠",
    Priority.NORMAL: "🟢",
}

NOT_DETECTED = "Not detected"


@dataclass
class Document:
    """Represents a single stored document / structured record."""

    id: Optional[int] = None
    filename: str = ""
    title: str = NOT_DETECTED
    document_type: str = DocumentType.OTHER.value
    category: str = DocumentType.OTHER.value
    organization: str = NOT_DETECTED
    person_name: str = NOT_DETECTED
    product_name: str = NOT_DETECTED
    purchase_date: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    renewal_date: Optional[str] = None
    amount: Optional[float] = None
    currency: str = NOT_DETECTED
    invoice_number: str = NOT_DETECTED
    email: str = NOT_DETECTED
    phone: str = NOT_DETECTED
    keywords: str = ""
    file_path: str = ""
    extracted_text: str = ""
    extraction_note: str = ""
    is_demo: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def relevant_date(self) -> Optional[str]:
        """The single most relevant forward-looking date for status/reminders."""
        return self.expiration_date or self.renewal_date

    def compute_status(self) -> DocumentStatus:
        d = self.relevant_date()
        if not d:
            return DocumentStatus.NO_DATE
        try:
            target = datetime.strptime(d, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return DocumentStatus.NO_DATE
        delta = (target - date.today()).days
        if delta < 0:
            return DocumentStatus.EXPIRED
        if delta <= 30:
            return DocumentStatus.EXPIRING_SOON
        return DocumentStatus.ACTIVE

    def days_until_relevant_date(self) -> Optional[int]:
        d = self.relevant_date()
        if not d:
            return None
        try:
            target = datetime.strptime(d, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
        return (target - date.today()).days

    def icon(self) -> str:
        try:
            return TYPE_ICONS[DocumentType(self.document_type)]
        except ValueError:
            return "📄"


@dataclass
class Reminder:
    """Represents a single reminder tied to a document."""

    id: Optional[int] = None
    document_id: int = 0
    title: str = ""
    reminder_date: str = ""
    status: str = "Pending"  # Pending / Dismissed / Done
    priority: str = Priority.NORMAL.value
    message: str = ""

    def days_left(self) -> int:
        try:
            target = datetime.strptime(self.reminder_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return 9999
        return (target - date.today()).days
