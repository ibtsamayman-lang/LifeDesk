"""
insights.py
-------------
Turns stored documents into aggregate insights using pandas for
aggregation and Plotly for interactive charts.
"""

from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from models import Document, DocumentStatus, STATUS_COLORS

CHART_COLORWAY = ["#4F6BFE", "#22B07D", "#F2A93B", "#EF5B5B", "#8B5CF6", "#0EA5B7", "#6B7280"]


class Insights:
    def __init__(self, documents: List[Document]):
        self.documents = documents
        self.df = self._to_dataframe(documents)

    @staticmethod
    def _to_dataframe(documents: List[Document]) -> pd.DataFrame:
        if not documents:
            return pd.DataFrame(columns=[
                "id", "title", "document_type", "category", "amount", "currency",
                "expiration_date", "renewal_date", "created_at", "status",
            ])
        rows = []
        for d in documents:
            rows.append({
                "id": d.id, "title": d.title, "document_type": d.document_type,
                "category": d.category, "amount": d.amount, "currency": d.currency,
                "expiration_date": d.expiration_date, "renewal_date": d.renewal_date,
                "created_at": d.created_at, "status": d.compute_status().value,
            })
        df = pd.DataFrame(rows)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        return df

    def by_category_chart(self):
        if self.df.empty:
            return None
        counts = self.df["category"].value_counts().reset_index()
        counts.columns = ["Category", "Count"]
        fig = px.bar(counts, x="Category", y="Count", color="Category",
                      color_discrete_sequence=CHART_COLORWAY)
        fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                           margin=dict(t=20, b=10, l=10, r=10))
        return fig

    def by_type_pie(self):
        if self.df.empty:
            return None
        counts = self.df["document_type"].value_counts().reset_index()
        counts.columns = ["Type", "Count"]
        fig = px.pie(counts, names="Type", values="Count", hole=0.55,
                      color_discrete_sequence=CHART_COLORWAY)
        fig.update_layout(margin=dict(t=20, b=10, l=10, r=10), paper_bgcolor="white")
        return fig

    def monthly_additions_chart(self):
        if self.df.empty or self.df["created_at"].isna().all():
            return None
        monthly = self.df.dropna(subset=["created_at"]).copy()
        monthly["month"] = monthly["created_at"].dt.to_period("M").astype(str)
        counts = monthly.groupby("month").size().reset_index(name="Documents Added")
        fig = px.line(counts, x="month", y="Documents Added", markers=True,
                       color_discrete_sequence=["#4F6BFE"])
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                           margin=dict(t=20, b=10, l=10, r=10), xaxis_title="Month")
        return fig

    def status_breakdown_chart(self):
        if self.df.empty:
            return None
        counts = self.df["status"].value_counts().reset_index()
        counts.columns = ["Status", "Count"]
        color_map = {s.value: STATUS_COLORS[s] for s in DocumentStatus}
        fig = px.bar(counts, x="Status", y="Count", color="Status",
                      color_discrete_map=color_map)
        fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                           margin=dict(t=20, b=10, l=10, r=10))
        return fig

    def total_tracked_amount(self) -> float:
        if self.df.empty:
            return 0.0
        return float(self.df["amount"].fillna(0).sum())

    def count_by_type(self, doc_type: str) -> int:
        if self.df.empty:
            return 0
        return int((self.df["document_type"] == doc_type).sum())

    def count_needing_attention(self) -> int:
        if self.df.empty:
            return 0
        return int(self.df["status"].isin(
            [DocumentStatus.EXPIRING_SOON.value, DocumentStatus.EXPIRED.value]
        ).sum())
