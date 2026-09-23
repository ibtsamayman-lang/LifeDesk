"""
database.py
------------
Persistent storage layer for LifeDesk, built on SQLite.

The Database class acts as a "Repository" (DocumentRepository /
ReminderRepository responsibilities combined into one cohesive object)
that encapsulates all SQL so the rest of the app never writes raw SQL.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional

from models import Document, Reminder

DB_PATH = Path("data/lifedesk.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    title TEXT,
    document_type TEXT,
    category TEXT,
    organization TEXT,
    person_name TEXT,
    product_name TEXT,
    purchase_date TEXT,
    issue_date TEXT,
    expiration_date TEXT,
    renewal_date TEXT,
    amount REAL,
    currency TEXT,
    invoice_number TEXT,
    email TEXT,
    phone TEXT,
    keywords TEXT,
    file_path TEXT,
    extracted_text TEXT,
    extraction_note TEXT,
    is_demo INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    title TEXT,
    reminder_date TEXT,
    status TEXT DEFAULT 'Pending',
    priority TEXT,
    message TEXT,
    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS document_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    event_type TEXT,
    event_date TEXT,
    note TEXT,
    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

DEFAULT_SETTINGS = {
    "default_currency": "EGP",
    "reminder_days": "30,7,1",
    "data_folder": "data/documents",
}


class Database:
    """Encapsulates all SQLite access for LifeDesk (Repository pattern)."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            for k, v in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
                )

    # ---------------------------------------------------------- documents --
    def add_document(self, doc: Document) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO documents
                (filename, title, document_type, category, organization, person_name,
                 product_name, purchase_date, issue_date, expiration_date, renewal_date,
                 amount, currency, invoice_number, email, phone, keywords, file_path,
                 extracted_text, extraction_note, is_demo, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    doc.filename, doc.title, doc.document_type, doc.category,
                    doc.organization, doc.person_name, doc.product_name,
                    doc.purchase_date, doc.issue_date, doc.expiration_date,
                    doc.renewal_date, doc.amount, doc.currency, doc.invoice_number,
                    doc.email, doc.phone, doc.keywords, doc.file_path,
                    doc.extracted_text, doc.extraction_note, doc.is_demo, doc.created_at,
                ),
            )
            return cur.lastrowid

    def update_document(self, doc: Document):
        with self._connect() as conn:
            conn.execute(
                """UPDATE documents SET title=?, document_type=?, category=?, organization=?,
                   person_name=?, product_name=?, purchase_date=?, issue_date=?,
                   expiration_date=?, renewal_date=?, amount=?, currency=?, invoice_number=?,
                   email=?, phone=? WHERE id=?""",
                (
                    doc.title, doc.document_type, doc.category, doc.organization,
                    doc.person_name, doc.product_name, doc.purchase_date, doc.issue_date,
                    doc.expiration_date, doc.renewal_date, doc.amount, doc.currency,
                    doc.invoice_number, doc.email, doc.phone, doc.id,
                ),
            )

    def delete_document(self, doc_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM reminders WHERE document_id=?", (doc_id,))
            conn.execute("DELETE FROM document_events WHERE document_id=?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))

    def get_document(self, doc_id: int) -> Optional[Document]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            return self._row_to_document(row) if row else None

    def get_all_documents(self, include_demo: bool = True) -> List[Document]:
        with self._connect() as conn:
            if include_demo:
                rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE is_demo=0 ORDER BY created_at DESC"
                ).fetchall()
            return [self._row_to_document(r) for r in rows]

    def clear_demo_data(self):
        with self._connect() as conn:
            ids = [r["id"] for r in conn.execute("SELECT id FROM documents WHERE is_demo=1")]
            for i in ids:
                conn.execute("DELETE FROM reminders WHERE document_id=?", (i,))
            conn.execute("DELETE FROM documents WHERE is_demo=1")

    def reset_database(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM reminders")
            conn.execute("DELETE FROM document_events")
            conn.execute("DELETE FROM documents")

    @staticmethod
    def _row_to_document(row: sqlite3.Row) -> Document:
        d = dict(row)
        return Document(**d)

    # ---------------------------------------------------------- reminders --
    def add_reminder(self, rem: Reminder) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO reminders (document_id, title, reminder_date, status, priority, message)
                   VALUES (?,?,?,?,?,?)""",
                (rem.document_id, rem.title, rem.reminder_date, rem.status, rem.priority, rem.message),
            )
            return cur.lastrowid

    def delete_reminders_for_document(self, doc_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM reminders WHERE document_id=?", (doc_id,))

    def get_all_reminders(self) -> List[Reminder]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reminders ORDER BY reminder_date ASC"
            ).fetchall()
            return [Reminder(**dict(r)) for r in rows]

    def update_reminder_status(self, reminder_id: int, status: str):
        with self._connect() as conn:
            conn.execute("UPDATE reminders SET status=? WHERE id=?", (status, reminder_id))

    # ----------------------------------------------------------- settings --
    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )


# DocumentRepository is an explicit alias so the module vocabulary matches
# the spec's "DocumentRepository" concept while avoiding duplicate logic.
DocumentRepository = Database
