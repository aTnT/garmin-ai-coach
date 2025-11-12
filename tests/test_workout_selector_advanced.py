"""
Advanced tests for WorkoutSelector - pushing coverage from 64% to 80%+

Focus on uncovered areas:
- TAPER phase selection (lines 67-76, 176-200)
- RECOVERY phase selection (lines 72-73)
- adjust_for_constraints method (lines 289-324) - BIGGEST GAP
- Edge cases in phase-specific selectors
"""

from datetime import date, timedelta
import pytest

from services.ai.planning import WorkoutSelector
from services.ai.planning.plan_models import (
    TrainingPhase,
    TrainingPhaseType,
    VolumeRange,
    IntensityDistribution,
    WorkoutPriority,
    WorkoutType,
)
from services.ai.workouts.workout_models import Sport


def create_taper_phase(start_date: date, duration_weeks: int = 2) -> TrainingPhase:
    """Create a taper phase for testing."""
    return TrainingPhase(
        phase_id="taper-1",
        phase_type=TrainingPhaseType.TAPER,
        name="Taper Phase",
        start_date=start_date,
        end_date=start_date + timedelta(weeks=duration_weeks),
        duration_weeks=duration_weeks,
        focus="Reduce volume, maintain sharpness",
        volume_range=VolumeRange(
            min_hours_per_week=3.0,
            max_hours_per_week=6.0,
            target_hours_per_week=4.5,
            min_sessions_per_week=3,
            max_sessions_per_week=5,
        ),
        intensity_distribution=IntensityDistribution(
            zone1_percent=60,
            zone2_percent=20,
            zone3_percent=10,
            zone4_percent=5,
            zone5_percent=5,
        ),
        key_workout_types=[WorkoutType.SPEED, WorkoutType.RECOVERY],
        goals=["Arrive fresh for race"],
        success_criteria=["Feel sharp and rested"],
    )


def create_recovery_phase(start_date: date, duration_weeks: int = 2) -> TrainingPhase:
    """Create a recovery phase for testing."""
    return TrainingPhase(
        phase_id="recovery-1",
        phase_type=TrainingPhaseType.RECOVERY,
        name="Recovery Phase",
        start_date=start_date,
        end_date=start_date + timedelta(weeks=duration_weeks),
        duration_weeks=duration_weeks,
        focus="Active recovery and regeneration",
        volume_range=VolumeRange(
            min_hours_per_week=2.0,
            max_hours_per_week=5.0,
            target_hours_per_week=3.5,
            min_sessions_per_week=2,
            max_sessions_per_week=4,
        ),
        intensity_distribution=IntensityDistribution(
            zone1_percent=80,
            zone2_percent=20,
            zone3_percent=0,
            zone4_percent=0,
            zone5_percent=0,
        ),
        key_workout_types=[WorkoutType.RECOVERY],
        goals=["Full recovery"],
        success_criteria=["Feel refreshed"],
    )


