"""
api/routes/medication.py

All endpoints for:
  - GET/POST  /v1/medication/journeys
  - GET       /v1/medication/journeys/{id}
  - GET       /v1/medication/journeys/{id}/stats
  - POST      /v1/medication/journeys/{id}/reset
  - POST      /v1/medication/logs
  - GET       /v1/medication/logs?journey_id=...
  - GET       /v1/medication/achievements
  - POST      /v1/medication/achievements/seed   (admin / one-time)
"""
from __future__ import annotations

import uuid
import math
from datetime import datetime, timezone, timedelta, date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.db.models import (
    MedicationJourney,
    PrescribedDose,
    MedicationLog,
    MedicationLogEntry,
    Achievement,
    UserAchievement,
    JourneyStatus,
    AchievementCategory,
)
from app.schemas.medication import (
    JourneyCreate,
    JourneyOut,
    JourneyListOut,
    JourneyListItem,
    JourneyStatsOut,
    MedicationLogCreate,
    MedicationLogOut,
    MedicationLogListOut,
    LogEntryOut,
    ResetJourneyRequest,
    ResetJourneyOut,
    UserAchievementOut,
    UserAchievementListOut,
    AchievementOut,
)
from app.services.achievement import evaluate_and_unlock, seed_achievements

router = APIRouter(prefix="/medication", tags=["Medication"])

UserDep = Annotated[dict, Depends(get_current_user)]
DBDep = Annotated[AsyncSession, Depends(get_db)]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _get_journey_or_404(
    journey_id: uuid.UUID, user_id: str, db: AsyncSession
) -> MedicationJourney:
    result = await db.execute(
        select(MedicationJourney)
        .options(selectinload(MedicationJourney.prescribed_doses))
        .where(
            MedicationJourney.id == journey_id,
            MedicationJourney.user_id == user_id,
        )
    )
    journey = result.scalar_one_or_none()
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found.")
    return journey


async def _compute_stats(
    journey: MedicationJourney, user_id: str, db: AsyncSession
) -> JourneyStatsOut:
    """Compute streak and adherence stats for a journey."""

    logs_result = await db.execute(
        select(MedicationLog)
        .options(selectinload(MedicationLog.entries))
        .where(
            MedicationLog.journey_id == journey.id,
            MedicationLog.user_id == user_id,
        )
        .order_by(desc(MedicationLog.time_taken))
    )
    logs = logs_result.scalars().all()

    if not logs:
        days_elapsed = (
            (_utcnow() - journey.start_date.replace(tzinfo=timezone.utc)).days
            if journey.start_date.tzinfo is None
            else (_utcnow() - journey.start_date).days
        )
        days_remaining = None
        if journey.end_date:
            end = (
                journey.end_date
                if journey.end_date.tzinfo
                else journey.end_date.replace(tzinfo=timezone.utc)
            )
            days_remaining = max(0, (end - _utcnow()).days)

        return JourneyStatsOut(
            journey_id=journey.id,
            current_streak=0,
            longest_streak=0,
            total_doses_taken=0,
            total_doses_missed=0,
            adherence_percent=0.0,
            days_elapsed=days_elapsed,
            days_remaining=days_remaining,
            on_track=False,
            last_log_date=None,
            interrupted=False,
            days_since_last_log=None,
            completed_dates=[],  # <--- Tambahan
        )

    # Unique log dates HANYA untuk hari di mana user BENAR-BENAR minum obat (taken = True)
    log_dates = sorted(
        {
            (log.time_taken.date() if hasattr(log.time_taken, "date") else log.time_taken)
            for log in logs
            if any(e.taken for e in log.entries)
        },
        reverse=True,
    )

    # Sort Ascending khusus untuk dilempar ke kalender Flutter
    completed_dates = sorted(list(log_dates))

    today = _utcnow().date()

    # Current streak
    current_streak = 0
    expected = today
    if log_dates:
        for i, d in enumerate(log_dates):
            if i == 0:
                if (today - d).days > 1:
                    break
                current_streak = 1
                expected = d - timedelta(days=1)
            else:
                if d == expected:
                    current_streak += 1
                    expected = d - timedelta(days=1)
                else:
                    break

    # Longest streak
    longest_streak = 0
    if log_dates:
        temp = 1
        prev = log_dates[0]
        for d in log_dates[1:]:
            if (prev - d).days == 1:
                temp += 1
            else:
                longest_streak = max(longest_streak, temp)
                temp = 1
            prev = d
        longest_streak = max(longest_streak, temp)

    # Dose totals
    total_taken = sum(1 for log in logs for e in log.entries if e.taken)
    total_missed = sum(1 for log in logs for e in log.entries if not e.taken)
    total = total_taken + total_missed
    adherence_percent = round((total_taken / total * 100), 1) if total else 0.0

    # Days elapsed / remaining
    start = (
        journey.start_date
        if journey.start_date.tzinfo
        else journey.start_date.replace(tzinfo=timezone.utc)
    )
    days_elapsed = (_utcnow() - start).days
    days_remaining = None
    if journey.end_date:
        end = (
            journey.end_date
            if journey.end_date.tzinfo
            else journey.end_date.replace(tzinfo=timezone.utc)
        )
        days_remaining = max(0, (end - _utcnow()).days)

    last_log = logs[0]
    last_log_date = (
        last_log.time_taken
        if last_log.time_taken.tzinfo
        else last_log.time_taken.replace(tzinfo=timezone.utc)
    )
    days_since = (_utcnow() - last_log_date).days
    interrupted = days_since > 2
    on_track = not interrupted and adherence_percent >= 80.0

    return JourneyStatsOut(
        journey_id=journey.id,
        current_streak=current_streak,
        longest_streak=longest_streak,
        total_doses_taken=total_taken,
        total_doses_missed=total_missed,
        adherence_percent=adherence_percent,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        on_track=on_track,
        last_log_date=last_log_date,
        interrupted=interrupted,
        days_since_last_log=days_since,
        completed_dates=completed_dates,  # <--- Tambahan kirim ke frontend
    )


