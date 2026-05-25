"""Add medication journey, logs, and achievement tables

Revision ID: 002_medication_journey
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_medication_journey"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create enums via raw SQL (DO block = safe if already exists) ───────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE journey_status AS ENUM ('active', 'completed', 'paused', 'reset');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE achievement_category AS ENUM ('streak', 'milestone', 'consistency', 'recovery');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # ── medication_journey ─────────────────────────────────────────────────
    op.create_table(
        "medication_journey",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "paused", "reset",
                    name="journey_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_medication_journey_user_id", "medication_journey", ["user_id"])

    # ── prescribed_dose ────────────────────────────────────────────────────
    op.create_table(
        "prescribed_dose",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("medication_journey.id", ondelete="CASCADE"), nullable=False),
        sa.Column("medication_name", sa.String(255), nullable=False),
        sa.Column("dosage_mg", sa.Float(), nullable=False),
        sa.Column("pill_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("frequency", sa.String(50), nullable=False, server_default="Daily"),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_prescribed_dose_journey_id", "prescribed_dose", ["journey_id"])

    # ── medication_log ─────────────────────────────────────────────────────
    op.create_table(
        "medication_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("medication_journey.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("time_taken", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_medication_log_user_id", "medication_log", ["user_id"])
    op.create_index("ix_medication_log_journey_id", "medication_log", ["journey_id"])
    op.create_index("ix_medication_log_time_taken", "medication_log", ["time_taken"])

    # ── medication_log_entry ───────────────────────────────────────────────
    op.create_table(
        "medication_log_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("log_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("medication_log.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prescribed_dose_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("prescribed_dose.id", ondelete="CASCADE"), nullable=False),
        sa.Column("taken", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_log_entry_log_id", "medication_log_entry", ["log_id"])

    # ── achievement ────────────────────────────────────────────────────────
    op.create_table(
        "achievement",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum("streak", "milestone", "consistency", "recovery",
                    name="achievement_category", create_type=False),   # ← fixed
            nullable=False,
        ),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("required_value", sa.Integer(), nullable=False),
        sa.Column("badge_color", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # ── user_achievement ───────────────────────────────────────────────────
    op.create_table(
        "user_achievement",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("achievement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("achievement.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unlocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_user_achievement_user_id", "user_achievement", ["user_id"])
    op.create_unique_constraint(
        "uq_user_achievement", "user_achievement", ["user_id", "achievement_id"]
    )


def downgrade() -> None:
    op.drop_table("user_achievement")
    op.drop_table("achievement")
    op.drop_table("medication_log_entry")
    op.drop_table("medication_log")
    op.drop_table("prescribed_dose")
    op.drop_table("medication_journey")
    op.execute("DROP TYPE IF EXISTS journey_status")
    op.execute("DROP TYPE IF EXISTS achievement_category")