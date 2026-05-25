"""
services/achievement.py

Handles:
  1. Seeding all achievement definitions into the DB (run once).
  2. Evaluating which achievements to unlock after a medication log is saved.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Achievement,
    UserAchievement,
    MedicationLog,
    MedicationLogEntry,
    MedicationJourney,
    AchievementCategory,
)


# ── Seed data ─────────────────────────────────────────────────────────────────
# Each dict maps 1-to-1 to the Achievement model.
# Add / edit freely — the seeder is idempotent (upsert on `key`).

ACHIEVEMENT_SEEDS: list[dict] = [
    # ── Streak achievements ──────────────────────────────────────────────
    {
        "key": "streak_3",
        "title": "First Steps",
        "description": "Take your medication 3 days in a row.",
        "category": AchievementCategory.streak,
        "icon": "local_fire_department",
        "required_value": 3,
        "badge_color": "#FF8C42",
    },
    {
        "key": "streak_7",
        "title": "One Week Warrior",
        "description": "Maintain a 7-day medication streak.",
        "category": AchievementCategory.streak,
        "icon": "whatshot",
        "required_value": 7,
        "badge_color": "#FF5733",
    },
    {
        "key": "streak_14",
        "title": "Two-Week Champion",
        "description": "Keep your streak going for 14 days.",
        "category": AchievementCategory.streak,
        "icon": "star",
        "required_value": 14,
        "badge_color": "#FFC300",
    },
    {
        "key": "streak_30",
        "title": "Monthly Master",
        "description": "30 consecutive days — you're unstoppable!",
        "category": AchievementCategory.streak,
        "icon": "emoji_events",
        "required_value": 30,
        "badge_color": "#DAA520",
    },
    {
        "key": "streak_60",
        "title": "Iron Will",
        "description": "60 days straight. Your dedication is inspiring.",
        "category": AchievementCategory.streak,
        "icon": "military_tech",
        "required_value": 60,
        "badge_color": "#C0C0C0",
    },
    {
        "key": "streak_180",
        "title": "Half-Year Hero",
        "description": "180 days of perfect adherence. Extraordinary!",
        "category": AchievementCategory.streak,
        "icon": "workspace_premium",
        "required_value": 180,
        "badge_color": "#FFD700",
    },
    # ── Milestone achievements (total logs) ───────────────────────────────
    {
        "key": "logs_1",
        "title": "First Dose Logged",
        "description": "You logged your very first medication dose.",
        "category": AchievementCategory.milestone,
        "icon": "check_circle",
        "required_value": 1,
        "badge_color": "#2ECC71",
    },
    {
        "key": "logs_10",
        "title": "10 Doses Down",
        "description": "You have logged 10 medication sessions.",
        "category": AchievementCategory.milestone,
        "icon": "looks_10",
        "required_value": 10,
        "badge_color": "#1ABC9C",
    },
    {
        "key": "logs_30",
        "title": "30 Doses Strong",
        "description": "30 medication logs completed. Keep going!",
        "category": AchievementCategory.milestone,
        "icon": "auto_awesome",
        "required_value": 30,
        "badge_color": "#3498DB",
    },
    {
        "key": "logs_100",
        "title": "Century Club",
        "description": "100 medication sessions logged. Incredible commitment.",
        "category": AchievementCategory.milestone,
        "icon": "grade",
        "required_value": 100,
        "badge_color": "#9B59B6",
    },
    # ── Consistency achievements (all doses taken in a session) ───────────
    {
        "key": "full_dose_1",
        "title": "Complete Care",
        "description": "Take all prescribed doses in a single session.",
        "category": AchievementCategory.consistency,
        "icon": "done_all",
        "required_value": 1,
        "badge_color": "#27AE60",
    },
    {
        "key": "full_dose_7",
        "title": "Perfect Week",
        "description": "Complete all doses every day for 7 days.",
        "category": AchievementCategory.consistency,
        "icon": "verified",
        "required_value": 7,
        "badge_color": "#2980B9",
    },
    {
        "key": "full_dose_30",
        "title": "Flawless Month",
        "description": "Full dose compliance every day for 30 days.",
        "category": AchievementCategory.consistency,
        "icon": "diamond",
        "required_value": 30,
        "badge_color": "#8E44AD",
    },
    # ── Recovery achievements (comeback after reset) ───────────────────────
    {
        "key": "comeback_1",
        "title": "Back on Track",
        "description": "Resumed medication after an interrupted streak.",
        "category": AchievementCategory.recovery,
        "icon": "restart_alt",
        "required_value": 1,
        "badge_color": "#E67E22",
    },
    {
        "key": "comeback_streak_7",
        "title": "Resilient",
        "description": "Reached a 7-day streak after a reset.",
        "category": AchievementCategory.recovery,
        "icon": "trending_up",
        "required_value": 7,
        "badge_color": "#E74C3C",
    },
]


# ── Seeder ────────────────────────────────────────────────────────────────────

async def seed_achievements(db: AsyncSession) -> int:
    """
    Idempotent: inserts only achievements whose `key` doesn't exist yet.
    Returns number of new rows inserted.
    """
    existing_keys_result = await db.execute(select(Achievement.key))
    existing_keys: set[str] = {row[0] for row in existing_keys_result.fetchall()}

    new_count = 0
    for seed in ACHIEVEMENT_SEEDS:
        if seed["key"] in existing_keys:
            continue
        db.add(Achievement(id=uuid.uuid4(), **seed))
        new_count += 1

    await db.commit()
    return new_count


# ── Helper: compute streak ────────────────────────────────────────────────────

async def _compute_streak(user_id: str, journey_id: uuid.UUID, db: AsyncSession) -> tuple[int, int]:
    """
    Returns (current_streak, longest_streak) for a user's journey.
    A day counts if at least one log exists for that calendar day.
    """
    result = await db.execute(
        select(func.date(MedicationLog.time_taken))
        .where(
            MedicationLog.user_id == user_id,
            MedicationLog.journey_id == journey_id,
        )
        .order_by(func.date(MedicationLog.time_taken).desc())
    )
    log_dates = sorted({row[0] for row in result.fetchall()}, reverse=True)

    if not log_dates:
        return 0, 0

    today = datetime.now(timezone.utc).date()
    current_streak = 0
    longest_streak = 0
    temp_streak = 1
    expected = today

    # current streak (from today backwards)
    for i, d in enumerate(log_dates):
        if i == 0:
            if (today - d).days > 1:        # more than 1 day gap from today
                current_streak = 0
                break
            current_streak = 1
            expected = d - timedelta(days=1)
        else:
            if d == expected:
                current_streak += 1
                expected = d - timedelta(days=1)
            else:
                break

    # longest streak
    prev = log_dates[0]
    for d in log_dates[1:]:
        if (prev - d).days == 1:
            temp_streak += 1
        else:
            longest_streak = max(longest_streak, temp_streak)
            temp_streak = 1
        prev = d
    longest_streak = max(longest_streak, temp_streak)

    return current_streak, longest_streak


async def _total_full_dose_days(user_id: str, journey_id: uuid.UUID, db: AsyncSession) -> int:
    """
    Count days where ALL prescribed doses were taken (taken=True for every entry).
    """
    result = await db.execute(
        select(MedicationLog.id, MedicationLog.time_taken)
        .where(
            MedicationLog.user_id == user_id,
            MedicationLog.journey_id == journey_id,
        )
    )
    logs = result.fetchall()

    full_days: set = set()
    for log_id, time_taken in logs:
        entries_result = await db.execute(
            select(MedicationLogEntry).where(MedicationLogEntry.log_id == log_id)
        )
        entries = entries_result.scalars().all()
        if entries and all(e.taken for e in entries):
            full_days.add(time_taken.date() if hasattr(time_taken, "date") else time_taken)

    return len(full_days)


# ── Main evaluator ────────────────────────────────────────────────────────────

async def evaluate_and_unlock(
    user_id: str,
    journey_id: uuid.UUID,
    db: AsyncSession,
) -> list[UserAchievement]:
    """
    Called after every successful medication log save.
    Checks all relevant metrics and unlocks newly earned achievements.
    Returns list of newly unlocked UserAchievement rows (for push notification, etc.).
    """
    # Load all achievements
    all_achievements_result = await db.execute(select(Achievement))
    all_achievements: Sequence[Achievement] = all_achievements_result.scalars().all()

    # Load existing user achievements
    existing_result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == user_id)
    )
    existing: dict[uuid.UUID, UserAchievement] = {
        ua.achievement_id: ua for ua in existing_result.scalars().all()
    }

    # Compute metrics
    current_streak, longest_streak = await _compute_streak(user_id, journey_id, db)

    total_logs_result = await db.execute(
        select(func.count(MedicationLog.id)).where(
            MedicationLog.user_id == user_id,
            MedicationLog.journey_id == journey_id,
        )
    )
    total_logs: int = total_logs_result.scalar() or 0

    full_dose_days = await _total_full_dose_days(user_id, journey_id, db)

    # Check reset count (for recovery achievements)
    journey_result = await db.execute(
        select(MedicationJourney).where(MedicationJourney.id == journey_id)
    )
    journey = journey_result.scalar_one_or_none()
    reset_count = journey.reset_count if journey else 0

    # Metric map per category
    def metric_for(achievement: Achievement) -> int:
        cat = achievement.category
        if cat == AchievementCategory.streak:
            return current_streak
        if cat == AchievementCategory.milestone:
            return total_logs
        if cat == AchievementCategory.consistency:
            return full_dose_days
        if cat == AchievementCategory.recovery:
            if achievement.key == "comeback_1":
                return reset_count
            if achievement.key == "comeback_streak_7":
                return current_streak if reset_count >= 1 else 0
        return 0

    now = datetime.now(timezone.utc)
    newly_unlocked: list[UserAchievement] = []

    for ach in all_achievements:
        current_value = metric_for(ach)
        ua = existing.get(ach.id)

        if ua is None:
            # Create progress row
            ua = UserAchievement(
                id=uuid.uuid4(),
                user_id=user_id,
                achievement_id=ach.id,
                unlocked=False,
                current_progress=current_value,
            )
            db.add(ua)
        else:
            ua.current_progress = current_value

        if not ua.unlocked and current_value >= ach.required_value:
            ua.unlocked = True
            ua.unlocked_at = now
            newly_unlocked.append(ua)

    await db.commit()

    # Reload relationships for response
    for ua in newly_unlocked:
        await db.refresh(ua, ["achievement"])

    return newly_unlocked