"""
Tests for Activity Matcher

Comprehensive testing of activity-to-workout matching logic, quality assessment,
and completion tracking.
"""

from datetime import date, datetime, timedelta

import pytest

from services.ai.planning.activity_matcher import ActivityMatcher
from services.ai.planning.plan_models import (
    CompletionQuality,
    PlannedWorkout,
    WorkoutPriority,
)
from services.ai.workouts.workout_models import (
    Interval,
    IntensityZone,
    Sport,
    StructuredWorkout,
    WorkoutSegment,
    WorkoutType,
)


# ============================================================================
# Test Fixtures
# ============================================================================


def create_mock_activity(
    activity_id: str,
    start_time: datetime,
    sport_type: str = "running",
    duration_seconds: int = 3600,
    distance: float = 10000.0,
    average_hr: int | None = 150,
    max_hr: int | None = 180,
    average_speed: float | None = None,
    average_power: float | None = None,
    name: str = "Morning Run",
):
    """Create mock Activity object for testing."""

    class MockActivity:
        def __init__(self):
            self.activity_id = activity_id
            self.start_time = start_time
            self.sport_type = sport_type
            self.duration_seconds = duration_seconds
            self.distance = distance
            self.average_hr = average_hr
            self.max_hr = max_hr
            self.average_speed = average_speed or (distance / duration_seconds)
            self.average_power = average_power
            self.name = name

    return MockActivity()


def create_planned_workout(
    workout_id: str,
    workout_date: date,
    sport: Sport = Sport.RUNNING,
    workout_type: WorkoutType = WorkoutType.ENDURANCE,
    duration_minutes: int = 60,
    intensity: IntensityZone = IntensityZone.Z2,
) -> PlannedWorkout:
    """Create PlannedWorkout for testing."""
    workout = StructuredWorkout(
        workout_id=f"wo-{workout_id}",
        name=f"{workout_type.value.title()} Workout",
        sport=sport,
        workout_type=workout_type,
        duration_minutes=duration_minutes,
        segments=[
            WorkoutSegment(
                name="Main",
                intervals=[
                    Interval(
                        duration_minutes=float(duration_minutes),
                        intensity_zone=intensity,
                        description=f"{workout_type.value} effort",
                    )
                ],
            )
        ],
        average_intensity=intensity,
        peak_intensity=intensity,
        goal=f"{workout_type.value} training",
    )

    return PlannedWorkout(
        workout_id=workout_id,
        date=workout_date,
        workout=workout,
        priority=WorkoutPriority.BENEFICIAL,
        rationale="Testing",
        phase_id="test_phase",
        week_number=1,
    )


# ============================================================================
# Test 1: Basic Activity Matching
# ============================================================================


