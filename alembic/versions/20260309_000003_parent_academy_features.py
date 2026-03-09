"""parent and academy features

Revision ID: 20260309_000003
Revises: 20260303_000002
Create Date: 2026-03-09 00:00:03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260309_000003"
down_revision: Union[str, None] = "20260303_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("coppa_consent_given", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("coppa_consent_at", sa.DateTime(), nullable=True))
    op.add_column(
        "users",
        sa.Column("communication_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "trial_bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("booking_kind", sa.String(length=20), nullable=False, server_default="trial"),
        sa.Column("program_slug", sa.String(length=64), nullable=False),
        sa.Column("child_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("child_grade", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/New_York"),
        sa.Column("slot_start", sa.DateTime(), nullable=False),
        sa.Column("slot_end", sa.DateTime(), nullable=False),
        sa.Column("meeting_link", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("notes", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trial_bookings_parent_id"), "trial_bookings", ["parent_id"], unique=False)
    op.create_index(op.f("ix_trial_bookings_tutor_id"), "trial_bookings", ["tutor_id"], unique=False)
    op.create_index(op.f("ix_trial_bookings_slot_start"), "trial_bookings", ["slot_start"], unique=False)

    op.create_table(
        "program_enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("program_slug", sa.String(length=64), nullable=False),
        sa.Column("child_name", sa.String(length=120), nullable=False),
        sa.Column("child_grade", sa.String(length=40), nullable=False),
        sa.Column("plan_type", sa.String(length=20), nullable=False),
        sa.Column("billing_cycle_months", sa.Integer(), nullable=False),
        sa.Column("list_price_usd", sa.Integer(), nullable=False),
        sa.Column("plan_discount_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bundle_discount_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_price_usd", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("next_billing_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_program_enrollments_parent_id"), "program_enrollments", ["parent_id"], unique=False)
    op.create_index(op.f("ix_program_enrollments_program_slug"), "program_enrollments", ["program_slug"], unique=False)

    op.create_table(
        "session_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=False),
        sa.Column("session_start", sa.DateTime(), nullable=False),
        sa.Column("session_end", sa.DateTime(), nullable=False),
        sa.Column("attendance_status", sa.String(length=20), nullable=False, server_default="attended"),
        sa.Column("note_summary", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("homework", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("meeting_link", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["program_enrollments.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_session_notes_enrollment_id"), "session_notes", ["enrollment_id"], unique=False)
    op.create_index(op.f("ix_session_notes_parent_id"), "session_notes", ["parent_id"], unique=False)
    op.create_index(op.f("ix_session_notes_tutor_id"), "session_notes", ["tutor_id"], unique=False)
    op.create_index(op.f("ix_session_notes_session_start"), "session_notes", ["session_start"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_session_notes_session_start"), table_name="session_notes")
    op.drop_index(op.f("ix_session_notes_tutor_id"), table_name="session_notes")
    op.drop_index(op.f("ix_session_notes_parent_id"), table_name="session_notes")
    op.drop_index(op.f("ix_session_notes_enrollment_id"), table_name="session_notes")
    op.drop_table("session_notes")

    op.drop_index(op.f("ix_program_enrollments_program_slug"), table_name="program_enrollments")
    op.drop_index(op.f("ix_program_enrollments_parent_id"), table_name="program_enrollments")
    op.drop_table("program_enrollments")

    op.drop_index(op.f("ix_trial_bookings_slot_start"), table_name="trial_bookings")
    op.drop_index(op.f("ix_trial_bookings_tutor_id"), table_name="trial_bookings")
    op.drop_index(op.f("ix_trial_bookings_parent_id"), table_name="trial_bookings")
    op.drop_table("trial_bookings")

    op.drop_column("users", "communication_opt_in")
    op.drop_column("users", "coppa_consent_at")
    op.drop_column("users", "coppa_consent_given")