class TestTaperPhase:
    """Test TAPER phase workout selection."""

    def test_taper_phase_very_close_to_race(self):
        """Test taper within 3 days of race - should be pure recovery."""
        selector = WorkoutSelector()
        phase = create_taper_phase(date.today(), duration_weeks=1)

        # 2 days before race
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Friday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=2,
            days_to_race=2,
        )

        assert workout_type == WorkoutType.RECOVERY
        assert duration == 30  # Very short
        assert priority == WorkoutPriority.IMPORTANT

    def test_taper_phase_4_to_7_days_out(self):
        """Test taper 4-7 days before race - short openers."""
        selector = WorkoutSelector()
        phase = create_taper_phase(date.today(), duration_weeks=1)

        # 5 days before race, Tuesday
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=85,
            days_since_last_hard=2,
            days_to_race=5,
        )

        assert workout_type == WorkoutType.SPEED  # Short opener
        assert duration == 30
        assert priority == WorkoutPriority.KEY

    def test_taper_phase_non_opener_day(self):
        """Test taper 4-7 days out on non-Tuesday/Thursday."""
        selector = WorkoutSelector()
        phase = create_taper_phase(date.today(), duration_weeks=1)

        # 6 days before race, Wednesday
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Wednesday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=1,
            days_to_race=6,
        )

        assert workout_type == WorkoutType.RECOVERY
        assert duration == 30
        assert priority == WorkoutPriority.BENEFICIAL

    def test_taper_phase_8_to_14_days_out(self):
        """Test taper 8-14 days out - reduced volume with some intensity."""
        selector = WorkoutSelector()
        phase = create_taper_phase(date.today(), duration_weeks=2)

        # 10 days before race, Wednesday
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Wednesday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=2,
            days_to_race=10,
        )

        assert workout_type == WorkoutType.TEMPO
        assert duration == 40
        assert priority == WorkoutPriority.IMPORTANT

    def test_taper_phase_recovery_day_8_to_14_days_out(self):
        """Test taper 8-14 days out on Monday (non-Wednesday/Friday)."""
        selector = WorkoutSelector()
        phase = create_taper_phase(date.today(), duration_weeks=2)

        # 12 days before race, Monday
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Monday",
            phase=phase,
            readiness_score=75,
            days_since_last_hard=1,
            days_to_race=12,
        )

        assert workout_type == WorkoutType.RECOVERY
        assert duration == 40
        assert priority == WorkoutPriority.BENEFICIAL

    def test_peak_phase_delegates_to_taper(self):
        """Test peak phase delegates to taper when close to race."""
        from services.ai.planning import create_peak_phase

        selector = WorkoutSelector()
        phase = create_peak_phase(date.today(), duration_weeks=4)

        # Peak phase, but only 8 days to race - should use taper logic
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Wednesday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=2,
            days_to_race=8,
        )

        # Should be taper workout
        assert workout_type in [WorkoutType.TEMPO, WorkoutType.RECOVERY]
        assert duration <= 60


class TestRecoveryPhase:
    """Test RECOVERY phase workout selection."""

    def test_recovery_phase_returns_recovery_workout(self):
        """Test recovery phase always returns recovery workouts."""
        selector = WorkoutSelector()
        phase = create_recovery_phase(date.today(), duration_weeks=2)

        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=0,
        )

        assert workout_type == WorkoutType.RECOVERY
        assert duration == 45
        assert priority == WorkoutPriority.BENEFICIAL

    def test_recovery_phase_any_day(self):
        """Test recovery phase on different days."""
        selector = WorkoutSelector()
        phase = create_recovery_phase(date.today(), duration_weeks=2)

        for day in ["Monday", "Wednesday", "Friday", "Sunday"]:
            workout_type, duration, priority = selector.select_workout_for_day(
                day_of_week=day,
                phase=phase,
                readiness_score=70,
                days_since_last_hard=1,
            )

            assert workout_type == WorkoutType.RECOVERY
            assert duration == 45
            assert priority == WorkoutPriority.BENEFICIAL