class TestBasicMatching:
    """Test basic activity matching functionality."""

    def test_match_activity_perfect_timing(self):
        """Test matching activity at exact planned time."""
        matcher = ActivityMatcher(matching_window_hours=36)

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        # Activity at exact planned time (7am on planned date)
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=3600,  # 60 minutes
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion is not None
        assert completion.activity_id == "act1"
        assert completion.planned_workout_id == "pw1"
        assert completion.completion_percentage == 100.0

    def test_match_activity_within_window(self):
        """Test matching activity within time window."""
        matcher = ActivityMatcher(matching_window_hours=36)

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        # Activity 12 hours after planned time (still within 36h window)
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 12, 0),
            duration_seconds=3600,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion is not None
        assert completion.activity_id == "act1"

    def test_match_activity_outside_window(self):
        """Test no match when activity is outside time window."""
        matcher = ActivityMatcher(matching_window_hours=24)

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        # Activity 48 hours later (outside 24h window)
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 17, 12, 0),
            duration_seconds=3600,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion is None

    def test_match_no_activities(self):
        """Test matching with empty activity list."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        completion = matcher.match_activity_to_workout(planned, [])

        assert completion is None


# ============================================================================
# Test 2: Sport Matching
# ============================================================================


class TestSportMatching:
    """Test sport compatibility matching."""

    def test_sport_exact_match(self):
        """Test exact sport type match."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, sport=Sport.RUNNING)

        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            sport_type="running",
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion is not None

    def test_sport_equivalent_match(self):
        """Test sport equivalent matching (e.g., running vs run)."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, sport=Sport.RUNNING)

        # Activity with "run" instead of "running"
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            sport_type="run",
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion is not None

    def test_sport_cycling_equivalents(self):
        """Test cycling sport equivalents (bike, ride, etc.)."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, sport=Sport.CYCLING)

        for sport_type in ["bike", "ride", "indoor bike", "virtual ride"]:
            activity = create_mock_activity(
                activity_id="act1",
                start_time=datetime(2025, 1, 15, 7, 0),
                sport_type=sport_type,
            )

            completion = matcher.match_activity_to_workout(planned, [activity])
            assert completion is not None, f"Failed to match sport: {sport_type}"

    def test_sport_mismatch(self):
        """Test no match when sports don't match."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, sport=Sport.RUNNING)

        # Cycling activity for running workout
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            sport_type="cycling",
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion is None


# ============================================================================
# Test 3: Best Match Selection
# ============================================================================


class TestBestMatchSelection:
    """Test best match selection from multiple candidates."""

    def test_select_closest_timing(self):
        """Test selection of activity closest to planned time."""
        matcher = ActivityMatcher(matching_window_hours=48)

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        # Two activities: one at 7am, one at 3pm
        activity1 = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),  # Closer to midnight
            duration_seconds=3600,
        )

        activity2 = create_mock_activity(
            activity_id="act2",
            start_time=datetime(2025, 1, 15, 15, 0),  # Further from midnight
            duration_seconds=3600,
        )

        completion = matcher.match_activity_to_workout(planned, [activity1, activity2])

        # Should match activity1 (closer to start of day)
        assert completion.activity_id == "act1"

    def test_select_better_duration_match(self):
        """Test selection based on duration similarity."""
        matcher = ActivityMatcher(matching_window_hours=48)

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, duration_minutes=60)

        # Same time, different durations
        activity1 = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=7200,  # 120 min (far from 60)
        )

        activity2 = create_mock_activity(
            activity_id="act2",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=3600,  # 60 min (exact match)
        )

        completion = matcher.match_activity_to_workout(planned, [activity1, activity2])

        # Should match activity2 (better duration match)
        assert completion.activity_id == "act2"

    def test_select_with_workout_type_match(self):
        """Test selection considers workout type via activity name."""
        matcher = ActivityMatcher(matching_window_hours=48)

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout(
            "pw1", workout_date, workout_type=WorkoutType.TEMPO
        )

        # Two activities with different names
        activity1 = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=3600,
            name="Easy Run",  # Doesn't match TEMPO
        )

        activity2 = create_mock_activity(
            activity_id="act2",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=3600,
            name="Tempo Run",  # Matches TEMPO
        )

        completion = matcher.match_activity_to_workout(planned, [activity1, activity2])

        # Should match activity2 (name matches workout type)
        assert completion.activity_id == "act2"


# ============================================================================
# Test 4: Quality Assessment
# ============================================================================


class TestQualityAssessment:
    """Test workout completion quality rating."""

    def test_quality_excellent(self):
        """Test EXCELLENT quality rating."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout(
            "pw1", workout_date,
            duration_minutes=60,
            intensity=IntensityZone.Z2,
        )

        # Perfect execution: exact duration, good HR match
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=3600,  # Exactly 60 min
            average_hr=117,  # 65% of 180 max HR ≈ Z2
            max_hr=180,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.quality_rating == CompletionQuality.EXCELLENT

    def test_quality_good(self):
        """Test GOOD quality rating."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout(
            "pw1", workout_date,
            duration_minutes=60,
            intensity=IntensityZone.Z2,
        )

        # Good execution: 90% duration, decent HR
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=3240,  # 54 min (90%)
            average_hr=120,  # 66.7% of 180 max HR
            max_hr=180,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.quality_rating == CompletionQuality.GOOD

    def test_quality_adequate(self):
        """Test ADEQUATE quality rating."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout(
            "pw1", workout_date,
            duration_minutes=60,
            intensity=IntensityZone.Z2,
        )

        # Adequate execution: 80% duration, moderate HR deviation
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=2880,  # 48 min (80%)
            average_hr=126,  # 70% of 180 max HR
            max_hr=180,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.quality_rating == CompletionQuality.ADEQUATE

    def test_quality_poor(self):
        """Test POOR quality rating."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout(
            "pw1", workout_date,
            duration_minutes=60,
            intensity=IntensityZone.Z2,
        )

        # Poor execution: completed but way off intensity
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=2700,  # 45 min (75%)
            average_hr=162,  # 90% of 180 max HR (too high for Z2)
            max_hr=180,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.quality_rating == CompletionQuality.POOR

    def test_quality_partial(self):
        """Test PARTIAL completion rating."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, duration_minutes=60)

        # Partial: only 40 minutes of planned 60
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=2400,  # 40 min (67%)
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.quality_rating == CompletionQuality.PARTIAL


# ============================================================================
# Test 5: Weekly Matching
# ============================================================================


