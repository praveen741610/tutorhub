"""initial schema

Revision ID: 20260303_000001
Revises:
Create Date: 2026-03-03 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260303_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "tutor_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("headline", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("bio", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("hourly_rate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subjects", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("languages", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tutor_profiles_user_id"), "tutor_profiles", ["user_id"], unique=True)

    op.create_table(
        "availability_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("is_booked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_availability_slots_start_time"), "availability_slots", ["start_time"], unique=False)
    op.create_index(op.f("ix_availability_slots_tutor_id"), "availability_slots", ["tutor_id"], unique=False)

    op.create_table(
        "booking_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("slot_start", sa.DateTime(), nullable=False),
        sa.Column("slot_end", sa.DateTime(), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="requested"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_requests_slot_start"), "booking_requests", ["slot_start"], unique=False)
    op.create_index(op.f("ix_booking_requests_student_id"), "booking_requests", ["student_id"], unique=False)
    op.create_index(op.f("ix_booking_requests_tutor_id"), "booking_requests", ["tutor_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_booking_requests_tutor_id"), table_name="booking_requests")
    op.drop_index(op.f("ix_booking_requests_student_id"), table_name="booking_requests")
    op.drop_index(op.f("ix_booking_requests_slot_start"), table_name="booking_requests")
    op.drop_table("booking_requests")

    op.drop_index(op.f("ix_availability_slots_tutor_id"), table_name="availability_slots")
    op.drop_index(op.f("ix_availability_slots_start_time"), table_name="availability_slots")
    op.drop_table("availability_slots")

    op.drop_index(op.f("ix_tutor_profiles_user_id"), table_name="tutor_profiles")
    op.drop_table("tutor_profiles")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
