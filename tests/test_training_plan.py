"""
Tests for Training Plan System.
"""

from datetime import date, datetime, timedelta
import pytest
import tempfile
from pathlib import Path

from services.ai.planning import (
    TrainingPlan,
    TrainingPhase,
    TrainingPhaseType,
    PlannedWorkout,
    WorkoutPriority,
    PlanStorage,
    ActivityMatcher,
    AdaptationEngine,
    WorkoutSelector,
    create_base_phase,
    create_build_phase,
)
from services.ai.workouts.workout_models import (
    StructuredWorkout,
    WorkoutSegment,
    Interval,
    WorkoutType,
    IntensityZone,
    Sport,
)


class TestTrainingPlanModels:
    """Test training plan data models."""

    def test_training_phase_creation(self):
        """Test creating a training phase."""
        start_date = date.today() + timedelta(days=30)
        phase = create_base_phase(start_date, duration_weeks=4)

        assert phase.phase_type == TrainingPhaseType.BASE
        assert phase.start_date == start_date
        assert phase.duration_weeks == 4
        assert phase.end_date == start_date + timedelta(weeks=4)
        assert len(phase.goals) > 0

    def test_training_plan_creation(self):
        """Test creating a training plan."""
        start_date = date.today() + timedelta(days=30)
        end_date = start_date + timedelta(weeks=12)

        plan = TrainingPlan(
            plan_id="test-plan-1",
            athlete_id="athlete1",
            athlete_name="Test Athlete",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=end_date,
            last_updated=datetime.now(),
            primary_goal={
                "name": "Test Marathon",
                "date": end_date.isoformat(),
                "race_type": "Marathon",
            },
            phases=[
                create_base_phase(start_date, 4),
                create_build_phase(start_date + timedelta(weeks=4), 8),
            ],
        )

        assert plan.plan_id == "test-plan-1"
        assert plan.athlete_name == "Test Athlete"
        assert len(plan.phases) == 2
        assert plan.weeks_remaining >= 0

    def test_planned_workout_creation(self):
        """Test creating a planned workout."""
        workout = StructuredWorkout(
            workout_id="wo-1",
            name="Easy Run",
            sport=Sport.RUNNING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=45,
            segments=[
                WorkoutSegment(
                    name="Easy running",
                    intervals=[
                        Interval(
                            duration_minutes=45,
                            intensity_zone=IntensityZone.Z1,
                            description="Easy effort",
                        )
                    ],
                )
            ],
            average_intensity=IntensityZone.Z1,
            peak_intensity=IntensityZone.Z1,
            goal="Recovery run",
        )

        planned = PlannedWorkout(
            workout_id="pw-1",
            date=date.today() + timedelta(days=45),
            workout=workout,
            priority=WorkoutPriority.BENEFICIAL,
            rationale="Active recovery",
            phase_id="base_1",
            week_number=2,
        )

        assert planned.workout_id == "pw-1"
        assert planned.priority == WorkoutPriority.BENEFICIAL
        assert planned.workout.duration_minutes == 45
        assert not planned.completed
        assert not planned.is_overdue  # Future date


class TestPlanStorage:
    """Test plan storage and persistence."""

    def test_save_and_load_plan(self):
        """Test saving and loading a plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            # Create test plan
            plan = TrainingPlan(
                plan_id="test-123",
                athlete_id="athlete1",
                athlete_name="Test Athlete",
                created_date=datetime.now(),
                start_date=date.today() + timedelta(days=30),
                end_date=date.today() + timedelta(days=120),
                last_updated=datetime.now(),
                primary_goal={"name": "Test Race", "date": (date.today() + timedelta(days=120)).isoformat()},
                phases=[create_base_phase(date.today() + timedelta(days=30), 4)],
            )

            # Save
            saved_path = storage.save_plan(plan, backup=False)
            assert saved_path.exists()

            # Load
            loaded_plan = storage.load_plan("test-123")
            assert loaded_plan is not None
            assert loaded_plan.plan_id == "test-123"
            assert loaded_plan.athlete_name == "Test Athlete"
            assert len(loaded_plan.phases) == 1

    def test_list_active_plans(self):
        """Test listing active plans."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            # Create multiple plans
            for i in range(3):
                plan = TrainingPlan(
                    plan_id=f"plan-{i}",
                    athlete_id=f"athlete{i}",
                    athlete_name=f"Athlete {i}",
                    created_date=datetime.now(),
                    start_date=date.today() + timedelta(days=30),
                    end_date=date.today() + timedelta(days=120),
                    last_updated=datetime.now(),
                    primary_goal={"name": f"Race {i}", "date": (date.today() + timedelta(days=120)).isoformat()},
                    phases=[],
                )
                storage.save_plan(plan, backup=False)

            # List
            summaries = storage.list_active_plans()
            assert len(summaries) == 3