# ── Journey routes ────────────────────────────────────────────────────────────

@router.get("/journeys", response_model=JourneyListOut, summary="List all journeys for current user")
async def list_journeys(current_user: UserDep, db: DBDep):
    user_id: str = current_user["user_id"]

    result = await db.execute(
        select(MedicationJourney)
        .options(selectinload(MedicationJourney.logs))
        .where(MedicationJourney.user_id == user_id)
        .order_by(desc(MedicationJourney.created_at))
    )
    journeys = result.scalars().all()

    items: list[JourneyListItem] = []
    for j in journeys:
        last_log = max(j.logs, key=lambda l: l.time_taken, default=None) if j.logs else None
        last_log_date = last_log.time_taken if last_log else None

        on_track = False
        if last_log_date:
            last_dt = last_log_date if last_log_date.tzinfo else last_log_date.replace(tzinfo=timezone.utc)
            days_since = (_utcnow() - last_dt).days
            on_track = days_since <= 1

        items.append(
            JourneyListItem(
                id=j.id,
                name=j.name,
                status=j.status,
                start_date=j.start_date,
                end_date=j.end_date,
                on_track=on_track,
                last_log_date=last_log_date,
            )
        )

    return JourneyListOut(journeys=items)


@router.post(
    "/journeys",
    response_model=JourneyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new medication journey",
)
async def create_journey(body: JourneyCreate, current_user: UserDep, db: DBDep):
    user_id: str = current_user["user_id"]

    journey = MedicationJourney(
        id=uuid.uuid4(),
        user_id=user_id,
        name=body.name,
        status=JourneyStatus.active,
        start_date=body.start_date,
        end_date=body.end_date,
        clinical_notes=body.clinical_notes,
    )
    db.add(journey)
    await db.flush()  # get journey.id before adding doses

    for dose_in in body.prescribed_doses:
        db.add(
            PrescribedDose(
                id=uuid.uuid4(),
                journey_id=journey.id,
                **dose_in.model_dump(),
            )
        )

    await db.commit()
    await db.refresh(journey, ["prescribed_doses"])
    return journey


@router.get("/journeys/{journey_id}", response_model=JourneyOut, summary="Get a single journey")
async def get_journey(journey_id: uuid.UUID, current_user: UserDep, db: DBDep):
    user_id: str = current_user["user_id"]
    return await _get_journey_or_404(journey_id, user_id, db)


@router.get(
    "/journeys/{journey_id}/stats",
    response_model=JourneyStatsOut,
    summary="Get streak & adherence stats for a journey",
)
async def get_journey_stats(journey_id: uuid.UUID, current_user: UserDep, db: DBDep):
    user_id: str = current_user["user_id"]
    journey = await _get_journey_or_404(journey_id, user_id, db)
    return await _compute_stats(journey, user_id, db)

@router.delete(
    "/journeys/{journey_id}", status_code=status.HTTP_200_OK, summary="Delete a medication journey"
)
async def delete_journey(journey_id: uuid.UUID, current_user: UserDep, db: DBDep):
    user_id: str = current_user["user_id"]
    journey = await _get_journey_or_404(journey_id, user_id, db)

    await db.delete(journey)
    await db.commit()

    return {"message": "Journey successfully deleted."}

# ── Reset / Adjust Journey ────────────────────────────────────────────────────

