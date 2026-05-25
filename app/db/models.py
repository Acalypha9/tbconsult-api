import uuid
from datetime import datetime, timezone
from typing import Any
<<<<<<< HEAD
from sqlalchemy import String, Text, Integer, Boolean, ARRAY
=======
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, ARRAY, Float, Date, Enum as SAEnum
>>>>>>> 5b5d1ebcd7588ceedb2f6d957c11b0b23ee825e0
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
import enum


class Base(DeclarativeBase):
    pass


# ── Existing models (unchanged) ───────────────────────────────────────────────

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Session_(Base):
    __tablename__ = "session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    user_query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_entities: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)
    red_flags_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=True)
    retrieved_doc_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    llm_response: Mapped[str] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)


# ── Enums ─────────────────────────────────────────────────────────────────────

class JourneyStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    paused = "paused"
    reset = "reset"


class AchievementCategory(str, enum.Enum):
    streak = "streak"
    milestone = "milestone"
    consistency = "consistency"
    recovery = "recovery"


# ── New models ────────────────────────────────────────────────────────────────

class MedicationJourney(Base):
    """
    Represents a treatment plan / regimen assigned to a user.
    Maps to the 'My Journeys' screen.
    """
    __tablename__ = "medication_journey"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)          # e.g. "Rifampicin & Isoniazid"
    status: Mapped[str] = mapped_column(
        SAEnum(JourneyStatus, name="journey_status"), nullable=False, default=JourneyStatus.active
    )
    start_date: Mapped[datetime] = mapped_column(nullable=False)
    end_date: Mapped[datetime] = mapped_column(nullable=True)               # None = ongoing
    reset_count: Mapped[int] = mapped_column(Integer, default=0)
    clinical_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # relationships
    prescribed_doses: Mapped[list["PrescribedDose"]] = relationship(
        "PrescribedDose", back_populates="journey", cascade="all, delete-orphan"
    )
    logs: Mapped[list["MedicationLog"]] = relationship(
        "MedicationLog", back_populates="journey", cascade="all, delete-orphan"
    )


class PrescribedDose(Base):
    """
    Individual medication within a journey.
    e.g. Rifampicin 150mg • 2 Pills, Daily
    """
    __tablename__ = "prescribed_dose"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medication_journey.id"), nullable=False)
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)   # "Rifampicin"
    dosage_mg: Mapped[float] = mapped_column(Float, nullable=False)             # 150
    pill_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1) # 2
    frequency: Mapped[str] = mapped_column(String(50), nullable=False, default="Daily")  # "Daily"
    instructions: Mapped[str] = mapped_column(Text, nullable=True)              # "Take with full glass of water..."
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    journey: Mapped["MedicationJourney"] = relationship("MedicationJourney", back_populates="prescribed_doses")
    log_entries: Mapped[list["MedicationLogEntry"]] = relationship(
        "MedicationLogEntry", back_populates="prescribed_dose", cascade="all, delete-orphan"
    )


class MedicationLog(Base):
    """
    One log session = user opens 'Log Medication' and confirms.
    Contains the time_taken and links to individual dose entries.
    """
    __tablename__ = "medication_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medication_journey.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    time_taken: Mapped[datetime] = mapped_column(nullable=False)               # The "08:30 AM" the user selects
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    journey: Mapped["MedicationJourney"] = relationship("MedicationJourney", back_populates="logs")
    entries: Mapped[list["MedicationLogEntry"]] = relationship(
        "MedicationLogEntry", back_populates="log", cascade="all, delete-orphan"
    )


class MedicationLogEntry(Base):
    """
    Whether a specific prescribed dose was taken in a log session.
    Rifampicin ✓, Isoniazid ✗, Pyrazinamide ✓ → three rows per log.
    """
    __tablename__ = "medication_log_entry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medication_log.id"), nullable=False)
    prescribed_dose_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescribed_dose.id"), nullable=False)
    taken: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    log: Mapped["MedicationLog"] = relationship("MedicationLog", back_populates="entries")
    prescribed_dose: Mapped["PrescribedDose"] = relationship("PrescribedDose", back_populates="log_entries")


# ── Achievement system ────────────────────────────────────────────────────────

class Achievement(Base):
    """
    Achievement definitions — seeded once, never owned by a user.
    """
    __tablename__ = "achievement"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # machine key, e.g. "streak_7"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        SAEnum(AchievementCategory, name="achievement_category"), nullable=False
    )
    icon: Mapped[str] = mapped_column(String(100), nullable=True)               # icon name for Flutter
    required_value: Mapped[int] = mapped_column(Integer, nullable=False)        # e.g. 7 for 7-day streak
    badge_color: Mapped[str] = mapped_column(String(20), nullable=True)         # hex color for Flutter UI
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    user_achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="achievement"
    )


class UserAchievement(Base):
    """
    Tracks which achievements a user has unlocked and their progress.
    """
    __tablename__ = "user_achievement"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    achievement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("achievement.id"), nullable=False)
    unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    unlocked_at: Mapped[datetime] = mapped_column(nullable=True)
    current_progress: Mapped[int] = mapped_column(Integer, default=0)           # e.g. current streak count
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    achievement: Mapped["Achievement"] = relationship("Achievement", back_populates="user_achievements")