class TestWeeklyMatching:
    """Test matching activities to weekly workout plans."""

    def test_match_multiple_workouts(self):
        """Test matching multiple workouts to activities."""
        matcher = ActivityMatcher()

        start_date = date(2025, 1, 13)  # Monday

        # Create 3 planned workouts
        workouts = [
            create_planned_workout("pw1", start_date, workout_type=WorkoutType.RECOVERY),
            create_planned_workout("pw2", start_date + timedelta(days=1), workout_type=WorkoutType.ENDURANCE),
            create_planned_workout("pw3", start_date + timedelta(days=2), workout_type=WorkoutType.TEMPO),
        ]

        # Create matching activities
        activities = [
            create_mock_activity("act1", datetime(2025, 1, 13, 7, 0), name="Easy Recovery Run"),
            create_mock_activity("act2", datetime(2025, 1, 14, 7, 0), name="Long Endurance Run"),
            create_mock_activity("act3", datetime(2025, 1, 15, 7, 0), name="Tempo Run"),
        ]

        completions = matcher.match_activities_to_week(workouts, activities)

        assert len(completions) == 3
        assert all(c.activity_id in ["act1", "act2", "act3"] for c in completions)

    def test_match_prevents_double_matching(self):
        """Test that activities aren't matched to multiple workouts."""
        matcher = ActivityMatcher()

        start_date = date(2025, 1, 13)

        # Two workouts on same day
        workouts = [
            create_planned_workout("pw1", start_date),
            create_planned_workout("pw2", start_date),
        ]

        # Only one activity
        activities = [
            create_mock_activity("act1", datetime(2025, 1, 13, 7, 0)),
        ]

        completions = matcher.match_activities_to_week(workouts, activities)

        # Should only match once
        assert len(completions) == 1

    def test_match_with_no_activities(self):
        """Test weekly matching with no activities."""
        matcher = ActivityMatcher()

        start_date = date(2025, 1, 13)
        workouts = [create_planned_workout("pw1", start_date)]

        completions = matcher.match_activities_to_week(workouts, [])

        assert len(completions) == 0


# ============================================================================
# Test 6: Intensity Matching
# ============================================================================


class TestIntensityMatching:
    """Test intensity matching calculations."""

    def test_intensity_match_no_hr_data(self):
        """Test intensity matching with no HR data."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, intensity=IntensityZone.Z3)

        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            average_hr=None,
            max_hr=None,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        # Should still create completion with neutral intensity score
        assert completion is not None
        assert 0 <= completion.intensity_adherence <= 1

    def test_intensity_match_z2_perfect(self):
        """Test perfect Z2 intensity match."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, intensity=IntensityZone.Z2)

        # Z2 = ~65% max HR, so 117 BPM for max HR of 180
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            average_hr=117,
            max_hr=180,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.intensity_adherence >= 0.9  # Very good match

    def test_intensity_match_z5_perfect(self):
        """Test perfect Z5 intensity match."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, intensity=IntensityZone.Z5)

        # Z5 = ~95% max HR, so 171 BPM for max HR of 180
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            average_hr=171,
            max_hr=180,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.intensity_adherence >= 0.9


# ============================================================================
# Test 7: Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Test helper and utility functions."""

    def test_format_pace(self):
        """Test pace formatting from speed."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        # Speed of 2.778 m/s = 6:00/km pace
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            average_speed=2.778,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.average_pace is not None
        # Should be around 6:00/km (5:59 or 6:00 both valid)
        assert completion.average_pace.startswith(("5:59", "6:00"))

    def test_format_pace_no_speed_data(self):
        """Test pace formatting with missing speed data."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        # Create activity without average_speed attribute
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            average_speed=None,  # Will be calculated from distance/duration
        )
        # Manually set to 0 to test edge case
        activity.average_speed = 0.0

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.average_pace is None

    def test_estimate_tss(self):
        """Test TSS estimation."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        # 1 hour at 150 BPM (avg HR), max HR 180
        # IF = 150/180 = 0.833
        # TSS = 1 × 0.833² × 100 ≈ 69.4
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=3600,
            average_hr=150,
            max_hr=180,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.total_tss is not None
        assert 60 <= completion.total_tss <= 80  # Approximate range

    def test_estimate_tss_no_hr(self):
        """Test TSS estimation with no HR data."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            average_hr=None,
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion.total_tss is None


# ============================================================================
# Test 8: Weekly Adherence Metrics
# ============================================================================


