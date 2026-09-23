"""
search_engine.py
------------------
Lightweight, deterministic "smart search" over stored documents.
Understands a handful of natural phrasings (e.g. "expiring this month",
"amounts above 10000", "certificates") on top of plain keyword search
across title / type / organization / product / extracted text.
"""

import re
from datetime import datetime, date
from typing import List, Optional

from models import Document, DocumentType

MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july",
               "august", "september", "october", "november", "december"]


class SearchEngine:
    def __init__(self, documents: List[Document]):
        self.documents = documents

    def search(self, query: str, doc_type: Optional[str] = None,
               category: Optional[str] = None) -> List[Document]:
        results = self.documents
        query = (query or "").strip().lower()

        if doc_type:
            results = [d for d in results if d.document_type == doc_type]
        if category:
            results = [d for d in results if d.category == category]

        if not query:
            return results

        # --- special natural-language patterns -----------------------
        above_match = re.search(r"above\s+(\d[\d,]*)", query)
        below_match = re.search(r"below\s+(\d[\d,]*)", query)
        if above_match:
            threshold = float(above_match.group(1).replace(",", ""))
            return [d for d in results if d.amount and d.amount > threshold]
        if below_match:
            threshold = float(below_match.group(1).replace(",", ""))
            return [d for d in results if d.amount and d.amount < threshold]

        if "expiring this month" in query or "expire this month" in query:
            today = date.today()
            out = []
            for d in results:
                dd = self._to_date(d.expiration_date or d.renewal_date)
                if dd and dd.year == today.year and dd.month == today.month and dd >= today:
                    out.append(d)
            return out

        year_match = re.search(r"\b(20\d{2})\b", query)
        if "from" in query and year_match:
            year = year_match.group(1)
            return [d for d in results if (d.created_at or "").startswith(year)
                    or (d.issue_date or "").startswith(year)
                    or (d.purchase_date or "").startswith(year)]

        if "renewal" in query or "renewals" in query or "renewing" in query:
            return [d for d in results if d.renewal_date]

        # match against a known document type name mentioned in the query
        for t in DocumentType:
            if t.value.lower().rstrip("s") in query or t.value.lower() in query:
                type_matches = [d for d in results if d.document_type == t.value]
                if type_matches:
                    return type_matches

        # --- fallback: plain keyword search across fields -------------
        terms = query.split()
        out = []
        for d in results:
            haystack = " ".join([
                d.title or "", d.document_type or "", d.organization or "",
                d.product_name or "", d.extracted_text or "", d.person_name or "",
                d.purchase_date or "", d.issue_date or "", d.expiration_date or "",
                d.renewal_date or "",
            ]).lower()
            if all(term in haystack for term in terms):
                out.append(d)
        return out

    @staticmethod
    def _to_date(value: Optional[str]):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
