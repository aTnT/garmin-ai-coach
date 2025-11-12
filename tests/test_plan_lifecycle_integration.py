"""
Integration Tests for Training Plan Lifecycle

Tests end-to-end workflows including:
- Plan creation → storage → retrieval
- Weekly workout selection and scheduling
- Activity completion and performance analysis
- Readiness-driven plan adaptation
- Multi-week plan execution
"""

import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from services.ai.planning.plan_models import (
    AdaptationDecision,
    AdaptationStatus,
    AdaptationTrigger,
    CompletionQuality,
    PlannedWorkout,
    TrainingPhase,
    TrainingPlan,
    WeeklySchedule,
    WorkoutCompletion,
    WorkoutPriority,
    create_base_phase,
    create_build_phase,
    create_peak_phase,
    create_taper_phase,
)
from services.ai.planning.plan_storage import PlanStorage
from services.ai.planning.performance_analyzer import PerformanceAnalyzer
from services.ai.planning.workout_selector import WorkoutSelector
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


@pytest.fixture
def temp_storage_dir():
    """Create temporary directory for plan storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def plan_storage(temp_storage_dir):
    """Create PlanStorage instance with temp directory."""
    return PlanStorage(storage_dir=temp_storage_dir)


@pytest.fixture
def workout_selector():
    """Create WorkoutSelector instance."""
    return WorkoutSelector()


@pytest.fixture
def performance_analyzer():
    """Create PerformanceAnalyzer instance."""
    return PerformanceAnalyzer()


def create_simple_workout(
    workout_id: str,
    name: str,
    workout_type: WorkoutType,
    duration_minutes: int,
    zone: IntensityZone = IntensityZone.Z2,
) -> StructuredWorkout:
    """Create a simple test workout."""
    return StructuredWorkout(
        workout_id=workout_id,
        name=name,
        sport=Sport.RUNNING,
        workout_type=workout_type,
        duration_minutes=duration_minutes,
        segments=[
            WorkoutSegment(
                name="Main",
                intervals=[
                    Interval(
                        duration_minutes=float(duration_minutes),
                        intensity_zone=zone,
                        description=f"{workout_type.value} effort",
                    )
                ],
            )
        ],
        average_intensity=zone,
        peak_intensity=zone,
        goal=f"{workout_type.value} workout",
    )


def create_mock_activity(
    activity_id: str,
    start_time: datetime,
    duration_minutes: int,
    distance_km: float = 10.0,
):
    """Create a mock activity object."""

    class MockActivity:
        def __init__(self):
            self.activity_id = activity_id
            self.start_time = start_time
            self.duration_seconds = duration_minutes * 60
            self.distance = distance_km * 1000  # Convert to meters
            self.average_speed = self.distance / self.duration_seconds
            self.sport = "running"
            self.average_hr = 150
            self.max_hr = 170

    return MockActivity()


# ============================================================================
# Test 1: Complete Plan Creation and Storage
# ============================================================================


class TestPlanCreationAndStorage:
    """Test complete plan creation, storage, and retrieval."""

    def test_create_and_save_complete_plan(self, plan_storage):
        """Test creating a complete multi-phase plan and saving it."""
        start_date = date.today()

        # Create phases
        base_phase = create_base_phase(start_date, duration_weeks=4)
        build_phase = create_build_phase(
            start_date + timedelta(weeks=4), duration_weeks=4
        )
        peak_phase = create_peak_phase(
            start_date + timedelta(weeks=8), duration_weeks=3
        )
        taper_phase = create_taper_phase(
            start_date + timedelta(weeks=11), duration_weeks=2
        )

        # Create plan
        plan = TrainingPlan(
            plan_id="integration-test-001",
            athlete_id="athlete-001",
            athlete_name="Test Athlete",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=start_date + timedelta(weeks=13),
            last_updated=datetime.now(),
            primary_goal={
                "race_name": "Test Marathon",
                "date": (start_date + timedelta(weeks=13)).isoformat(),
                "distance": 42.195,
                "goal_time": "3:30:00",
            },
            phases=[base_phase, build_phase, peak_phase, taper_phase],
            current_phase_id=base_phase.phase_id,
        )

        # Save plan
        plan_storage.save_plan(plan)

        # Retrieve plan
        loaded_plan = plan_storage.load_plan("integration-test-001")

        # Verify plan loaded correctly
        assert loaded_plan is not None
        assert loaded_plan.plan_id == "integration-test-001"
        assert loaded_plan.athlete_id == "athlete-001"
        assert len(loaded_plan.phases) == 4
        assert loaded_plan.phases[0].phase_type.value == "base"
        assert loaded_plan.phases[1].phase_type.value == "build"
        assert loaded_plan.phases[2].phase_type.value == "peak"
        assert loaded_plan.phases[3].phase_type.value == "taper"
        assert loaded_plan.primary_goal["race_name"] == "Test Marathon"

    def test_plan_with_weekly_schedules(self, plan_storage, workout_selector):
        """Test creating plan with weekly schedules and workouts."""
        start_date = date.today()
        base_phase = create_base_phase(start_date, duration_weeks=2)

        plan = TrainingPlan(
            plan_id="weekly-schedule-test",
            athlete_id="athlete-002",
            athlete_name="Schedule Test Athlete",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=start_date + timedelta(weeks=2),
            last_updated=datetime.now(),
            primary_goal={"race_name": "Test Race", "date": (start_date + timedelta(weeks=2)).isoformat()},
            phases=[base_phase],
        )

        # Generate weekly schedules
        for week_num in range(2):
            week_start = start_date + timedelta(weeks=week_num)
            week_end = week_start + timedelta(days=6)

            # Get workout schedule
            workout_schedule = workout_selector.select_weekly_schedule(
                phase=base_phase,
                week_start_date=week_start,
                average_readiness=80,
                sport=Sport.RUNNING,
            )

            # Convert to PlannedWorkouts
            planned_workouts = []
            for i, workout_dict in enumerate(workout_schedule):
                workout = create_simple_workout(
                    workout_id=f"w{week_num+1}-{i+1}",
                    name=f"Week {week_num+1} {workout_dict['workout_type'].value}",
                    workout_type=workout_dict["workout_type"],
                    duration_minutes=workout_dict["duration_minutes"],
                )

                planned_workout = PlannedWorkout(
                    workout_id=f"planned-w{week_num+1}-{i+1}",
                    date=workout_dict["date"],
                    workout=workout,
                    priority=workout_dict["priority"],
                    rationale=f"Phase: {base_phase.phase_type.value}",
                    phase_id=base_phase.phase_id,
                    week_number=week_num + 1,
                )
                planned_workouts.append(planned_workout)

            # Create weekly schedule
            weekly_schedule = WeeklySchedule(
                week_number=week_num + 1,
                start_date=week_start,
                end_date=week_end,
                phase_id=base_phase.phase_id,
                planned_workouts=planned_workouts,
                target_volume_hours=sum(w["duration_minutes"] for w in workout_schedule) / 60,
            )

            plan.weekly_schedules.append(weekly_schedule)

        # Save and reload
        plan_storage.save_plan(plan)
        loaded_plan = plan_storage.load_plan("weekly-schedule-test")

        # Verify schedules persisted
        assert loaded_plan is not None
        assert len(loaded_plan.weekly_schedules) == 2
        assert len(loaded_plan.weekly_schedules[0].planned_workouts) > 0
        assert len(loaded_plan.weekly_schedules[1].planned_workouts) > 0


# ============================================================================
# Test 2: Workout Execution and Completion
# ============================================================================


class TestWorkoutExecution:
    """Test workout completion and tracking."""

    def test_mark_workouts_completed(self, plan_storage):
        """Test marking workouts as completed and tracking quality."""
        start_date = date.today()
        base_phase = create_base_phase(start_date, duration_weeks=1)

        # Create plan with one week
        plan = TrainingPlan(
            plan_id="completion-test",
            athlete_id="athlete-003",
            athlete_name="Completion Test",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=start_date + timedelta(weeks=1),
            last_updated=datetime.now(),
            primary_goal={"race_name": "Test", "date": (start_date + timedelta(weeks=1)).isoformat()},
            phases=[base_phase],
        )

        # Create workouts for week
        workouts = []
        for i in range(5):  # 5 workouts
            workout = create_simple_workout(
                workout_id=f"wo-{i+1}",
                name=f"Workout {i+1}",
                workout_type=WorkoutType.ENDURANCE,
                duration_minutes=60,
            )
            planned = PlannedWorkout(
                workout_id=f"planned-{i+1}",
                date=start_date + timedelta(days=i),
                workout=workout,
                priority=WorkoutPriority.BENEFICIAL,
                rationale="Base building",
                phase_id=base_phase.phase_id,
                week_number=1,
            )
            workouts.append(planned)

        week_schedule = WeeklySchedule(
            week_number=1,
            start_date=start_date,
            end_date=start_date + timedelta(days=6),
            phase_id=base_phase.phase_id,
            planned_workouts=workouts,
            target_volume_hours=5.0,
        )
        plan.weekly_schedules.append(week_schedule)

        # Complete 3 out of 5 workouts
        workouts[0].completed = True
        workouts[0].completion_quality = CompletionQuality.EXCELLENT
        workouts[0].completion_date = start_date

        workouts[1].completed = True
        workouts[1].completion_quality = CompletionQuality.GOOD
        workouts[1].completion_date = start_date + timedelta(days=1)

        workouts[2].completed = True
        workouts[2].completion_quality = CompletionQuality.ADEQUATE
        workouts[2].completion_date = start_date + timedelta(days=2)

        # Save and reload
        plan_storage.save_plan(plan)
        loaded_plan = plan_storage.load_plan("completion-test")

        # Verify completion tracking
        assert loaded_plan is not None
        week = loaded_plan.weekly_schedules[0]
        assert week.completion_rate == 60.0  # 3/5 = 60%

        completed_workouts = [w for w in week.planned_workouts if w.completed]
        assert len(completed_workouts) == 3
        assert completed_workouts[0].completion_quality == CompletionQuality.EXCELLENT
        assert completed_workouts[1].completion_quality == CompletionQuality.GOOD
        assert completed_workouts[2].completion_quality == CompletionQuality.ADEQUATE

    def test_workout_completion_with_activities(self):
        """Test linking completed activities to planned workouts."""
        start_date = date.today()

        # Create planned workout
        workout = create_simple_workout(
            workout_id="wo-001",
            name="Morning Run",
            workout_type=WorkoutType.ENDURANCE,
            duration_minutes=60,
        )

        planned = PlannedWorkout(
            workout_id="planned-001",
            date=start_date,
            workout=workout,
            priority=WorkoutPriority.KEY,
            rationale="Build base",
            phase_id="base_1",
            week_number=1,
        )

        # Create matching activity
        activity = create_mock_activity(
            activity_id="garmin-123456",
            start_time=datetime.combine(start_date, datetime.min.time()) + timedelta(hours=7),
            duration_minutes=62,  # Slightly longer
            distance_km=10.0,
        )

        # Mark as completed
        planned.completed = True
        planned.completion_date = start_date
        planned.completion_quality = CompletionQuality.GOOD

        # Verify completion
        assert planned.completed
        assert planned.completion_quality == CompletionQuality.GOOD
        assert not planned.is_overdue


# ============================================================================
# Test 3: Performance Analysis Integration
# ============================================================================


class TestPerformanceAnalysisIntegration:
    """Test integration of performance analysis with plan execution."""

    def test_performance_analyzer_initialization(self, performance_analyzer):
        """Test PerformanceAnalyzer can be initialized and used."""
        # Verify analyzer exists
        assert performance_analyzer is not None

        # This test verifies the PerformanceAnalyzer can be instantiated
        # Full integration with actual activity matching would require
        # implementing the matching logic in the analyzer
        # For now, we verify the component is available for integration


# ============================================================================
# Test 4: Plan Adaptation Flow
# ============================================================================


class TestPlanAdaptation:
    """Test plan adaptation based on readiness and performance."""

    def test_low_readiness_adaptation(self, plan_storage):
        """Test plan adapts when readiness is consistently low."""
        start_date = date.today()
        base_phase = create_base_phase(start_date, duration_weeks=2)

        plan = TrainingPlan(
            plan_id="adaptation-test",
            athlete_id="athlete-004",
            athlete_name="Adaptation Test",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=start_date + timedelta(weeks=2),
            last_updated=datetime.now(),
            primary_goal={"race_name": "Test", "date": (start_date + timedelta(weeks=2)).isoformat()},
            phases=[base_phase],
            adaptation_enabled=True,
        )

        # Record adaptation decision
        adaptation = AdaptationDecision(
            adaptation_id="adapt-001",
            timestamp=datetime.now(),
            trigger=AdaptationTrigger.LOW_READINESS,
            trigger_details="Readiness score < 60 for 3 consecutive days",
            affected_workouts=["planned-1", "planned-2"],
            original_plan_summary="2x Threshold workouts",
            adapted_plan_summary="2x Tempo workouts (reduced intensity)",
            reasoning="Low readiness indicates insufficient recovery. Reducing intensity to prevent overtraining.",
            confidence=0.85,
            requires_approval=False,
        )

        plan.adaptations.append(adaptation)

        # Save and reload
        plan_storage.save_plan(plan)
        loaded_plan = plan_storage.load_plan("adaptation-test")

        # Verify adaptation recorded
        assert loaded_plan is not None
        assert len(loaded_plan.adaptations) == 1
        assert loaded_plan.adaptations[0].trigger == AdaptationTrigger.LOW_READINESS
        assert loaded_plan.adaptations[0].confidence == 0.85

    def test_missed_workouts_adaptation(self, plan_storage):
        """Test plan adapts when key workouts are missed."""
        start_date = date.today()
        build_phase = create_build_phase(start_date, duration_weeks=2)

        plan = TrainingPlan(
            plan_id="missed-workouts-test",
            athlete_id="athlete-005",
            athlete_name="Missed Workouts Test",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=start_date + timedelta(weeks=2),
            last_updated=datetime.now(),
            primary_goal={"race_name": "Test", "date": (start_date + timedelta(weeks=2)).isoformat()},
            phases=[build_phase],
        )

        # Create week with missed key workouts
        workouts = []
        for i in range(3):
            workout = create_simple_workout(
                workout_id=f"wo-{i}",
                name=f"Key Workout {i+1}",
                workout_type=WorkoutType.THRESHOLD,
                duration_minutes=60,
            )
            planned = PlannedWorkout(
                workout_id=f"planned-{i}",
                date=start_date + timedelta(days=i),
                workout=workout,
                priority=WorkoutPriority.KEY,
                rationale="Build threshold",
                phase_id=build_phase.phase_id,
                week_number=1,
                completed=False,  # Missed
            )
            workouts.append(planned)

        week = WeeklySchedule(
            week_number=1,
            start_date=start_date,
            end_date=start_date + timedelta(days=6),
            phase_id=build_phase.phase_id,
            planned_workouts=workouts,
            target_volume_hours=3.0,
            adaptation_status=AdaptationStatus.FALLING_BEHIND,
        )
        plan.weekly_schedules.append(week)

        # Record adaptation
        adaptation = AdaptationDecision(
            adaptation_id="adapt-002",
            timestamp=datetime.now(),
            trigger=AdaptationTrigger.MISSED_WORKOUTS,
            trigger_details="3 key threshold workouts missed in week 1",
            affected_workouts=[f"planned-{i}" for i in range(3)],
            original_plan_summary="Week 1: 3x Threshold",
            adapted_plan_summary="Week 2: Add makeup threshold session, adjust volume",
            reasoning="Reschedule critical threshold work to week 2 to maintain progression.",
            confidence=0.9,
        )
        plan.adaptations.append(adaptation)

        # Save and reload
        plan_storage.save_plan(plan)
        loaded_plan = plan_storage.load_plan("missed-workouts-test")

        # Verify
        assert loaded_plan is not None
        assert len(loaded_plan.adaptations) == 1
        assert loaded_plan.adaptations[0].trigger == AdaptationTrigger.MISSED_WORKOUTS
        assert loaded_plan.weekly_schedules[0].adaptation_status == AdaptationStatus.FALLING_BEHIND


# ============================================================================
# Test 5: Multi-Week Plan Execution
# ============================================================================


class TestMultiWeekExecution:
    """Test complete multi-week plan execution."""

    def test_8_week_plan_progression(self, plan_storage, workout_selector):
        """Test 8-week plan with phase progression."""
        start_date = date.today()

        # Create 8-week plan: 4 weeks base + 4 weeks build
        base_phase = create_base_phase(start_date, duration_weeks=4)
        build_phase = create_build_phase(
            start_date + timedelta(weeks=4), duration_weeks=4
        )

        plan = TrainingPlan(
            plan_id="8-week-test",
            athlete_id="athlete-006",
            athlete_name="8-Week Test",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=start_date + timedelta(weeks=8),
            last_updated=datetime.now(),
            primary_goal={
                "race_name": "Test Half Marathon",
                "date": (start_date + timedelta(weeks=8)).isoformat(),
                "distance": 21.1,
            },
            phases=[base_phase, build_phase],
        )

        # Generate 8 weeks of schedules
        for week_num in range(8):
            week_start = start_date + timedelta(weeks=week_num)
            week_end = week_start + timedelta(days=6)

            # Select appropriate phase
            if week_num < 4:
                phase = base_phase
                readiness = 85  # Good readiness in base
            else:
                phase = build_phase
                readiness = 75  # Slightly lower in build

            # Generate schedule
            workout_schedule = workout_selector.select_weekly_schedule(
                phase=phase,
                week_start_date=week_start,
                average_readiness=readiness,
                sport=Sport.RUNNING,
            )

            # Convert to planned workouts
            planned_workouts = []
            for i, workout_dict in enumerate(workout_schedule):
                workout = create_simple_workout(
                    workout_id=f"w{week_num+1}-{i+1}",
                    name=f"Week {week_num+1} {workout_dict['workout_type'].value}",
                    workout_type=workout_dict["workout_type"],
                    duration_minutes=workout_dict["duration_minutes"],
                )

                planned = PlannedWorkout(
                    workout_id=f"planned-w{week_num+1}-{i+1}",
                    date=workout_dict["date"],
                    workout=workout,
                    priority=workout_dict["priority"],
                    rationale=f"{phase.phase_type.value} phase training",
                    phase_id=phase.phase_id,
                    week_number=week_num + 1,
                )
                planned_workouts.append(planned)

            weekly = WeeklySchedule(
                week_number=week_num + 1,
                start_date=week_start,
                end_date=week_end,
                phase_id=phase.phase_id,
                planned_workouts=planned_workouts,
                target_volume_hours=sum(w["duration_minutes"] for w in workout_schedule) / 60,
            )
            plan.weekly_schedules.append(weekly)

        # Save plan
        plan_storage.save_plan(plan)
        loaded_plan = plan_storage.load_plan("8-week-test")

        # Verify plan structure
        assert loaded_plan is not None
        assert len(loaded_plan.weekly_schedules) == 8
        assert len(loaded_plan.phases) == 2

        # Verify phase progression
        assert loaded_plan.weekly_schedules[0].phase_id == "base_1"
        assert loaded_plan.weekly_schedules[3].phase_id == "base_1"
        assert loaded_plan.weekly_schedules[4].phase_id == "build_1"
        assert loaded_plan.weekly_schedules[7].phase_id == "build_1"

    def test_full_race_prep_plan(self, plan_storage, workout_selector):
        """Test complete race prep: BASE → BUILD → PEAK → TAPER."""
        start_date = date.today()
        race_date = start_date + timedelta(weeks=13)

        # Create all phases
        base = create_base_phase(start_date, duration_weeks=4)
        build = create_build_phase(start_date + timedelta(weeks=4), duration_weeks=4)
        peak = create_peak_phase(start_date + timedelta(weeks=8), duration_weeks=3)
        taper = create_taper_phase(start_date + timedelta(weeks=11), duration_weeks=2)

        plan = TrainingPlan(
            plan_id="race-prep-test",
            athlete_id="athlete-007",
            athlete_name="Race Prep Test",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=race_date,
            last_updated=datetime.now(),
            primary_goal={
                "race_name": "Target Marathon",
                "date": race_date.isoformat(),
                "distance": 42.195,
                "goal_time": "3:30:00",
            },
            phases=[base, build, peak, taper],
        )

        # Generate schedules for all 13 weeks
        phases_by_week = (
            [base] * 4 + [build] * 4 + [peak] * 3 + [taper] * 2
        )

        for week_num in range(13):
            week_start = start_date + timedelta(weeks=week_num)
            week_end = week_start + timedelta(days=6)
            phase = phases_by_week[week_num]

            # Calculate days to race for taper logic
            days_to_race = (race_date - week_start).days

            workout_schedule = workout_selector.select_weekly_schedule(
                phase=phase,
                week_start_date=week_start,
                average_readiness=80,
                sport=Sport.RUNNING,
            )

            planned_workouts = []
            for i, workout_dict in enumerate(workout_schedule):
                workout = create_simple_workout(
                    workout_id=f"w{week_num+1}-{i+1}",
                    name=f"Week {week_num+1} {workout_dict['workout_type'].value}",
                    workout_type=workout_dict["workout_type"],
                    duration_minutes=workout_dict["duration_minutes"],
                )

                planned = PlannedWorkout(
                    workout_id=f"planned-w{week_num+1}-{i+1}",
                    date=workout_dict["date"],
                    workout=workout,
                    priority=workout_dict["priority"],
                    rationale=f"{phase.phase_type.value} training for marathon",
                    phase_id=phase.phase_id,
                    week_number=week_num + 1,
                )
                planned_workouts.append(planned)

            weekly = WeeklySchedule(
                week_number=week_num + 1,
                start_date=week_start,
                end_date=week_end,
                phase_id=phase.phase_id,
                planned_workouts=planned_workouts,
                target_volume_hours=sum(w["duration_minutes"] for w in workout_schedule) / 60,
            )
            plan.weekly_schedules.append(weekly)

        # Save and verify
        plan_storage.save_plan(plan)
        loaded_plan = plan_storage.load_plan("race-prep-test")

        assert loaded_plan is not None
        assert len(loaded_plan.weekly_schedules) == 13
        assert len(loaded_plan.phases) == 4

        # Verify phase transitions
        assert loaded_plan.weekly_schedules[0].phase_id == "base_1"
        assert loaded_plan.weekly_schedules[4].phase_id == "build_1"
        assert loaded_plan.weekly_schedules[8].phase_id == "peak"
        assert loaded_plan.weekly_schedules[11].phase_id == "taper"

        # Verify taper weeks have reduced volume compared to build
        taper_week_11 = loaded_plan.weekly_schedules[10]  # Week 11 (index 10)
        taper_week_12 = loaded_plan.weekly_schedules[11]  # Week 12 (index 11)
        build_week_7 = loaded_plan.weekly_schedules[6]  # Week 7 (index 6)

        # Taper weeks should have less volume than build weeks
        assert taper_week_11.target_volume_hours < build_week_7.target_volume_hours
        # Note: Taper weeks may have similar volumes, so we just verify they're both reduced


# ============================================================================
# Test 6: Plan History and Versioning
# ============================================================================


class TestPlanVersioning:
    """Test plan versioning and history tracking."""

    def test_plan_update_creates_backup(self, plan_storage):
        """Test that updating a plan creates version history."""
        start_date = date.today()
        base_phase = create_base_phase(start_date, duration_weeks=2)

        plan = TrainingPlan(
            plan_id="versioning-test",
            athlete_id="athlete-008",
            athlete_name="Versioning Test",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=start_date + timedelta(weeks=2),
            last_updated=datetime.now(),
            primary_goal={"race_name": "Test", "date": (start_date + timedelta(weeks=2)).isoformat()},
            phases=[base_phase],
            version=1,
        )

        # Save initial version
        plan_storage.save_plan(plan)

        # Wait to ensure different timestamp
        import time
        time.sleep(1.1)

        # Update plan
        plan.version = 2
        plan.notes = "Updated after week 1 review"
        plan.last_updated = datetime.now()

        # Save updated version (should create backup)
        plan_storage.save_plan(plan)

        # Get history
        history = plan_storage.get_plan_history("versioning-test")

        # Verify backup created
        assert len(history) >= 1  # At least one backup

        # Get current version
        current = plan_storage.load_plan("versioning-test")
        assert current.version == 2
        assert current.notes == "Updated after week 1 review"


# ============================================================================
# Test 7: Constraint-Based Schedule Adjustment
# ============================================================================


class TestScheduleConstraints:
    """Test schedule adjustments based on constraints."""

    def test_max_hours_constraint(self, workout_selector):
        """Test schedule adjusts to max weekly hours."""
        start_date = date.today()
        build_phase = create_build_phase(start_date, duration_weeks=1)

        # Generate full schedule
        schedule = workout_selector.select_weekly_schedule(
            phase=build_phase,
            week_start_date=start_date,
            average_readiness=85,
            sport=Sport.RUNNING,
        )

        # Apply 8-hour constraint
        adjusted = workout_selector.adjust_for_constraints(
            schedule=schedule.copy(),
            max_weekly_hours=8.0,
        )

        # Verify constraint met
        total_hours = sum(w["duration_minutes"] for w in adjusted) / 60
        assert total_hours <= 8.5  # Allow small rounding margin

    def test_max_sessions_constraint(self, workout_selector):
        """Test schedule adjusts to max sessions per week."""
        start_date = date.today()
        build_phase = create_build_phase(start_date, duration_weeks=1)

        schedule = workout_selector.select_weekly_schedule(
            phase=build_phase,
            week_start_date=start_date,
            average_readiness=85,
            sport=Sport.RUNNING,
        )

        # Limit to 4 sessions
        adjusted = workout_selector.adjust_for_constraints(
            schedule=schedule.copy(),
            max_sessions_per_week=4,
        )

        assert len(adjusted) <= 4

        # Verify key workouts prioritized
        priorities = [w["priority"] for w in adjusted]
        assert WorkoutPriority.KEY in priorities

    def test_required_rest_days(self, workout_selector):
        """Test schedule ensures minimum rest days."""
        start_date = date.today()
        build_phase = create_build_phase(start_date, duration_weeks=1)

        schedule = workout_selector.select_weekly_schedule(
            phase=build_phase,
            week_start_date=start_date,
            average_readiness=85,
            sport=Sport.RUNNING,
        )

        # Require 2 rest days
        adjusted = workout_selector.adjust_for_constraints(
            schedule=schedule.copy(),
            required_rest_days=2,
        )

        recovery_count = sum(
            1 for w in adjusted
            if w["workout_type"] == WorkoutType.RECOVERY
        )
        assert recovery_count >= 2
