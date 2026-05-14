"""Add primary usage service URL setting.

Revision ID: 20260514_0001
Revises: 20260513_0001
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260514_0001"
down_revision: str | None = "20260513_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def upgrade() -> None:
    if _column_exists("app_settings", "usage_service_url"):
        return
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "usage_service_url",
                sa.String(length=500),
                nullable=False,
                server_default="http://127.0.0.1:18318",
            )
        )


def downgrade() -> None:
    if not _column_exists("app_settings", "usage_service_url"):
        return
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_column("usage_service_url")
