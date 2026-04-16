"""add user_id to orders

Revision ID: 7f12b2f8f8b1
Revises: e36a5d5b3765
Create Date: 2026-04-16 19:40:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7f12b2f8f8b1"
down_revision = "e36a5d5b3765"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_orders_user_id_users",
        "orders",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    connection = op.get_bind()
    first_user_id = connection.execute(sa.text("SELECT id FROM users LIMIT 1")).scalar()
    if first_user_id is not None:
        connection.execute(
            sa.text("UPDATE orders SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": first_user_id},
        )

    null_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM orders WHERE user_id IS NULL")
    ).scalar()
    if null_count and null_count > 0:
        raise RuntimeError(
            "Cannot set orders.user_id to NOT NULL: existing orders have no user mapping"
        )

    op.alter_column("orders", "user_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_orders_user_id_users", "orders", type_="foreignkey")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_column("orders", "user_id")