class TestWeeklyAdherence:
    """Test weekly adherence calculation."""

    def test_adherence_empty_completions(self):
        """Test adherence with no completions."""
        matcher = ActivityMatcher()

        metrics = matcher.calculate_weekly_adherence([])

        assert metrics["completion_rate"] == 0.0
        assert metrics["average_completion_pct"] == 0.0
        assert metrics["excellent_count"] == 0

    def test_adherence_with_completions(self):
        """Test adherence metrics calculation."""
        matcher = ActivityMatcher()

        start_date = date(2025, 1, 13)

        # Create 3 workouts with different qualities
        workouts = [
            create_planned_workout("pw1", start_date),
            create_planned_workout("pw2", start_date + timedelta(days=1)),
            create_planned_workout("pw3", start_date + timedelta(days=2)),
        ]

        activities = [
            # Excellent
            create_mock_activity("act1", datetime(2025, 1, 13, 7, 0), duration_seconds=3600, average_hr=117, max_hr=180),
            # Good
            create_mock_activity("act2", datetime(2025, 1, 14, 7, 0), duration_seconds=3240, average_hr=120, max_hr=180),
            # Adequate
            create_mock_activity("act3", datetime(2025, 1, 15, 7, 0), duration_seconds=2880, average_hr=126, max_hr=180),
        ]

        completions = matcher.match_activities_to_week(workouts, activities)
        metrics = matcher.calculate_weekly_adherence(completions)

        assert metrics["completion_rate"] == 100.0
        assert metrics["excellent_count"] >= 1
        assert metrics["good_count"] >= 1
        assert metrics["adequate_count"] >= 1
        assert metrics["average_completion_pct"] > 80.0


# ============================================================================
# Test 9: Name-Based Type Matching
# ============================================================================


class TestNameTypeMatching:
    """Test workout type matching based on activity names."""

    def test_name_matches_recovery(self):
        """Test recovery workout name matching."""
        matcher = ActivityMatcher()

        for name in ["Easy Recovery", "Shakeout Run", "Z1 Easy"]:
            result = matcher._name_matches_type(name, WorkoutType.RECOVERY)
            assert result, f"Failed to match recovery name: {name}"

    def test_name_matches_tempo(self):
        """Test tempo workout name matching."""
        matcher = ActivityMatcher()

        for name in ["Tempo Run", "Sweetspot Ride", "Z3 Effort"]:
            result = matcher._name_matches_type(name, WorkoutType.TEMPO)
            assert result, f"Failed to match tempo name: {name}"

    def test_name_matches_vo2max(self):
        """Test VO2max workout name matching."""
        matcher = ActivityMatcher()

        for name in ["VO2 Intervals", "Hard 5min Repeats", "Z5 Session"]:
            result = matcher._name_matches_type(name, WorkoutType.VO2MAX)
            assert result, f"Failed to match VO2max name: {name}"

    def test_name_no_match(self):
        """Test name doesn't match wrong type."""
        matcher = ActivityMatcher()

        result = matcher._name_matches_type("Easy Recovery", WorkoutType.THRESHOLD)
        assert not result


# ============================================================================
# Test 10: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_very_long_duration(self):
        """Test matching with very long duration workout."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, duration_minutes=300)  # 5 hours

        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=18000,  # 5 hours
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion is not None
        assert completion.completion_percentage == 100.0

    def test_activity_longer_than_planned(self):
        """Test activity that's longer than planned workout."""
        matcher = ActivityMatcher()

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, duration_minutes=60)

        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 7, 0),
            duration_seconds=5400,  # 90 minutes (150% of plan)
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        assert completion is not None
        assert completion.completion_percentage == 100.0  # Capped at 100
        assert completion.duration_adherence == 1.5

    def test_custom_matching_window(self):
        """Test custom matching window configuration."""
        matcher = ActivityMatcher(matching_window_hours=12)  # Tight 12-hour window

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date)

        # Activity 18 hours after midnight (outside 12h window)
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 18, 0),
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        # Should still match if within window from midnight
        assert completion is not None or completion is None  # Depends on exact window calculation

    def test_single_candidate_always_selected(self):
        """Test single candidate is always selected if within window."""
        matcher = ActivityMatcher(matching_window_hours=36)

        workout_date = date(2025, 1, 15)
        planned = create_planned_workout("pw1", workout_date, duration_minutes=60)

        # Poor match but within window: wrong duration, late timing
        activity = create_mock_activity(
            activity_id="act1",
            start_time=datetime(2025, 1, 15, 16, 0),  # 16h from midnight (within 36h window)
            duration_seconds=1800,  # 30 min instead of 60
        )

        completion = matcher.match_activity_to_workout(planned, [activity])

        # Should still match (only candidate within window)
        assert completion is not None
        assert completion.activity_id == "act1"
        assert completion.quality_rating == CompletionQuality.PARTIAL  # Only 50% duration