@router.post(
    "/journeys/{journey_id}/reset",
    response_model=ResetJourneyOut,
    summary="Reset (adjust) a treatment journey — maps to the 'Adjust Journey' screen",
)
async def reset_journey(
    journey_id: uuid.UUID,
    body: ResetJourneyRequest,
    current_user: UserDep,
    db: DBDep,
):
    user_id: str = current_user["user_id"]
    old_journey = await _get_journey_or_404(journey_id, user_id, db)

    if old_journey.status != JourneyStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active journeys can be reset.",
        )

    # Mark old journey as reset
    old_journey.status = JourneyStatus.reset
    old_journey.end_date = _utcnow()
    await db.flush()

    # Carry over existing doses from old journey, override with new dose
    new_journey = MedicationJourney(
        id=uuid.uuid4(),
        user_id=user_id,
        name=old_journey.name,
        status=JourneyStatus.active,
        start_date=_utcnow(),
        reset_count=old_journey.reset_count + 1,
        clinical_notes=body.clinical_notes,
    )
    db.add(new_journey)
    await db.flush()

    # Copy existing active doses and apply the reset override
    old_doses_result = await db.execute(
        select(PrescribedDose).where(
            PrescribedDose.journey_id == old_journey.id,
            PrescribedDose.is_active == True,
        )
    )
    old_doses = old_doses_result.scalars().all()

    for old_dose in old_doses:
        if old_dose.medication_name.lower() in body.medication_name.lower():
            # Apply the updated dose from the reset form
            db.add(
                PrescribedDose(
                    id=uuid.uuid4(),
                    journey_id=new_journey.id,
                    medication_name=body.medication_name,
                    dosage_mg=body.dosage_mg,
                    pill_count=old_dose.pill_count,
                    frequency=body.frequency,
                    instructions=old_dose.instructions,
                )
            )
        else:
            # Keep the existing dose unchanged
            db.add(
                PrescribedDose(
                    id=uuid.uuid4(),
                    journey_id=new_journey.id,
                    medication_name=old_dose.medication_name,
                    dosage_mg=old_dose.dosage_mg,
                    pill_count=old_dose.pill_count,
                    frequency=old_dose.frequency,
                    instructions=old_dose.instructions,
                )
            )

    await db.commit()
    await db.refresh(new_journey, ["prescribed_doses"])

    return ResetJourneyOut(
        old_journey_id=old_journey.id,
        new_journey=new_journey,
        message="Treatment journey has been reset. Your new journey starts fresh.",
    )


# ── Medication Log routes ─────────────────────────────────────────────────────

@router.post(
    "/logs",
    response_model=MedicationLogOut,
    status_code=status.HTTP_201_CREATED,
    summary="Log a medication session — maps to 'Confirm Consumption'",
)
async def create_medication_log(body: MedicationLogCreate, current_user: UserDep, db: DBDep):
    user_id: str = current_user["user_id"]

    # Validate journey ownership
    journey = await _get_journey_or_404(body.journey_id, user_id, db)
    if journey.status != JourneyStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot log doses for a non-active journey.",
        )

    frequency_map = {
        "Daily": 1,
        "Once Daily": 1,
        "Twice daily": 2,
        "Three times daily": 3,
        "Weekly": 1,
    }
    active_doses = [d for d in journey.prescribed_doses if d.is_active]
    max_logs_allowed = 1
    for d in active_doses:
        max_logs_allowed = max(max_logs_allowed, frequency_map.get(d.frequency, 1))

    dt = body.time_taken
    start_of_day = datetime(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)
    end_of_day = start_of_day + timedelta(days=1)

    logs_today_result = await db.execute(
        select(func.count(MedicationLog.id)).where(
            MedicationLog.journey_id == journey.id,
            MedicationLog.user_id == user_id,
            MedicationLog.time_taken >= start_of_day,
            MedicationLog.time_taken < end_of_day,
        )
    )
    today_logs_count = logs_today_result.scalar() or 0

    if today_logs_count >= max_logs_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maksimal konsumsi obat untuk hari ini ({max_logs_allowed} kali) sudah tercapai.",
        )

    # Validate all prescribed_dose_ids belong to this journey
    dose_ids = {e.prescribed_dose_id for e in body.entries}
    doses_result = await db.execute(
        select(PrescribedDose).where(
            PrescribedDose.id.in_(dose_ids),
            PrescribedDose.journey_id == journey.id,
        )
    )
    found_doses = {d.id: d for d in doses_result.scalars().all()}
    for dose_id in dose_ids:
        if dose_id not in found_doses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prescribed dose {dose_id} does not belong to this journey.",
            )

    # Create log
    log = MedicationLog(
        id=uuid.uuid4(),
        journey_id=journey.id,
        user_id=user_id,
        time_taken=body.time_taken,
        notes=body.notes,
    )
    db.add(log)
    await db.flush()

    # Create entries
    for entry_in in body.entries:
        db.add(
            MedicationLogEntry(
                id=uuid.uuid4(),
                log_id=log.id,
                prescribed_dose_id=entry_in.prescribed_dose_id,
                taken=entry_in.taken,
            )
        )

    await db.commit()
    await db.refresh(log, ["entries"])

    # Evaluate achievements (fire and forget — won't fail the log)
    try:
        await evaluate_and_unlock(user_id, journey.id, db)
    except Exception:
        pass

    # Build response with flattened dose info
    entries_out: list[LogEntryOut] = []
    for entry in log.entries:
        dose = found_doses[entry.prescribed_dose_id]
        entries_out.append(
            LogEntryOut(
                id=entry.id,
                prescribed_dose_id=entry.prescribed_dose_id,
                medication_name=dose.medication_name,
                dosage_mg=dose.dosage_mg,
                pill_count=dose.pill_count,
                taken=entry.taken,
            )
        )

    return MedicationLogOut(
        id=log.id,
        journey_id=log.journey_id,
        user_id=log.user_id,
        time_taken=log.time_taken,
        notes=log.notes,
        created_at=log.created_at,
        entries=entries_out,
    )


