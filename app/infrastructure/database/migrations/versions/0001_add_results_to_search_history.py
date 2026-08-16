"""add results, ai_summary, citations to search_history

Revision ID: 0001
Revises: 
Create Date: 2026-08-16

Adds three new columns to search_history so the full search result payload
(papers, AI summary, citation list) is persisted alongside query metadata.
This enables GET /api/v1/history to return complete past search results
without re-querying PubMed.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add full result payload columns (all nullable so existing rows are unaffected)
    op.add_column(
        "search_history",
        sa.Column("results", JSONB, nullable=True, comment="Full serialised paper list"),
    )
    op.add_column(
        "search_history",
        sa.Column("ai_summary", sa.Text, nullable=True, comment="LLM-generated evidence synthesis"),
    )
    op.add_column(
        "search_history",
        sa.Column("citations", JSONB, nullable=True, comment="List of cited PMID strings"),
    )

    # Migrate existing JSON columns to JSONB for better indexing performance
    op.alter_column("search_history", "intent",
                    type_=JSONB, existing_nullable=True)
    op.alter_column("search_history", "search_strategy",
                    type_=JSONB, existing_nullable=True)


def downgrade() -> None:
    op.drop_column("search_history", "citations")
    op.drop_column("search_history", "ai_summary")
    op.drop_column("search_history", "results")

    # Revert JSONB back to JSON
    op.alter_column("search_history", "intent",
                    type_=sa.JSON, existing_nullable=True)
    op.alter_column("search_history", "search_strategy",
                    type_=sa.JSON, existing_nullable=True)
