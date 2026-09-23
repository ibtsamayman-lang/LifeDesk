"""
app.py
-------
LifeDesk — Smart Personal Document & Deadline Management System.
Main Streamlit entry point: sidebar navigation + all pages.

Run with:  python -m streamlit run app.py
"""

from datetime import datetime, date

import streamlit as st

from database import Database
from models import Document, DocumentType, DocumentStatus, STATUS_EMOJI, PRIORITY_EMOJI, Priority
from document_extractor import DocumentExtractor
from document_analyzer import DocumentAnalyzer
from reminder_manager import ReminderManager
from search_engine import SearchEngine
from insights import Insights
import ui
import utils

st.set_page_config(page_title="LifeDesk", page_icon="🧠", layout="wide")
utils.ensure_dirs()
ui.inject_css()

# ---------------------------------------------------------------- state --
if "db" not in st.session_state:
    st.session_state.db = Database()
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "selected_doc_id" not in st.session_state:
    st.session_state.selected_doc_id = None

db: Database = st.session_state.db
extractor = DocumentExtractor()
analyzer = DocumentAnalyzer()
reminder_mgr = ReminderManager(db)

NAV_ITEMS = [
    ("Dashboard", "🏠 Dashboard"),
    ("Add Document", "📤 Add Document"),
    ("My Documents", "📁 My Documents"),
    ("Reminders", "🔔 Reminders"),
    ("Search", "🔎 Search"),
    ("Ask LifeDesk", "🧠 Ask LifeDesk"),
    ("Insights", "📊 Insights"),
    ("Settings", "⚙️ Settings"),
]


def go_to(page_name: str, doc_id=None):
    st.session_state.page = page_name
    if doc_id is not None:
        st.session_state.selected_doc_id = doc_id


# ------------------------------------------------------------- sidebar --
with st.sidebar:
    st.markdown("## 🧠 LifeDesk")
    st.caption("Your important documents, understood and remembered.")
    st.markdown("---")
    for key, label in NAV_ITEMS:
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            go_to(key)
    st.markdown("---")
    doc_count = len(db.get_all_documents())
    st.caption(f"📄 {doc_count} document(s) tracked")


# ============================================================ helpers ===
def save_and_analyze(uploaded_file) -> Document:
    """Persists an uploaded file, extracts + analyzes it, saves the
    resulting record and generates reminders. Returns the Document."""
    safe_name = utils.safe_filename(uploaded_file.name)
    dest_path = utils.DOCS_DIR / safe_name
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    result = extractor.extract(str(dest_path))
    analysis = analyzer.analyze(result.text, uploaded_file.name)

    doc = Document(
        filename=uploaded_file.name,
        title=analysis["title"],
        document_type=analysis["document_type"],
        category=analysis["category"],
        organization=analysis["organization"],
        person_name=analysis["person_name"],
        product_name=analysis["product_name"],
        purchase_date=analysis["purchase_date"],
        issue_date=analysis["issue_date"],
        expiration_date=analysis["expiration_date"],
        renewal_date=analysis["renewal_date"],
        amount=analysis["amount"],
        currency=analysis["currency"],
        invoice_number=analysis["invoice_number"],
        email=analysis["email"],
        phone=analysis["phone"],
        keywords=analysis["keywords"],
        file_path=str(dest_path),
        extracted_text=result.text,
        extraction_note=result.note,
        is_demo=0,
    )
    doc.id = db.add_document(doc)
    reminder_mgr.generate_for_document(doc)
    return doc


def build_smart_summary(documents) -> str:
    total = len(documents)
    if total == 0:
        return "You have no documents yet. Upload your first document to get started."
    insights = Insights(documents)
    needs_attention = insights.count_needing_attention()
    warranties_active = sum(
        1 for d in documents
        if d.document_type == DocumentType.WARRANTY.value and d.compute_status() == DocumentStatus.ACTIVE
    )
    soon = [d for d in documents if d.compute_status() == DocumentStatus.EXPIRING_SOON]
    soon.sort(key=lambda d: d.days_until_relevant_date() or 9999)
    urgent_line = ""
    if soon:
        top = soon[0]
        urgent_line = f" <b>{top.title}</b> {'expires' if top.expiration_date else 'renews'} within {top.days_until_relevant_date()} day(s)."

    return (
        f"You have <b>{total}</b> document{'s' if total != 1 else ''}.<br>"
        f"<b>{needs_attention}</b> need attention this month.<br>"
        f"{urgent_line}<br>" if urgent_line else ""
    ) + f"You have <b>{warranties_active}</b> active warrant{'ies' if warranties_active != 1 else 'y'}."


