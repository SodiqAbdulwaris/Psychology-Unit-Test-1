"""staff_student_admin_split

Revision ID: b3d0f3c7e21f
Revises: 9fbe777c4802
Create Date: 2026-04-07 14:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3d0f3c7e21f"
down_revision: Union[str, Sequence[str], None] = "9fbe777c4802"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute("UPDATE users SET is_admin = true WHERE role = 'admin'")
    op.execute("UPDATE users SET role = 'staff' WHERE role IN ('admin', 'psychologist')")
    op.alter_column("users", "is_admin", server_default=None)


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin = true")
    op.drop_column("users", "is_admin")
