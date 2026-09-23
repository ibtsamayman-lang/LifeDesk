# 🧠 LifeDesk

**Your important documents, understood and remembered.**

LifeDesk is a Smart Personal Document & Deadline Management System. It is not a
file manager and not a to-do list — it's a system that *reads* your documents,
understands what they are, extracts the information that matters, and quietly
tracks the deadlines hidden inside them so you never have to remember on your own.

---

## 1. Problem Statement

Important personal documents contain valuable information, but users often have
no organized way to understand, track, and remember the actions associated with
those documents. A warranty PDF sits in a Downloads folder. A subscription
invoice gets buried in email. A university certificate's re-issue deadline is
forgotten entirely. The information is *in* the document — nobody re-reads it
in time.

## 2. Why It Matters

Missed warranty windows cost money. Missed subscription cancellations cost
money. Missed certificate or ID renewal deadlines cost time and stress. The
underlying issue isn't a lack of storage — it's a lack of **understanding** of
what's already stored.

## 3. Solution

LifeDesk transforms uploaded documents into structured, searchable, trackable
information and automatically alerts users about important dates. Upload a
file; LifeDesk reads it (via native PDF text extraction or OCR), classifies
it, pulls out dates/amounts/organizations/contacts, stores a clean structured
record in SQLite, and generates reminders automatically — no manual data entry
required.

---

## 4. Main Features

- **Automatic document understanding** — classification into 11 document types
  (Warranty, Invoice, Receipt, Subscription, University Document, Certificate,
  Identification, Medical, Contract, Payment, Insurance, Other)
- **Automatic information extraction** — dates, amounts/currency, emails,
  phone numbers, organizations, invoice numbers — via regex + contextual
  keyword scoring, no paid AI API required
- **OCR fallback** — scanned PDFs and photographed documents are read via
  pytesseract when native text isn't available
- **Smart Reminders** — 30/7/1-day-before reminders generated automatically
  from any detected expiration or renewal date, with 🔴 Urgent / 🟠 Soon /
  🟢 Normal prioritization
- **Dashboard** — live summary cards, "Needs Your Attention" feed, recent
  documents, category chart — all computed from the real database, never
  hard-coded
- **My Documents** — filterable, sortable document cards with full detail
  pages, inline editing, and reminder regeneration
- **Search** — keyword search across all fields plus natural phrasings like
  *"documents expiring this month"* or *"amounts above 10000"*
- **Ask LifeDesk** — deterministic natural-language Q&A over your own data
  (no external AI API needed) — *"What expires next month?"*, *"How many
  invoices do I have?"*
- **Insights** — Pandas + Plotly charts: by category, by type, monthly
  additions, status breakdown, total tracked value
- **Smart Timeline** — chronological view of every upcoming reminder
- **Demo Data** — one click populates realistic sample documents for a
  presentation, and can be cleared again from Settings
- **Settings** — reminder-day preferences, default currency, destructive
  actions gated behind confirmation

## 5. Technologies

| Purpose            | Library                     |
|---------------------|------------------------------|
| Web UI              | Streamlit                   |
| Database            | SQLite (via `sqlite3`)      |
| Data analysis       | Pandas                      |
| Charts              | Plotly                      |
| PDF text extraction | PyMuPDF (`fitz`)            |
| Image handling      | Pillow                      |
| OCR                 | pytesseract (optional)      |
| Pattern extraction  | Regular expressions (`re`)  |

## 6. Architecture

```
LifeDesk/
├── app.py                 # Streamlit entry point, navigation, all pages
├── database.py             # SQLite access layer (Database / DocumentRepository)
├── models.py                # Document, Reminder, enums (DocumentType, Status, Priority)
├── document_extractor.py    # PDF/image → text (PyMuPDF + OCR fallback)
├── document_analyzer.py     # text → structured understanding (classification, dates, amounts, entities)
├── reminder_manager.py      # date → prioritized reminders
├── search_engine.py         # keyword + natural-phrase search
├── insights.py               # Pandas/Plotly aggregate analytics
├── utils.py                  # safe filenames, formatting, demo data
├── ui.py                     # custom CSS + reusable styled components
├── requirements.txt
├── data/
│   ├── documents/            # uploaded files, stored with collision-safe names
│   └── lifedesk.db            # SQLite database (auto-created on first run)
└── README.md
```

The pipeline for every uploaded file:

```
Upload → DocumentExtractor.extract() → DocumentAnalyzer.analyze()
       → Document record → Database.add_document()
       → ReminderManager.generate_for_document() → shown on Dashboard/Reminders
```

## 7. Database Design

**documents** — one row per stored document: filename, title, document_type,
category, organization, person_name, product_name, purchase/issue/expiration/
renewal dates, amount, currency, invoice_number, email, phone, keywords,
file_path, extracted_text, extraction_note, is_demo, created_at.

**reminders** — one row per generated reminder: document_id (FK, cascades on
delete), title, reminder_date, status (Pending/Done/Dismissed), priority,
message.

**document_events** — reserved table for future event-logging (e.g. edits,
re-analysis) — created alongside the other tables so the schema is
extensible without a migration.