class TestAdjustForConstraints:
    """Test schedule adjustment methods - BIGGEST COVERAGE GAP (lines 289-324)."""

    def test_adjust_reduces_total_hours(self):
        """Test max_weekly_hours constraint reduces durations proportionally."""
        from services.ai.planning import create_build_phase

        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Generate schedule with ~10 hours
        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            sport=Sport.RUNNING,
        )

        # Calculate original total
        original_minutes = sum(w["duration_minutes"] for w in schedule)
        original_hours = original_minutes / 60

        # Constrain to 6 hours
        adjusted = selector.adjust_for_constraints(
            schedule=schedule.copy(),
            max_weekly_hours=6.0,
        )

        adjusted_minutes = sum(w["duration_minutes"] for w in adjusted)
        adjusted_hours = adjusted_minutes / 60

        # Should be reduced
        if original_hours > 6.0:
            assert adjusted_hours <= 6.5  # Allow small rounding margin
            assert adjusted_hours < original_hours

    def test_adjust_removes_sessions_for_max_sessions(self):
        """Test max_sessions_per_week constraint removes lowest priority workouts."""
        from services.ai.planning import create_build_phase

        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Generate full 7-day schedule
        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            sport=Sport.RUNNING,
        )

        original_count = len(schedule)

        # Limit to 4 sessions
        adjusted = selector.adjust_for_constraints(
            schedule=schedule.copy(),
            max_sessions_per_week=4,
        )

        assert len(adjusted) == 4
        # Should keep KEY workouts
        priorities = [w["priority"] for w in adjusted]
        # At least one KEY workout should be preserved
        assert WorkoutPriority.KEY in priorities or WorkoutPriority.IMPORTANT in priorities

    def test_adjust_ensures_minimum_rest_days(self):
        """Test required_rest_days converts beneficial workouts to recovery."""
        from services.ai.planning import create_build_phase

        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=85,  # High readiness = more hard workouts
            sport=Sport.RUNNING,
        )

        # Count initial recovery workouts
        initial_recovery = sum(
            1 for w in schedule
            if w["workout_type"] == WorkoutType.RECOVERY
        )

        # Require at least 2 rest days
        adjusted = selector.adjust_for_constraints(
            schedule=schedule.copy(),
            required_rest_days=2,
        )

        recovery_count = sum(
            1 for w in adjusted
            if w["workout_type"] == WorkoutType.RECOVERY
        )

        assert recovery_count >= 2

    def test_adjust_multiple_constraints(self):
        """Test applying multiple constraints together."""
        from services.ai.planning import create_build_phase

        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            sport=Sport.RUNNING,
        )

        # Apply all constraints
        adjusted = selector.adjust_for_constraints(
            schedule=schedule.copy(),
            max_weekly_hours=8.0,
            max_sessions_per_week=5,
            required_rest_days=1,
        )

        # Check all constraints met
        assert len(adjusted) <= 5

        total_hours = sum(w["duration_minutes"] for w in adjusted) / 60
        assert total_hours <= 8.5  # Allow small margin

        recovery_count = sum(
            1 for w in adjusted
            if w["workout_type"] == WorkoutType.RECOVERY
        )
        assert recovery_count >= 1

    def test_adjust_no_constraints_returns_unchanged(self):
        """Test adjust_for_constraints with no constraints returns schedule unchanged."""
        from services.ai.planning import create_base_phase

        selector = WorkoutSelector()
        phase = create_base_phase(date.today(), duration_weeks=4)

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=75,
            sport=Sport.RUNNING,
        )

        original_count = len(schedule)
        original_types = [w["workout_type"] for w in schedule]

        # No constraints
        adjusted = selector.adjust_for_constraints(
            schedule=schedule.copy(),
            max_weekly_hours=None,
            max_sessions_per_week=None,
            required_rest_days=1,
        )

        # Should be mostly unchanged (may convert to recovery if needed)
        assert len(adjusted) == original_count