@router.get(
    "/logs",
    response_model=MedicationLogListOut,
    summary="Get medication logs, optionally filtered by journey",
)
async def list_logs(
    current_user: UserDep,
    db: DBDep,
    journey_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    user_id: str = current_user["user_id"]

    q = (
        select(MedicationLog)
        .options(selectinload(MedicationLog.entries).selectinload(MedicationLogEntry.prescribed_dose))
        .where(MedicationLog.user_id == user_id)
        .order_by(desc(MedicationLog.time_taken))
    )
    if journey_id:
        q = q.where(MedicationLog.journey_id == journey_id)

    count_result = await db.execute(
        select(func.count(MedicationLog.id)).where(MedicationLog.user_id == user_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(q.limit(limit).offset(offset))
    logs = result.scalars().all()

    logs_out: list[MedicationLogOut] = []
    for log in logs:
        entries_out = [
            LogEntryOut(
                id=e.id,
                prescribed_dose_id=e.prescribed_dose_id,
                medication_name=e.prescribed_dose.medication_name,
                dosage_mg=e.prescribed_dose.dosage_mg,
                pill_count=e.prescribed_dose.pill_count,
                taken=e.taken,
            )
            for e in log.entries
        ]
        logs_out.append(
            MedicationLogOut(
                id=log.id,
                journey_id=log.journey_id,
                user_id=log.user_id,
                time_taken=log.time_taken,
                notes=log.notes,
                created_at=log.created_at,
                entries=entries_out,
            )
        )

    return MedicationLogListOut(logs=logs_out, total=total)


# ── Achievement routes ────────────────────────────────────────────────────────

@router.get(
    "/achievements",
    response_model=UserAchievementListOut,
    summary="Get all achievements with user progress",
)
async def list_achievements(current_user: UserDep, db: DBDep):
    user_id: str = current_user["user_id"]

    # All achievement definitions
    all_ach_result = await db.execute(select(Achievement))
    all_ach = all_ach_result.scalars().all()

    # User's progress rows
    user_ach_result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == user_id)
    )
    user_ach_map: dict[uuid.UUID, UserAchievement] = {
        ua.achievement_id: ua for ua in user_ach_result.scalars().all()
    }

    items: list[UserAchievementOut] = []
    total_unlocked = 0

    for ach in all_ach:
        ua = user_ach_map.get(ach.id)
        progress = ua.current_progress if ua else 0
        unlocked = ua.unlocked if ua else False
        unlocked_at = ua.unlocked_at if ua else None
        if unlocked:
            total_unlocked += 1

        percent = min(100.0, round((progress / ach.required_value) * 100, 1))

        items.append(
            UserAchievementOut(
                achievement=AchievementOut.model_validate(ach),
                unlocked=unlocked,
                unlocked_at=unlocked_at,
                current_progress=progress,
                percent=percent,
            )
        )

    # Sort: unlocked first, then by progress desc
    items.sort(key=lambda x: (not x.unlocked, -x.percent))

    return UserAchievementListOut(
        achievements=items,
        total_unlocked=total_unlocked,
        total=len(items),
    )


@router.post(
    "/achievements/seed",
    summary="Seed achievement definitions (run once — idempotent)",
    status_code=status.HTTP_200_OK,
)
async def seed_achievements_endpoint(current_user: UserDep, db: DBDep):
    """
    Inserts all predefined achievement definitions.
    Safe to call multiple times — skips already-existing keys.
    """
    new_count = await seed_achievements(db)
    return {"inserted": new_count, "message": f"{new_count} new achievements seeded."}