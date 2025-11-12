"""
Comprehensive tests for WorkoutSelector.
"""

from datetime import date, timedelta
import pytest

from services.ai.planning import WorkoutSelector, create_base_phase, create_build_phase, create_peak_phase
from services.ai.workouts.workout_models import WorkoutType, Sport
from services.ai.planning.plan_models import WorkoutPriority


class TestWorkoutSelection:
    """Test workout selection logic."""

    def test_base_phase_emphasizes_endurance(self):
        """Test base phase focuses on endurance work."""
        selector = WorkoutSelector()
        phase = create_base_phase(date.today(), duration_weeks=4)

        # Saturday in base phase should favor long endurance
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Saturday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=2,
        )

        assert workout_type in [WorkoutType.ENDURANCE, WorkoutType.LONG_ENDURANCE]
        assert duration >= 90  # Long workout

    def test_build_phase_includes_intervals(self):
        """Test build phase includes threshold/VO2max work."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Tuesday in build phase should favor intervals
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=85,
            days_since_last_hard=2,
        )

        assert workout_type in [
            WorkoutType.THRESHOLD,
            WorkoutType.VO2MAX,
            WorkoutType.TEMPO,
        ]

    def test_peak_phase_race_specific(self):
        """Test peak phase includes race-specific workouts."""
        selector = WorkoutSelector()
        phase = create_peak_phase(date.today(), duration_weeks=2)

        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Wednesday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=1,
            days_to_race=10,
        )

        # Should include race-specific intensity
        assert workout_type in [
            WorkoutType.THRESHOLD,
            WorkoutType.TEMPO,
            WorkoutType.VO2MAX,
            WorkoutType.SPEED,
        ]

    def test_low_readiness_forces_recovery(self):
        """Test low readiness overrides planned hard workout."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Tuesday with low readiness
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=45,  # Low
            days_since_last_hard=1,
        )

        # Should force recovery
        assert workout_type == WorkoutType.RECOVERY
        assert duration <= 60

    def test_high_readiness_allows_hard_workout(self):
        """Test high readiness allows planned intensity."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=90,  # High
            days_since_last_hard=2,
        )

        # Should allow hard workout
        assert workout_type in [
            WorkoutType.THRESHOLD,
            WorkoutType.VO2MAX,
            WorkoutType.TEMPO,
        ]

    def test_rest_day_selection(self):
        """Test rest days are included appropriately."""
        selector = WorkoutSelector()
        phase = create_base_phase(date.today(), duration_weeks=4)

        # Monday might be rest/easy day
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Monday",
            phase=phase,
            readiness_score=70,
            days_since_last_hard=0,  # Hard workout yesterday
        )

        # Should be recovery or easy
        assert workout_type in [WorkoutType.RECOVERY, WorkoutType.ENDURANCE]
        if workout_type == WorkoutType.RECOVERY:
            assert priority in [WorkoutPriority.BENEFICIAL, WorkoutPriority.OPTIONAL]

    def test_spacing_between_hard_workouts(self):
        """Test system respects recovery between hard efforts."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Just did hard workout yesterday
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Wednesday",
            phase=phase,
            readiness_score=75,
            days_since_last_hard=0,  # Yesterday was hard
        )

        # Should be easier workout
        assert workout_type in [
            WorkoutType.RECOVERY,
            WorkoutType.ENDURANCE,
            WorkoutType.TEMPO,
        ]

    def test_weekly_schedule_generation(self):
        """Test generating complete weekly schedule."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=75,
            available_days=["Monday", "Tuesday", "Thursday", "Saturday", "Sunday"],
            sport=Sport.RUNNING,
        )

        assert len(schedule) == 5  # 5 training days
        assert all("date" in day for day in schedule)
        assert all("workout_type" in day for day in schedule)
        assert all("duration_minutes" in day for day in schedule)
        assert all("priority" in day for day in schedule)

    def test_weekly_schedule_respects_available_days(self):
        """Test weekly schedule only uses specified days."""
        selector = WorkoutSelector()
        phase = create_base_phase(date.today(), duration_weeks=4)

        # Only 3 days available
        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            available_days=["Tuesday", "Thursday", "Saturday"],
            sport=Sport.RUNNING,
        )

        assert len(schedule) == 3
        days_of_week = [day["date"].strftime("%A") for day in schedule]
        assert all(d in ["Tuesday", "Thursday", "Saturday"] for d in days_of_week)

    def test_weekly_schedule_includes_key_workouts(self):
        """Test weekly schedule includes key/important workouts."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            available_days=["Tuesday", "Wednesday", "Thursday", "Saturday", "Sunday"],
            sport=Sport.RUNNING,
        )

        # Should have at least one KEY workout
        priorities = [day["priority"] for day in schedule]
        assert WorkoutPriority.KEY in priorities

    def test_duration_scales_with_phase(self):
        """Test workout duration appropriate for phase."""
        selector = WorkoutSelector()
        base_phase = create_base_phase(date.today(), duration_weeks=4)

        # Long workout in base phase
        _, base_duration, _ = selector.select_workout_for_day(
            day_of_week="Saturday",
            phase=base_phase,
            readiness_score=80,
            days_since_last_hard=2,
        )

        # Should be long endurance
        assert base_duration >= 90

    def test_intensity_distribution_matches_phase(self):
        """Test intensity distribution aligns with phase goals."""
        selector = WorkoutSelector()
        phase = create_base_phase(date.today(), duration_weeks=4)

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            sport=Sport.RUNNING,
        )

        # Base phase should be mostly endurance/recovery
        workout_types = [day["workout_type"] for day in schedule]
        endurance_recovery_count = sum(
            1
            for wt in workout_types
            if wt in [WorkoutType.ENDURANCE, WorkoutType.RECOVERY]
        )

        # At least 60% should be endurance/recovery in base phase
        assert endurance_recovery_count / len(schedule) >= 0.6

    def test_race_proximity_affects_selection(self):
        """Test workout selection changes near race date."""
        selector = WorkoutSelector()
        phase = create_peak_phase(date.today(), duration_weeks=2)

        # Very close to race
        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=2,
            days_to_race=5,  # 5 days to race
        )

        # Should be easier/shorter as race approaches
        assert duration <= 60

    def test_progressive_overload_in_build(self):
        """Test build phase increases load appropriately."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Week 1 workout
        week1_schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            sport=Sport.RUNNING,
        )

        # All schedules should have reasonable durations
        for day in week1_schedule:
            assert 30 <= day["duration_minutes"] <= 180


class TestWorkoutPrioritization:
    """Test workout priority assignment."""

    def test_key_workouts_properly_marked(self):
        """Test key workouts receive KEY priority."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        # Long run on weekend should be key
        _, _, priority = selector.select_workout_for_day(
            day_of_week="Saturday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=2,
        )

        assert priority in [WorkoutPriority.KEY, WorkoutPriority.IMPORTANT]

    def test_recovery_workouts_lower_priority(self):
        """Test recovery workouts have appropriate priority."""
        selector = WorkoutSelector()
        phase = create_base_phase(date.today(), duration_weeks=4)

        workout_type, _, priority = selector.select_workout_for_day(
            day_of_week="Monday",
            phase=phase,
            readiness_score=60,
            days_since_last_hard=0,
        )

        if workout_type == WorkoutType.RECOVERY:
            assert priority in [
                WorkoutPriority.BENEFICIAL,
                WorkoutPriority.OPTIONAL,
            ]


class TestSportSpecificSelection:
    """Test sport-specific workout selection."""

    def test_running_workout_selection(self):
        """Test running-specific workout generation."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            sport=Sport.RUNNING,
        )

        # Should generate valid running workouts
        assert len(schedule) > 0
        for day in schedule:
            assert day["workout_type"] in [
                WorkoutType.RECOVERY,
                WorkoutType.ENDURANCE,
                WorkoutType.TEMPO,
                WorkoutType.THRESHOLD,
                WorkoutType.VO2MAX,
                WorkoutType.SPEED,
            ]

    def test_cycling_workout_selection(self):
        """Test cycling-specific workout generation."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today(), duration_weeks=8)

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today(),
            average_readiness=80,
            sport=Sport.CYCLING,
        )

        # Should generate valid cycling workouts
        assert len(schedule) > 0
        # Cycling workouts might be longer
        durations = [day["duration_minutes"] for day in schedule]
        assert any(d >= 90 for d in durations)