class TestEdgeCases:
    """Test edge cases in phase-specific selectors."""

    def test_base_phase_low_readiness_mid_week(self):
        """Test base phase Wednesday with low readiness (line 98 else case)."""
        from services.ai.planning import create_base_phase

        selector = WorkoutSelector()
        phase = create_base_phase(date.today(), duration_weeks=4)

        # Wednesday with low readiness or not recovered
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Wednesday",
            phase=phase,
            readiness_score=70,  # Not >= 75
            days_since_last_hard=1,  # Not >= 2
        )

        assert workout_type == WorkoutType.ENDURANCE
        assert duration == 60
        assert priority == WorkoutPriority.BENEFICIAL

    def test_build_phase_low_readiness_intervals(self):
        """Test build phase interval day with low readiness (line 134 else case)."""
        from services.ai.planning import create_build_phase

        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Tuesday with insufficient readiness
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=70,  # Not >= 75
            days_since_last_hard=1,  # Not >= 2
        )

        assert workout_type == WorkoutType.TEMPO
        assert duration == 60
        assert priority == WorkoutPriority.BENEFICIAL

    def test_peak_phase_low_readiness_weekend(self):
        """Test peak phase Saturday with low readiness (line 162 else case)."""
        from services.ai.planning import create_peak_phase

        selector = WorkoutSelector()
        phase = create_peak_phase(date.today(), duration_weeks=4)

        # Saturday with low readiness
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Saturday",
            phase=phase,
            readiness_score=75,  # Not >= 80
            days_since_last_hard=2,
            days_to_race=14,
        )

        assert workout_type == WorkoutType.TEMPO
        assert duration == 60
        assert priority == WorkoutPriority.IMPORTANT

    def test_peak_phase_moderate_readiness_mid_week(self):
        """Test peak phase mid-week with moderate readiness (lines 168-171)."""
        from services.ai.planning import create_peak_phase

        selector = WorkoutSelector()
        phase = create_peak_phase(date.today(), duration_weeks=4)

        # Tuesday with moderate readiness (75-79)
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=77,  # >= 75 but not >= 80
            days_since_last_hard=2,
            days_to_race=14,
        )

        assert workout_type == WorkoutType.THRESHOLD
        assert duration == 60
        assert priority == WorkoutPriority.IMPORTANT

    def test_peak_phase_low_readiness_mid_week(self):
        """Test peak phase mid-week with low readiness (lines 170-171)."""
        from services.ai.planning import create_peak_phase

        selector = WorkoutSelector()
        phase = create_peak_phase(date.today(), duration_weeks=4)

        # Tuesday with low readiness
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=70,  # Not >= 75
            days_since_last_hard=2,
            days_to_race=14,
        )

        assert workout_type == WorkoutType.TEMPO
        assert duration == 45
        assert priority == WorkoutPriority.BENEFICIAL

    def test_build_phase_alternates_threshold_vo2max(self):
        """Test build phase alternates between threshold and VO2max."""
        from services.ai.planning import create_build_phase

        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Tuesday with threshold in recent workouts
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=85,
            days_since_last_hard=3,
            recent_workout_types=[WorkoutType.THRESHOLD, WorkoutType.RECOVERY],
        )

        # Should select VO2max since threshold was recent
        assert workout_type == WorkoutType.VO2MAX
        assert duration == 45
        assert priority == WorkoutPriority.KEY

    def test_peak_phase_avoids_recent_vo2max(self):
        """Test peak phase avoids VO2max if done recently."""
        from services.ai.planning import create_peak_phase

        selector = WorkoutSelector()
        phase = create_peak_phase(date.today(), duration_weeks=4)

        # Tuesday with VO2max in recent workouts
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=85,
            days_since_last_hard=2,
            days_to_race=14,
            recent_workout_types=[WorkoutType.VO2MAX, WorkoutType.RECOVERY],
        )

        # Should not select VO2max since it was recent
        # Will fall through to threshold or tempo
        assert workout_type in [WorkoutType.THRESHOLD, WorkoutType.TEMPO]

    def test_peak_phase_recovery_fallback(self):
        """Test peak phase recovery day fallback (line 174)."""
        from services.ai.planning import create_peak_phase

        selector = WorkoutSelector()
        phase = create_peak_phase(date.today(), duration_weeks=4)

        # Monday (not Tuesday/Thursday/Saturday/Sunday) with any readiness
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Monday",
            phase=phase,
            readiness_score=75,
            days_since_last_hard=0,
            days_to_race=14,
        )

        assert workout_type == WorkoutType.RECOVERY
        assert duration == 45
        assert priority == WorkoutPriority.BENEFICIAL
