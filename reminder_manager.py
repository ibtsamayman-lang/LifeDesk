"""
reminder_manager.py
---------------------
Generates and prioritizes reminders from a document's dates. This is the
"Smart Reminders" engine — it never needs a human to schedule anything:
whenever a document with a relevant date is saved, reminders are derived
automatically.
"""

from datetime import datetime, timedelta
from typing import List

from database import Database
from models import Document, Reminder, Priority

DEFAULT_OFFSETS = [30, 7, 1]  # days before the target date


class ReminderManager:
    def __init__(self, db: Database):
        self.db = db

    def generate_for_document(self, doc: Document, offsets: List[int] = None) -> int:
        """Creates reminders for a document's expiration/renewal date.
        Returns the number of reminders created."""
        offsets = offsets or DEFAULT_OFFSETS
        target_date_str = doc.expiration_date or doc.renewal_date
        if not target_date_str or not doc.id:
            return 0

        try:
            target = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return 0

        label = "expires" if doc.expiration_date else "renews"
        created = 0
        today = datetime.today().date()

        for offset in sorted(offsets, reverse=True):
            remind_on = target - timedelta(days=offset)
            if remind_on < today:
                continue
            priority = self._priority_for_offset(offset)
            message = f"{doc.title} {label} in {offset} day{'s' if offset != 1 else ''}."
            reminder = Reminder(
                document_id=doc.id,
                title=doc.title,
                reminder_date=remind_on.strftime("%Y-%m-%d"),
                status="Pending",
                priority=priority.value,
                message=message,
            )
            self.db.add_reminder(reminder)
            created += 1

        # Always also add a "day of" reminder if not already covered and date is future/today
        if target >= today and 0 not in offsets:
            priority = Priority.URGENT
            message = f"{doc.title} {label} today."
            reminder = Reminder(
                document_id=doc.id,
                title=doc.title,
                reminder_date=target.strftime("%Y-%m-%d"),
                status="Pending",
                priority=priority.value,
                message=message,
            )
            self.db.add_reminder(reminder)
            created += 1

        return created

    def regenerate_for_document(self, doc: Document):
        self.db.delete_reminders_for_document(doc.id)
        self.generate_for_document(doc)

    @staticmethod
    def _priority_for_offset(offset: int) -> Priority:
        if offset <= 1:
            return Priority.URGENT
        if offset <= 7:
            return Priority.SOON
        return Priority.NORMAL

    @staticmethod
    def priority_for_days_left(days_left: int) -> Priority:
        if days_left <= 1:
            return Priority.URGENT
        if days_left <= 7:
            return Priority.SOON
        return Priority.NORMAL

    def get_upcoming(self, limit: int = 10) -> List[Reminder]:
        reminders = [r for r in self.db.get_all_reminders() if r.status == "Pending"]
        reminders.sort(key=lambda r: r.reminder_date)
        return reminders[:limit]

    def get_all_pending(self) -> List[Reminder]:
        return [r for r in self.db.get_all_reminders() if r.status == "Pending"]

    def dismiss(self, reminder_id: int):
        self.db.update_reminder_status(reminder_id, "Dismissed")

    def mark_done(self, reminder_id: int):
        self.db.update_reminder_status(reminder_id, "Done")
