"""
schemas/medication.py
Pydantic v2 request/response models for the medication feature.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Prescribed Dose ───────────────────────────────────────────────────────────

class PrescribedDoseOut(BaseModel):
    id: uuid.UUID
    medication_name: str
    dosage_mg: float
    pill_count: int
    frequency: str
    instructions: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class PrescribedDoseCreate(BaseModel):
    medication_name: str = Field(..., examples=["Rifampicin"])
    dosage_mg: float = Field(..., gt=0, examples=[150.0])
    pill_count: int = Field(..., ge=1, examples=[2])
    frequency: str = Field(default="Daily", examples=["Daily"])
    instructions: Optional[str] = None


class PrescribedDoseUpdate(BaseModel):
    medication_name: Optional[str] = None
    dosage_mg: Optional[float] = Field(default=None, gt=0)
    pill_count: Optional[int] = Field(default=None, ge=1)
    frequency: Optional[str] = None
    instructions: Optional[str] = None
    is_active: Optional[bool] = None


# ── Journey ───────────────────────────────────────────────────────────────────

class JourneyCreate(BaseModel):
    name: str = Field(..., examples=["Rifampicin & Isoniazid"])
    start_date: datetime
    end_date: Optional[datetime] = None
    clinical_notes: Optional[str] = None
    prescribed_doses: list[PrescribedDoseCreate] = []


class JourneyOut(BaseModel):
    id: uuid.UUID
    user_id: str
    name: str
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    reset_count: int
    clinical_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    prescribed_doses: list[PrescribedDoseOut] = []

    model_config = {"from_attributes": True}


class JourneyListItem(BaseModel):
    """Lightweight item for the 'My Journeys' list screen."""
    id: uuid.UUID
    name: str
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    on_track: bool                          # derived: no missed doses in last 3 days
    last_log_date: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JourneyListOut(BaseModel):
    journeys: list[JourneyListItem]


# ── Medication Log ────────────────────────────────────────────────────────────

class LogEntryIn(BaseModel):
    """A single dose checkbox result from the 'Log Medication' bottom sheet."""
    prescribed_dose_id: uuid.UUID
    taken: bool


class MedicationLogCreate(BaseModel):
    journey_id: uuid.UUID
    time_taken: datetime = Field(..., description="Exact datetime the user took the dose")
    entries: list[LogEntryIn] = Field(..., min_length=1)
    notes: Optional[str] = None


class LogEntryOut(BaseModel):
    id: uuid.UUID
    prescribed_dose_id: uuid.UUID
    medication_name: str          # flattened for Flutter convenience
    dosage_mg: float
    pill_count: int
    taken: bool

    model_config = {"from_attributes": True}


class MedicationLogOut(BaseModel):
    id: uuid.UUID
    journey_id: uuid.UUID
    user_id: str
    time_taken: datetime
    notes: Optional[str] = None
    created_at: datetime
    entries: list[LogEntryOut] = []

    model_config = {"from_attributes": True}


class MedicationLogListOut(BaseModel):
    logs: list[MedicationLogOut]
    total: int


# ── Reset / Adjust Journey ────────────────────────────────────────────────────

class ResetJourneyRequest(BaseModel):
    """
    Maps to the 'Adjust Journey' / 'Reset Treatment Journey' screen.
    Closes current journey and starts a new one with (optionally updated) dose.
    """
    medication_name: str = Field(..., examples=["Isoniazid (INH)"])
    dosage_mg: float = Field(..., gt=0, examples=[300.0])
    frequency: str = Field(default="Daily", examples=["Daily"])
    clinical_notes: Optional[str] = None


class ResetJourneyOut(BaseModel):
    old_journey_id: uuid.UUID
    new_journey: JourneyOut
    message: str


# ── Achievements ──────────────────────────────────────────────────────────────

class AchievementOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    description: str
    category: str
    icon: Optional[str] = None
    required_value: int
    badge_color: Optional[str] = None

    model_config = {"from_attributes": True}


class UserAchievementOut(BaseModel):
    achievement: AchievementOut
    unlocked: bool
    unlocked_at: Optional[datetime] = None
    current_progress: int
    percent: float              # current_progress / required_value * 100, capped at 100

    model_config = {"from_attributes": True}


class UserAchievementListOut(BaseModel):
    achievements: list[UserAchievementOut]
    total_unlocked: int
    total: int


# ── Streak / Stats (bonus, for dashboard) ─────────────────────────────────────

class JourneyStatsOut(BaseModel):
    journey_id: uuid.UUID
    current_streak: int         # consecutive days with at least one full log
    longest_streak: int
    total_doses_taken: int
    total_doses_missed: int
    adherence_percent: float    # taken / (taken + missed) * 100
    days_elapsed: int
    days_remaining: Optional[int] = None
    on_track: bool
    last_log_date: Optional[datetime] = None
    interrupted: bool           # True if last log > 2 days ago
    days_since_last_log: Optional[int] = None