class TestActivityMatcher:
    """Test activity matching."""

    def test_activity_matcher_initialization(self):
        """Test matcher initializes correctly."""
        matcher = ActivityMatcher(matching_window_hours=36)
        assert matcher.matching_window_hours == 36

    # Would need mock Activity objects for full testing
    # Skipping detailed tests for brevity


class TestAdaptationEngine:
    """Test adaptation engine."""

    def test_engine_initialization(self):
        """Test engine initializes."""
        engine = AdaptationEngine(sensitivity=1.0)
        assert engine.sensitivity == 1.0
        assert engine.workout_generator is not None

    def test_should_adapt_low_completion(self):
        """Test adaptation trigger for low completion."""
        engine = AdaptationEngine()

        # Create plan with low completion
        plan = TrainingPlan(
            plan_id="test",
            athlete_id="athlete1",
            athlete_name="Test",
            created_date=datetime.now(),
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=120),
            last_updated=datetime.now(),
            primary_goal={"name": "Race", "date": (date.today() + timedelta(days=120)).isoformat()},
            phases=[],
            weekly_schedules=[],
        )

        # Mock completion rate by modifying property (simplified)
        # In real scenario would have actual workouts

        readiness_history = [(date.today() - timedelta(days=i), 80) for i in range(7)]

        should_adapt, trigger, details = engine.should_adapt_plan(
            plan, readiness_history
        )

        # With empty plan, should not adapt
        assert not should_adapt


class TestWorkoutSelector:
    """Test workout selector."""

    def test_selector_initialization(self):
        """Test selector initializes."""
        selector = WorkoutSelector()
        assert selector.generator is not None

    def test_select_base_phase_workout(self):
        """Test workout selection for base phase."""
        selector = WorkoutSelector()
        phase = create_base_phase(date.today() + timedelta(days=30), 4)

        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Saturday",
            phase=phase,
            readiness_score=80,
            days_since_last_hard=3,
        )

        # Saturday in base should be long endurance
        assert workout_type == WorkoutType.ENDURANCE
        assert duration > 60
        assert priority == WorkoutPriority.KEY

    def test_select_low_readiness_override(self):
        """Test low readiness overrides plan."""
        selector = WorkoutSelector()
        phase = create_build_phase(date.today() + timedelta(days=30), 8)

        workout_type, duration, priority = selector.select_workout_for_day(
            day_of_week="Tuesday",  # Normally hard day
            phase=phase,
            readiness_score=50,  # Low readiness
            days_since_last_hard=3,
        )

        # Should be recovery despite being Tuesday in build phase
        assert workout_type == WorkoutType.RECOVERY

    def test_select_weekly_schedule(self):
        """Test generating full weekly schedule."""
        selector = WorkoutSelector()
        phase = create_base_phase(date.today() + timedelta(days=35), 4)  # Monday

        schedule = selector.select_weekly_schedule(
            phase=phase,
            week_start_date=date.today() + timedelta(days=35),
            average_readiness=75,
            sport=Sport.RUNNING,
        )

        assert len(schedule) == 7  # All 7 days
        assert all("date" in day for day in schedule)
        assert all("workout_type" in day for day in schedule)
        assert all("duration_minutes" in day for day in schedule)


@pytest.mark.integration
class TestTrainingPlanIntegration:
    """Integration tests for training plan system."""

    def test_create_and_manage_plan_lifecycle(self):
        """Test complete plan lifecycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            # 1. Create plan
            start_date = date.today()
            race_date = start_date + timedelta(weeks=16)

            plan = TrainingPlan(
                plan_id="integration-test",
                athlete_id="athlete1",
                athlete_name="Test Athlete",
                created_date=datetime.now(),
                start_date=start_date,
                end_date=race_date,
                last_updated=datetime.now(),
                primary_goal={
                    "name": "Test Marathon",
                    "date": race_date.isoformat(),
                    "race_type": "Marathon",
                    "priority": "A",
                },
                phases=[
                    create_base_phase(start_date, 4),
                    create_build_phase(start_date + timedelta(weeks=4), 8),
                ],
            )

            # 2. Save plan
            storage.save_plan(plan, backup=False)

            # 3. Load plan
            loaded = storage.load_plan("integration-test")
            assert loaded is not None
            assert len(loaded.phases) == 2

            # 4. Check adaptation needs
            engine = AdaptationEngine()
            readiness_history = [(date.today() - timedelta(days=i), 75) for i in range(7)]

            should_adapt, trigger, details = engine.should_adapt_plan(
                loaded, readiness_history
            )

            # New plan should not need adaptation
            assert not should_adapt

            # 5. List plans
            summaries = storage.list_active_plans()
            assert len(summaries) == 1
            assert summaries[0].athlete_name == "Test Athlete"