**settings** — simple key/value store for user preferences.

Foreign keys are enforced (`PRAGMA foreign_keys = ON`) and reminders are
cleaned up when a document is deleted.

## 8. Where OOP Is Used, and Why

- **`Document` / `Reminder` (`models.py`)** — dataclasses that encapsulate a
  record's fields *and* its derived behavior (`compute_status()`,
  `days_until_relevant_date()`, `icon()`), so status logic lives in one place
  instead of being recomputed inconsistently across pages.
- **`DocumentType`, `DocumentStatus`, `Priority` (Enums)** — controlled
  vocabularies that prevent typo'd string literals ("Warrenty" vs "Warranty")
  from silently breaking filters, charts, and reminders.
- **`DocumentExtractor`** — encapsulates every text-extraction strategy (PDF
  native text, PDF OCR fallback, image OCR) behind one `.extract()` method,
  so `app.py` never needs to know *how* a file was read.
- **`DocumentAnalyzer`** — a cohesive object whose methods
  (`classify_document`, `extract_dates`, `extract_amounts`, `extract_emails`,
  `extract_phone_numbers`, `extract_entities`, `analyze`) can be tested and
  reused independently, and composed together in `analyze()`.
- **`Database` (aliased as `DocumentRepository`)** — the Repository pattern:
  all SQL lives in one class, so every other module works with plain Python
  objects (`Document`, `Reminder`) instead of raw rows.
- **`ReminderManager`** — composition over the `Database` object; it doesn't
  inherit from it, it *uses* it, keeping reminder-generation logic separate
  from storage logic (single-responsibility).
- **`SearchEngine` / `Insights`** — each takes a list of `Document` objects in
  its constructor and exposes methods that operate on that encapsulated
  state, rather than free functions passing lists around everywhere.

No class was created "for the sake of it" — each one owns a distinct
responsibility in the pipeline above.

## 9. How Document Extraction Works

1. **PDFs**: PyMuPDF reads native text per page. If the combined text is
   below a minimum length threshold (likely a scanned PDF), each page is
   rendered to an image at 2x resolution and passed to `pytesseract` for OCR.
2. **Images**: Pillow opens and grayscales the image (auto-correcting EXIF
   orientation) before OCR.
3. If OCR isn't installed/available, the app **never crashes** — it falls
   back to whatever native text exists and shows a clear note such as *"OCR
   is unavailable. Text-based PDF extraction was used."*

## 10. How Reminders Work

`ReminderManager.generate_for_document()` looks at a document's expiration
date (or renewal date if no expiration was found) and creates reminders at
30, 7, and 1 days before that date (configurable in Settings), plus a
same-day reminder — skipping any that have already passed. Each reminder is
assigned a priority (🔴 Urgent ≤1 day, 🟠 Soon ≤7 days, 🟢 Normal otherwise)
used throughout the Dashboard, Reminders page, and Smart Timeline.

## 11. Installation

```bash
cd LifeDesk
pip install -r requirements.txt
```

OCR is optional but recommended for scanned documents — it requires the
Tesseract binary to be installed on your system separately from the Python
package (e.g. `apt install tesseract-ocr` on Debian/Ubuntu, or
`brew install tesseract` on macOS). If it's unavailable, LifeDesk keeps
working using native PDF text only.

## 12. Running the Project

```bash
python -m streamlit run app.py
```

The SQLite database and `data/documents/` folder are created automatically on
first run — no manual setup required. Click **"Load Demo Data"** on the
Dashboard for an instant, realistic preview.

## 13. Example Use Cases

- Upload a laptop warranty PDF → LifeDesk detects it's a Warranty, finds the
  "valid until" date, and reminds you a week before it expires.
- Upload a phone bill → classified as Invoice, amount and invoice number
  extracted automatically.
- Ask *"Which subscriptions renew soon?"* → instant answer from your own data.
- Search *"documents from 2026"* or *"amounts above 10000"* → instant,
  deterministic filtering.

## 14. Limitations

- Extraction accuracy depends on document layout; templated bank statements
  or unusual layouts may need manual correction via the Edit form.
- Date parsing assumes common formats (`YYYY-MM-DD`, `DD/MM/YYYY`, and named
  months); highly nonstandard date formats may not be detected.
- OCR quality depends on image resolution and the installed Tesseract
  language pack.
- "Ask LifeDesk" understands a defined set of question patterns plus a
  keyword-search fallback — it is not a general-purpose language model.

## 15. Future Improvements

- Folder-watch / auto-import for a designated inbox folder.
- Multi-language OCR and classification keyword sets.
- Optional, explicitly opt-in integration with an external AI API for
  more flexible free-form Q&A (the core product intentionally works without one).
- Push/email notifications for reminders instead of in-app only.
- Per-document custom reminder schedules.

---

## Privacy & Security

All files and the SQLite database stay on the local machine. Nothing is
uploaded to an external service by default. Extracted text is never printed
to the terminal or logs. Uploaded filenames are sanitized and made unique
before being written to disk, and file types are validated against an
allow-list (PDF, PNG, JPG, JPEG) before processing.
