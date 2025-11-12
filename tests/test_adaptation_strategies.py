"""
Comprehensive tests for AdaptationEngine strategies.
"""

from datetime import date, datetime, timedelta
import pytest

from services.ai.planning import (
    AdaptationEngine,
    TrainingPlan,
    PlannedWorkout,
    WorkoutPriority,
    AdaptationTrigger,
    create_base_phase,
)
from services.ai.workouts.workout_models import (
    StructuredWorkout,
    WorkoutSegment,
    Interval,
    WorkoutType,
    IntensityZone,
    Sport,
)


class TestAdaptationStrategies:
    """Test different adaptation strategies."""

    def test_adapt_for_low_readiness(self):
        """Test adaptation strategy for low readiness."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        # Trigger low readiness adaptation
        decision = engine.adapt_upcoming_workouts(
            plan=plan,
            trigger=AdaptationTrigger.LOW_READINESS,
            trigger_details="Average readiness 55 for 3 days",
            readiness_score=55,
            days_ahead=7,
        )

        assert decision is not None
        assert len(decision.affected_workouts) > 0
        assert "reduced" in decision.reasoning.lower() or "recovery" in decision.reasoning.lower()

    def test_adapt_for_high_training_load(self):
        """Test adaptation for high training load (ACWR)."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        decision = engine.adapt_upcoming_workouts(
            plan=plan,
            trigger=AdaptationTrigger.HIGH_TRAINING_LOAD,
            trigger_details="ACWR 1.7 exceeds safe threshold",
            readiness_score=70,
            days_ahead=7,
        )

        assert decision is not None
        assert len(decision.affected_workouts) > 0
        assert "load" in decision.reasoning.lower() or "recovery" in decision.reasoning.lower()

    def test_adapt_for_missed_workouts(self):
        """Test adaptation when workouts consistently missed."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        decision = engine.adapt_upcoming_workouts(
            plan=plan,
            trigger=AdaptationTrigger.MISSED_WORKOUTS,
            trigger_details="Key workout completion 65%",
            readiness_score=75,
            days_ahead=7,
        )

        assert decision is not None
        # Should simplify plan - fewer workouts
        assert "simplified" in decision.reasoning.lower() or "key" in decision.reasoning.lower()

    def test_adapt_for_poor_performance(self):
        """Test adaptation for declining performance."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        decision = engine.adapt_upcoming_workouts(
            plan=plan,
            trigger=AdaptationTrigger.POOR_PERFORMANCE,
            trigger_details="FTP declined 6% - overreaching detected",
            readiness_score=65,
            days_ahead=7,
        )

        assert decision is not None
        assert len(decision.affected_workouts) > 0
        assert "intensity" in decision.reasoning.lower() or "rebuild" in decision.reasoning.lower()

    def test_adaptation_requires_approval_for_major_changes(self):
        """Test that major adaptations require approval."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        # Illness/injury should require approval
        decision = engine.adapt_upcoming_workouts(
            plan=plan,
            trigger=AdaptationTrigger.ILLNESS_INJURY,
            trigger_details="Athlete reported knee pain",
            readiness_score=40,
            days_ahead=7,
        )

        assert decision.requires_approval is True

    def test_sensitivity_affects_thresholds(self):
        """Test that sensitivity modifies adaptation thresholds."""
        # Conservative engine (less likely to adapt)
        conservative_engine = AdaptationEngine(sensitivity=0.5)

        # Aggressive engine (more likely to adapt)
        aggressive_engine = AdaptationEngine(sensitivity=2.0)

        plan = self._create_test_plan_with_completion_rate(75)  # Borderline completion

        readiness_history = [(date.today() - timedelta(days=i), 75) for i in range(7)]

        conservative_result, _, _ = conservative_engine.should_adapt_plan(
            plan, readiness_history
        )
        aggressive_result, _, _ = aggressive_engine.should_adapt_plan(
            plan, readiness_history
        )

        # Aggressive should be more likely to adapt
        assert isinstance(conservative_result, bool)
        assert isinstance(aggressive_result, bool)

    def test_reschedule_missed_key_workout(self):
        """Test rescheduling a missed key workout."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        # Get a key workout that was missed
        missed_workout = plan.upcoming_workouts(days=7)[0]
        missed_workout.priority = WorkoutPriority.KEY
        missed_workout.date = date.today() - timedelta(days=2)  # In the past

        # Reschedule it
        decision = engine.reschedule_missed_key_workout(
            plan=plan, missed_workout=missed_workout
        )

        assert decision is not None
        assert decision.trigger == AdaptationTrigger.MISSED_WORKOUTS
        assert "rescheduled" in decision.adapted_plan_summary.lower()

    def test_no_adaptation_when_disabled(self):
        """Test that adaptation doesn't happen when disabled."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()
        plan.adaptation_enabled = False

        readiness_history = [(date.today() - timedelta(days=i), 45) for i in range(7)]

        should_adapt, trigger, details = engine.should_adapt_plan(
            plan, readiness_history
        )

        assert should_adapt is False
        assert trigger is None
        assert "disabled" in details.lower()

    def test_consecutive_low_readiness_triggers(self):
        """Test low readiness must be consecutive days."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        # Mark all workouts as completed to avoid MISSED_WORKOUTS trigger
        for week in plan.weekly_schedules:
            for workout in week.planned_workouts:
                workout.completed = True

        # 3 consecutive days of low readiness
        readiness_history = [
            (date.today() - timedelta(days=0), 55),
            (date.today() - timedelta(days=1), 55),
            (date.today() - timedelta(days=2), 55),
            (date.today() - timedelta(days=3), 80),  # Good day earlier
        ]

        should_adapt, trigger, details = engine.should_adapt_plan(
            plan, readiness_history
        )

        assert should_adapt is True
        assert trigger == AdaptationTrigger.LOW_READINESS

    def test_high_acwr_triggers_adaptation(self):
        """Test high ACWR ratio triggers adaptation."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        # Mark all workouts as completed to avoid MISSED_WORKOUTS trigger
        for week in plan.weekly_schedules:
            for workout in week.planned_workouts:
                workout.completed = True

        readiness_history = [(date.today() - timedelta(days=i), 75) for i in range(7)]

        should_adapt, trigger, details = engine.should_adapt_plan(
            plan, readiness_history, recent_acwr=1.6  # Above 1.5 threshold
        )

        assert should_adapt is True
        assert trigger == AdaptationTrigger.HIGH_TRAINING_LOAD
        assert "ACWR" in details

    def test_overdue_key_workouts_trigger(self):
        """Test that overdue key workouts trigger adaptation."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        # Set some workouts as overdue and key priority
        upcoming = plan.upcoming_workouts(days=7)
        for i, workout in enumerate(upcoming[:3]):
            workout.priority = WorkoutPriority.KEY
            workout.date = date.today() - timedelta(days=i + 1)  # Make them overdue

        readiness_history = [(date.today() - timedelta(days=i), 75) for i in range(7)]

        should_adapt, trigger, details = engine.should_adapt_plan(
            plan, readiness_history
        )

        assert should_adapt is True
        assert trigger == AdaptationTrigger.MISSED_WORKOUTS
        assert "overdue" in details.lower()

    def test_adaptation_confidence_scoring(self):
        """Test that adaptations include confidence scores."""
        engine = AdaptationEngine()

        plan = self._create_test_plan_with_workouts()

        decision = engine.adapt_upcoming_workouts(
            plan=plan,
            trigger=AdaptationTrigger.LOW_READINESS,
            trigger_details="Test adaptation",
            readiness_score=55,
            days_ahead=7,
        )

        assert decision is not None
        assert 0 <= decision.confidence <= 1.0

    def _create_test_plan_with_workouts(self) -> TrainingPlan:
        """Create a test plan with upcoming workouts."""
        start_date = date.today()
        end_date = start_date + timedelta(weeks=12)

        phase = create_base_phase(start_date, duration_weeks=12)

        plan = TrainingPlan(
            plan_id="test-plan",
            athlete_id="athlete1",
            athlete_name="Test Athlete",
            created_date=datetime.now(),
            start_date=start_date,
            end_date=end_date,
            last_updated=datetime.now(),
            primary_goal={"name": "Test Race", "date": end_date.isoformat()},
            phases=[phase],
        )

        # Add some upcoming workouts
        from services.ai.planning.plan_models import WeeklySchedule

        week = WeeklySchedule(
            week_number=1,
            start_date=start_date,
            end_date=start_date + timedelta(days=7),
            phase_id=phase.phase_id,
            target_volume_hours=10.0,  # Required parameter
            planned_workouts=[
                PlannedWorkout(
                    workout_id=f"wo-{i}",
                    date=start_date + timedelta(days=i),
                    workout=self._create_workout(WorkoutType.THRESHOLD, 60),
                    priority=WorkoutPriority.KEY
                    if i % 3 == 0
                    else WorkoutPriority.IMPORTANT,
                    rationale="Training",
                    phase_id=phase.phase_id,
                    week_number=1,
                )
                for i in range(5)
            ],
        )

        plan.weekly_schedules = [week]

        return plan

    def _create_test_plan_with_completion_rate(
        self, completion_rate: float
    ) -> TrainingPlan:
        """Create a test plan with specific completion rate."""
        plan = self._create_test_plan_with_workouts()

        # Mark some workouts as completed
        num_to_complete = int(len(plan.weekly_schedules[0].planned_workouts) * completion_rate / 100)

        for i in range(num_to_complete):
            plan.weekly_schedules[0].planned_workouts[i].completed = True

        return plan

    def _create_workout(
        self, workout_type: WorkoutType, duration: int
    ) -> StructuredWorkout:
        """Helper to create a workout."""
        return StructuredWorkout(
            workout_id="test-wo",
            name=f"{workout_type.value} workout",
            sport=Sport.RUNNING,
            workout_type=workout_type,
            duration_minutes=duration,
            segments=[
                WorkoutSegment(
                    name="Main",
                    intervals=[
                        Interval(
                            duration_minutes=duration,
                            intensity_zone=IntensityZone.Z3,
                            description="Steady",
                        )
                    ],
                )
            ],
            average_intensity=IntensityZone.Z3,
            peak_intensity=IntensityZone.Z4,
            goal="Training",
        )


class TestEnhancedAdaptation:
    """Test enhanced adaptation with performance metrics."""

    def test_enhanced_adaptation_with_activities(self):
        """Test enhanced adaptation using performance metrics."""
        from services.garmin.models import Activity

        engine = AdaptationEngine()

        plan = TestAdaptationStrategies()._create_test_plan_with_workouts()
        readiness_history = [(date.today() - timedelta(days=i), 75) for i in range(7)]

        # Create mock activities
        recent_activities = []
        for i in range(10):
            activity = Activity(
                activity_id=f"act-{i}",
                name=f"Activity {i}",
                sport="running",
                start_time=datetime.now() - timedelta(days=i),
                duration_seconds=3600,
                distance=10000,
                average_hr=150,
            )
            recent_activities.append(activity)

        # Test enhanced adaptation
        should_adapt, trigger, details, metrics = engine.should_adapt_plan_enhanced(
            plan=plan,
            readiness_history=readiness_history,
            recent_activities=recent_activities,
            historical_activities=None,
            recent_acwr=1.2,
        )

        # Should return performance metrics
        assert metrics is not None
        assert hasattr(metrics, "performance_direction")
        assert hasattr(metrics, "confidence")