# ============================================================== pages ===
def page_dashboard():
    ui.hero("LIFEDESK", "Your important things, understood and remembered.")
    documents = db.get_all_documents()

    st.markdown(f'<div class="ld-summary">{build_smart_summary(documents)}</div>', unsafe_allow_html=True)

    insights = Insights(documents)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("📄 Total Documents", str(len(documents)))
    with c2:
        ui.metric_card("⚠️ Needs Attention", str(insights.count_needing_attention()))
    with c3:
        upcoming = len(reminder_mgr.get_all_pending())
        ui.metric_card("📅 Upcoming Deadlines", str(upcoming))
    with c4:
        categories = len(set(d.category for d in documents)) if documents else 0
        ui.metric_card("🗂️ Categories", str(categories))

    ui.section_title("Needs Your Attention")
    attention_docs = [d for d in documents if d.compute_status() in
                       (DocumentStatus.EXPIRING_SOON, DocumentStatus.EXPIRED)]
    attention_docs.sort(key=lambda d: d.days_until_relevant_date() if d.days_until_relevant_date() is not None else 9999)
    if not attention_docs:
        st.markdown('<div class="ld-empty">🎉 Nothing urgent — you\'re all caught up.</div>', unsafe_allow_html=True)
    else:
        for d in attention_docs[:6]:
            days = d.days_until_relevant_date()
            urgency_class = "ld-alert-urgent" if (days is not None and days <= 3) else "ld-alert"
            verb = "expired" if (days is not None and days < 0) else ("expires" if d.expiration_date else "renews")
            day_text = f"{abs(days)} day(s) ago" if (days is not None and days < 0) else f"in {days} day(s)"
            st.markdown(
                f'<div class="{urgency_class}">⚠️ <b>{d.title}</b><br>{verb.capitalize()} {day_text}</div>',
                unsafe_allow_html=True,
            )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        ui.section_title("Recent Documents")
        recent = documents[:5]
        if not recent:
            st.markdown('<div class="ld-empty">No documents yet.</div>', unsafe_allow_html=True)
        for d in recent:
            st.markdown(ui.render_document_card_html(d), unsafe_allow_html=True)

    with col_b:
        ui.section_title("Document Overview")
        fig = insights.by_category_chart()
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown('<div class="ld-empty">Charts will appear once you add documents.</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("✨ Load Demo Data", use_container_width=False):
        demo_docs = utils.generate_demo_documents()
        for d in demo_docs:
            d.id = db.add_document(d)
            reminder_mgr.generate_for_document(d)
        st.success(f"Loaded {len(demo_docs)} demo documents.")
        st.rerun()


def page_add_document():
    ui.hero("Add Document", "Upload a file — LifeDesk reads and understands it for you.")
    tab1, tab2 = st.tabs(["📄 Single / Multiple Upload", "ℹ️ How it works"])

    with tab1:
        uploaded_files = st.file_uploader(
            "Drop PDF, PNG, JPG or JPEG files here",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
        )
        if uploaded_files and st.button("Analyze & Save", type="primary"):
            progress = st.progress(0.0, text="Analyzing documents...")
            saved_docs = []
            for i, f in enumerate(uploaded_files):
                try:
                    doc = save_and_analyze(f)
                    saved_docs.append(doc)
                except Exception as exc:
                    st.error(f"Could not process **{f.name}**: {type(exc).__name__}. The file was skipped.")
                progress.progress((i + 1) / len(uploaded_files), text=f"Processed {i+1}/{len(uploaded_files)}")
            progress.empty()

            if saved_docs:
                st.success(f"Saved and analyzed {len(saved_docs)} document(s).")
                for doc in saved_docs:
                    with st.expander(f"{doc.icon()} {doc.title} — review detected information", expanded=True):
                        if doc.extraction_note:
                            st.caption(f"ℹ️ {doc.extraction_note}")
                        cols = st.columns(2)
                        cols[0].markdown(f"**Type:** {doc.document_type}")
                        cols[0].markdown(f"**Organization:** {doc.organization}")
                        cols[0].markdown(f"**Person:** {doc.person_name}")
                        cols[0].markdown(f"**Product:** {doc.product_name}")
                        cols[1].markdown(f"**Expiration date:** {utils.format_date(doc.expiration_date) if doc.expiration_date else 'Not detected'}")
                        cols[1].markdown(f"**Renewal date:** {utils.format_date(doc.renewal_date) if doc.renewal_date else 'Not detected'}")
                        cols[1].markdown(f"**Amount:** {utils.format_amount(doc.amount, doc.currency)}")
                        cols[1].markdown(f"**Invoice #:** {doc.invoice_number}")
                        if st.button("View Full Details", key=f"view_new_{doc.id}"):
                            go_to("My Documents", doc.id)
                            st.rerun()

    with tab2:
        st.markdown("""
        1. **Upload** a PDF or image (receipt, warranty, certificate, invoice...)
        2. LifeDesk **extracts the text** (native PDF text, or OCR for scans/photos)
        3. It **classifies the document** and **pulls out key fields** automatically
        4. The record is **saved to your local database** — nothing is sent externally
        5. **Reminders are created automatically** for any expiration or renewal date found

        You almost never need to type anything by hand. If a field wasn't detected,
        it's shown as *Not detected* and you can fill it in later from the document's
        details page.
        """)


def page_my_documents():
    ui.hero("My Documents", "Everything you've stored, organized automatically.")
    documents = db.get_all_documents()

    if st.session_state.selected_doc_id:
        render_document_details(st.session_state.selected_doc_id)
        return

    if not documents:
        st.markdown('<div class="ld-empty">No documents yet. Go to <b>Add Document</b> to upload your first one.</div>', unsafe_allow_html=True)
        return

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        type_filter = st.selectbox("Filter by type", ["All"] + [t.value for t in DocumentType])
    with fc2:
        status_filter = st.selectbox("Filter by status", ["All"] + [s.value for s in DocumentStatus])
    with fc3:
        sort_by = st.selectbox("Sort by", ["Newest first", "Nearest deadline", "Title A-Z"])

    filtered = documents
    if type_filter != "All":
        filtered = [d for d in filtered if d.document_type == type_filter]
    if status_filter != "All":
        filtered = [d for d in filtered if d.compute_status().value == status_filter]
    if sort_by == "Nearest deadline":
        filtered.sort(key=lambda d: d.days_until_relevant_date() if d.days_until_relevant_date() is not None else 9999)
    elif sort_by == "Title A-Z":
        filtered.sort(key=lambda d: d.title.lower())

    st.caption(f"{len(filtered)} document(s)")
    cols = st.columns(3)
    for i, d in enumerate(filtered):
        with cols[i % 3]:
            st.markdown(ui.render_document_card_html(d), unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button("View Details", key=f"details_{d.id}", use_container_width=True):
                st.session_state.selected_doc_id = d.id
                st.rerun()
            if b2.button("Delete", key=f"delete_{d.id}", use_container_width=True):
                db.delete_document(d.id)
                st.rerun()


def render_document_details(doc_id: int):
    doc = db.get_document(doc_id)
    if not doc:
        st.warning("This document no longer exists.")
        st.session_state.selected_doc_id = None
        return

    if st.button("← Back to My Documents"):
        st.session_state.selected_doc_id = None
        st.rerun()

    status = doc.compute_status()
    st.markdown(f"## {doc.icon()} {doc.title}")
    st.markdown(f'<span class="ld-badge" style="background:{ui.priority_badge_color(Priority.NORMAL.value) if False else "#4F6BFE"}">{doc.document_type}</span> &nbsp; {STATUS_EMOJI[status]} **{status.value}**', unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### Details")
        st.markdown(f"**Organization:** {doc.organization}")
        st.markdown(f"**Person:** {doc.person_name}")
        st.markdown(f"**Product:** {doc.product_name}")
        st.markdown(f"**Purchase date:** {utils.format_date(doc.purchase_date) if doc.purchase_date else 'Not detected'}")
        st.markdown(f"**Issue date:** {utils.format_date(doc.issue_date) if doc.issue_date else 'Not detected'}")
        st.markdown(f"**Expiration date:** {utils.format_date(doc.expiration_date) if doc.expiration_date else 'Not detected'}")
        st.markdown(f"**Renewal date:** {utils.format_date(doc.renewal_date) if doc.renewal_date else 'Not detected'}")
        st.markdown(f"**Amount:** {utils.format_amount(doc.amount, doc.currency)}")
        st.markdown(f"**Invoice number:** {doc.invoice_number}")
        st.markdown(f"**Email:** {doc.email}")
        st.markdown(f"**Phone:** {doc.phone}")

    with right:
        st.markdown("#### File & Reminders")
        if doc.extraction_note:
            st.caption(f"ℹ️ {doc.extraction_note}")
        if doc.file_path and not doc.is_demo:
            try:
                with open(doc.file_path, "rb") as f:
                    st.download_button("📂 Open / Download File", f, file_name=doc.filename)
            except FileNotFoundError:
                st.warning("Original file could not be found on disk.")
        elif doc.is_demo:
            st.caption("This is demo data — no real file is attached.")

        doc_reminders = [r for r in db.get_all_reminders() if r.document_id == doc.id]
        if doc_reminders:
            st.markdown("**Reminders:**")
            for r in doc_reminders:
                st.markdown(f"- {PRIORITY_EMOJI.get(Priority(r.priority), '⚪')} {utils.format_date(r.reminder_date)} — {r.message} ({r.status})")
        else:
            st.caption("No reminders for this document.")

        if st.button("🔁 Regenerate Reminders"):
            reminder_mgr.regenerate_for_document(doc)
            st.success("Reminders regenerated.")
            st.rerun()

    st.markdown("---")
    with st.expander("✏️ Edit detected information"):
        with st.form(f"edit_form_{doc.id}"):
            c1, c2 = st.columns(2)
            title = c1.text_input("Title", doc.title)
            doc_type = c2.selectbox("Type", [t.value for t in DocumentType],
                                     index=[t.value for t in DocumentType].index(doc.document_type)
                                     if doc.document_type in [t.value for t in DocumentType] else 0)
            organization = c1.text_input("Organization", doc.organization)
            person_name = c2.text_input("Person", doc.person_name)
            exp_date = c1.text_input("Expiration date (YYYY-MM-DD)", doc.expiration_date or "")
            renew_date = c2.text_input("Renewal date (YYYY-MM-DD)", doc.renewal_date or "")
            amount = c1.number_input("Amount", value=float(doc.amount) if doc.amount else 0.0, step=1.0)
            currency = c2.text_input("Currency", doc.currency)

            if st.form_submit_button("Save Changes"):
                doc.title = title or doc.title
                doc.document_type = doc_type
                doc.category = doc_type
                doc.organization = organization or "Not detected"
                doc.person_name = person_name or "Not detected"
                doc.expiration_date = exp_date or None
                doc.renewal_date = renew_date or None
                doc.amount = amount if amount > 0 else None
                doc.currency = currency or "Not detected"
                db.update_document(doc)
                reminder_mgr.regenerate_for_document(doc)
                st.success("Document updated.")
                st.rerun()

    with st.expander("📄 View extracted text"):
        st.text_area("Extracted text", doc.extracted_text or "No text extracted.", height=200, disabled=True)

    st.markdown("---")
    if st.button("🗑️ Delete this document", type="secondary"):
        db.delete_document(doc.id)
        st.session_state.selected_doc_id = None
        st.success("Document deleted.")
        st.rerun()


def page_reminders():
    ui.hero("Reminders", "Every deadline LifeDesk is watching for you.")
    all_reminders = db.get_all_reminders()
    pending = [r for r in all_reminders if r.status == "Pending"]
    pending.sort(key=lambda r: r.reminder_date)

    if not pending:
        st.markdown('<div class="ld-empty">No active reminders. Add documents with dates to generate some.</div>', unsafe_allow_html=True)
        return

    ui.section_title("Smart Timeline")
    current_date_label = None
    for r in pending:
        label = utils.format_date(r.reminder_date)
        if label != current_date_label:
            st.markdown(f"**{label}**")
            current_date_label = label
        emoji = PRIORITY_EMOJI.get(Priority(r.priority), "⚪")
        doc = db.get_document(r.document_id)
        c1, c2, c3 = st.columns([6, 1, 1])
        c1.markdown(f"{emoji} {r.message}")
        if c2.button("Done", key=f"done_{r.id}"):
            reminder_mgr.mark_done(r.id)
            st.rerun()
        if c3.button("Dismiss", key=f"dismiss_{r.id}"):
            reminder_mgr.dismiss(r.id)
            st.rerun()

    st.markdown("---")
    with st.expander("View dismissed / completed reminders"):
        inactive = [r for r in all_reminders if r.status != "Pending"]
        if not inactive:
            st.caption("None yet.")
        for r in inactive:
            st.markdown(f"- ~~{r.message}~~ ({r.status})")


def page_search():
    ui.hero("Search", "Find anything — by name, type, date, or amount.")
    documents = db.get_all_documents()
    engine = SearchEngine(documents)

    query = st.text_input(
        "Try: \"Dell\", \"documents expiring this month\", \"amounts above 10000\", \"certificates\"..."
    )
    c1, c2 = st.columns(2)
    with c1:
        type_filter = st.selectbox("Type filter", ["Any"] + [t.value for t in DocumentType])
    with c2:
        category_filter = st.selectbox("Category filter", ["Any"] + sorted(set(d.category for d in documents)) if documents else ["Any"])

    results = engine.search(
        query,
        doc_type=None if type_filter == "Any" else type_filter,
        category=None if category_filter == "Any" else category_filter,
    )

    st.caption(f"{len(results)} result(s)")
    cols = st.columns(3)
    for i, d in enumerate(results):
        with cols[i % 3]:
            st.markdown(ui.render_document_card_html(d), unsafe_allow_html=True)
            if st.button("View Details", key=f"search_view_{d.id}", use_container_width=True):
                go_to("My Documents", d.id)
                st.rerun()


def page_ask_lifedesk():
    ui.hero("Ask LifeDesk", "Ask a question about your documents in plain language.")
    documents = db.get_all_documents()

    st.caption("Try: \"What expires next month?\", \"Show me all warranties\", "
               "\"Which documents need attention?\", \"How many invoices do I have?\", "
               "\"What was the price of my laptop?\", \"Which subscriptions renew soon?\"")

    question = st.text_input("Your question")
    if st.button("Ask", type="primary") or question:
        if not question.strip():
            st.info("Type a question above.")
        else:
            answer, matches = answer_question(question, documents)
            st.markdown(f'<div class="ld-summary">{answer}</div>', unsafe_allow_html=True)
            if matches:
                cols = st.columns(3)
                for i, d in enumerate(matches[:9]):
                    with cols[i % 3]:
                        st.markdown(ui.render_document_card_html(d), unsafe_allow_html=True)


def answer_question(question: str, documents):
    q = question.lower().strip()
    insights = Insights(documents)
    today = date.today()

    def is_in_month_offset(d: Document, months_ahead: int) -> bool:
        target = d.expiration_date or d.renewal_date
        if not target:
            return False
        try:
            dd = datetime.strptime(target, "%Y-%m-%d").date()
        except ValueError:
            return False
        # naive month-ahead window (approx 30 days per month)
        window_start = today
        window_end = today.replace(day=1)
        month = today.month - 1 + months_ahead
        year = today.year + month // 12
        month = month % 12 + 1
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        window_start = date(year, month, 1)
        window_end = date(year, month, last_day)
        return window_start <= dd <= window_end

    if "expire" in q and ("next month" in q):
        matches = [d for d in documents if is_in_month_offset(d, 1)]
        return (f"<b>{len(matches)}</b> document(s) expire next month." if matches
                else "Nothing expires next month."), matches

    if "warrant" in q:
        matches = [d for d in documents if d.document_type == DocumentType.WARRANTY.value]
        return f"You have <b>{len(matches)}</b> warranty document(s).", matches

    if "attention" in q or "need" in q and "attention" in q:
        matches = [d for d in documents if d.compute_status() in
                   (DocumentStatus.EXPIRING_SOON, DocumentStatus.EXPIRED)]
        return f"<b>{len(matches)}</b> document(s) need your attention.", matches

    if "how many invoice" in q or ("invoice" in q and "how many" in q):
        count = insights.count_by_type(DocumentType.INVOICE.value)
        return f"You have <b>{count}</b> invoice(s).", [d for d in documents if d.document_type == DocumentType.INVOICE.value]

    if "laptop" in q and ("price" in q or "cost" in q or "how much" in q):
        matches = [d for d in documents if "laptop" in (d.title + " " + d.product_name).lower()]
        if matches and matches[0].amount:
            return f"Your laptop record shows <b>{utils.format_amount(matches[0].amount, matches[0].currency)}</b>.", matches
        return "I couldn't find a laptop-related amount in your documents.", matches

    if "subscription" in q and ("renew" in q or "soon" in q):
        matches = [d for d in documents if d.document_type == DocumentType.SUBSCRIPTION.value and d.renewal_date]
        matches.sort(key=lambda d: d.renewal_date)
        return (f"<b>{len(matches)}</b> subscription(s) have an upcoming renewal." if matches
                else "No subscriptions have a detected renewal date."), matches

    if "certificate" in q:
        matches = [d for d in documents if d.document_type == DocumentType.CERTIFICATE.value]
        return f"You have <b>{len(matches)}</b> certificate(s).", matches

    if "expire" in q and "month" in q and "next" not in q:
        matches = [d for d in documents if is_in_month_offset(d, 0)]
        return (f"<b>{len(matches)}</b> document(s) expire this month." if matches
                else "Nothing expires this month."), matches

    # fallback: plain search
    engine = SearchEngine(documents)
    matches = engine.search(question)
    if matches:
        return f"I found <b>{len(matches)}</b> document(s) matching your question.", matches
    return "I couldn't find anything specific for that question — try rephrasing, or use the Search page for keyword search.", []


def page_insights():
    ui.hero("Insights", "Your document data, visualized.")
    documents = db.get_all_documents()
    if not documents:
        st.markdown('<div class="ld-empty">Add documents to see insights.</div>', unsafe_allow_html=True)
        return

    insights = Insights(documents)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total tracked amount", f"{insights.total_tracked_amount():,.0f}")
    c2.metric("Active warranties", sum(1 for d in documents if d.document_type == DocumentType.WARRANTY.value and d.compute_status() == DocumentStatus.ACTIVE))
    c3.metric("Subscriptions", insights.count_by_type(DocumentType.SUBSCRIPTION.value))
    c4.metric("Needs attention", insights.count_needing_attention())

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Documents by Category")
        fig = insights.by_category_chart()
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("#### Documents by Type")
        fig = insights.by_type_pie()
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Monthly Additions")
        fig = insights.monthly_additions_chart()
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Not enough data yet.")
    with col4:
        st.markdown("#### Status Breakdown")
        fig = insights.status_breakdown_chart()
        if fig:
            st.plotly_chart(fig, use_container_width=True)


def page_settings():
    ui.hero("Settings", "Configure LifeDesk to fit how you work.")

    st.markdown("#### Reminder Preferences")
    current_days = db.get_setting("reminder_days", "30,7,1")
    days_input = st.text_input("Default reminder days before a deadline (comma-separated)", current_days)
    if st.button("Save Reminder Preferences"):
        db.set_setting("reminder_days", days_input)
        st.success("Saved.")

    st.markdown("#### Default Currency")
    currency = st.text_input("Default currency", db.get_setting("default_currency", "EGP"))
    if st.button("Save Currency"):
        db.set_setting("default_currency", currency)
        st.success("Saved.")

    st.markdown("#### Data Folder")
    st.code(db.get_setting("data_folder", "data/documents"))
    st.caption("Documents are always stored locally on this machine and never uploaded elsewhere.")

    st.markdown("---")
    st.markdown("#### Danger Zone")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Clear Demo Data"):
            st.session_state["confirm_clear_demo"] = True
        if st.session_state.get("confirm_clear_demo"):
            st.warning("This will remove all demo documents. Confirm?")
            if st.button("Yes, clear demo data"):
                db.clear_demo_data()
                st.session_state["confirm_clear_demo"] = False
                st.success("Demo data cleared.")
                st.rerun()
    with col2:
        if st.button("⚠️ Reset Entire Database"):
            st.session_state["confirm_reset"] = True
        if st.session_state.get("confirm_reset"):
            st.error("This permanently deletes ALL documents and reminders. Confirm?")
            if st.button("Yes, reset everything"):
                db.reset_database()
                st.session_state["confirm_reset"] = False
                st.success("Database reset.")
                st.rerun()


# ============================================================== router ===
PAGES = {
    "Dashboard": page_dashboard,
    "Add Document": page_add_document,
    "My Documents": page_my_documents,
    "Reminders": page_reminders,
    "Search": page_search,
    "Ask LifeDesk": page_ask_lifedesk,
    "Insights": page_insights,
    "Settings": page_settings,
}

PAGES.get(st.session_state.page, page_dashboard)()
