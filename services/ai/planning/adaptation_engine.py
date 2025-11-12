"""
Adaptation Engine

Monitors plan execution and triggers dynamic adaptations based on athlete response.
"""

from datetime import date, datetime, timedelta
from typing import Any
import uuid

from services.ai.workouts.workout_generator import WorkoutGenerator
from services.ai.workouts.workout_models import WorkoutType, StructuredWorkout
from services.garmin.models import Activity
from .plan_models import (
    AdaptationDecision,
    AdaptationStatus,
    AdaptationTrigger,
    PlannedWorkout,
    TrainingPlan,
    WeeklySchedule,
    WorkoutCompletion,
    WorkoutPriority,
)
from .performance_analyzer import PerformanceAnalyzer, PerformanceMetrics


class AdaptationEngine:
    """Monitors training plan execution and triggers adaptive changes."""

    # Adaptation thresholds
    LOW_COMPLETION_THRESHOLD = 0.70  # <70% completion rate triggers adaptation
    LOW_READINESS_THRESHOLD = 60  # <60 average readiness
    LOW_READINESS_DAYS = 3  # 3+ consecutive days
    HIGH_ACWR_THRESHOLD = 1.5  # Acute:Chronic Workload Ratio
    KEY_WORKOUT_MISS_THRESHOLD = 0.80  # <80% key workout completion

    def __init__(self, sensitivity: float = 1.0):
        """
        Initialize adaptation engine.

        Args:
            sensitivity: Adaptation sensitivity (0.5=conservative, 1.0=normal, 2.0=aggressive)
        """
        self.sensitivity = sensitivity
        self.workout_generator = WorkoutGenerator()
        self.performance_analyzer = PerformanceAnalyzer()

    def should_adapt_plan(
        self,
        plan: TrainingPlan,
        readiness_history: list[tuple[date, int]],
        recent_acwr: float | None = None,
    ) -> tuple[bool, AdaptationTrigger | None, str]:
        """
        Determine if plan should be adapted.

        Args:
            plan: Current training plan
            readiness_history: List of (date, readiness_score) tuples
            recent_acwr: Recent Acute:Chronic Workload Ratio

        Returns:
            Tuple of (should_adapt, trigger, details)
        """
        # Check if adaptation is enabled
        if not plan.adaptation_enabled:
            return False, None, "Adaptation disabled"

        # Apply sensitivity to thresholds
        completion_threshold = self.LOW_COMPLETION_THRESHOLD / self.sensitivity
        readiness_threshold = self.LOW_READINESS_THRESHOLD / self.sensitivity

        # Check 1: Overall completion rate (only if plan has workouts)
        if plan.weekly_schedules:  # Only check if plan has scheduled workouts
            if plan.overall_completion_rate < completion_threshold * 100:
                return (
                    True,
                    AdaptationTrigger.MISSED_WORKOUTS,
                    f"Overall completion rate {plan.overall_completion_rate:.1f}% below threshold",
                )

        # Check 2: Current week completion
        current_week = plan.current_week
        if current_week:
            week_completion = current_week.key_workout_completion_rate
            if week_completion < self.KEY_WORKOUT_MISS_THRESHOLD * 100:
                return (
                    True,
                    AdaptationTrigger.MISSED_WORKOUTS,
                    f"Key workout completion {week_completion:.1f}% in current week",
                )

        # Check 3: Persistent low readiness
        if len(readiness_history) >= self.LOW_READINESS_DAYS:
            recent_scores = [score for _, score in readiness_history[-self.LOW_READINESS_DAYS:]]
            avg_readiness = sum(recent_scores) / len(recent_scores)

            if avg_readiness < readiness_threshold:
                return (
                    True,
                    AdaptationTrigger.LOW_READINESS,
                    f"Average readiness {avg_readiness:.1f} for {self.LOW_READINESS_DAYS} days",
                )

        # Check 4: High training load (ACWR)
        if recent_acwr and recent_acwr > self.HIGH_ACWR_THRESHOLD:
            return (
                True,
                AdaptationTrigger.HIGH_TRAINING_LOAD,
                f"ACWR {recent_acwr:.2f} exceeds safe threshold",
            )

        # Check 5: Overdue key workouts
        overdue_key = [
            w for w in plan.overdue_workouts
            if w.priority == WorkoutPriority.KEY
        ]
        if len(overdue_key) >= 2:
            return (
                True,
                AdaptationTrigger.MISSED_WORKOUTS,
                f"{len(overdue_key)} key workouts overdue",
            )

        return False, None, "Plan on track"

    def should_adapt_plan_enhanced(
        self,
        plan: TrainingPlan,
        readiness_history: list[tuple[date, int]],
        recent_activities: list[Activity],
        historical_activities: list[Activity] | None = None,
        recent_acwr: float | None = None,
    ) -> tuple[bool, AdaptationTrigger | None, str, PerformanceMetrics | None]:
        """
        Enhanced adaptation check using performance analysis.

        Integrates workout performance data (FTP, power curves, interval quality)
        with readiness and completion metrics for intelligent adaptation decisions.

        Args:
            plan: Current training plan
            readiness_history: List of (date, readiness_score) tuples
            recent_activities: Recent activities (last 2-4 weeks)
            historical_activities: Historical baseline for comparison
            recent_acwr: Recent Acute:Chronic Workload Ratio

        Returns:
            Tuple of (should_adapt, trigger, details, performance_metrics)
        """
        # Check basic adaptation triggers first
        basic_adapt, basic_trigger, basic_details = self.should_adapt_plan(
            plan, readiness_history, recent_acwr
        )

        # Analyze performance metrics
        performance_metrics = self.performance_analyzer.analyze_recent_performance(
            recent_activities=recent_activities,
            historical_activities=historical_activities,
        )

        # Get performance-based recommendation
        perf_adapt, perf_reasoning = self.performance_analyzer.get_adaptation_recommendation(
            performance_metrics
        )

        # Decision logic: Combine basic and performance analysis

        # Priority 1: Performance declining significantly
        if (performance_metrics.performance_direction == "declining"
            and performance_metrics.confidence > 0.7):

            # FTP declining > 5%
            if performance_metrics.ftp_change_pct < -5:
                return (
                    True,
                    AdaptationTrigger.POOR_PERFORMANCE,
                    f"FTP declined {performance_metrics.ftp_change_pct:.1f}% - overreaching detected",
                    performance_metrics,
                )

            # VO2max declining > 3%
            if performance_metrics.vo2max_change_pct < -3:
                return (
                    True,
                    AdaptationTrigger.POOR_PERFORMANCE,
                    f"VO2max declined {performance_metrics.vo2max_change_pct:.1f}% - reduce training load",
                    performance_metrics,
                )

        # Priority 2: Poor interval execution quality
        if performance_metrics.avg_interval_adherence < 0.70:
            return (
                True,
                AdaptationTrigger.POOR_PERFORMANCE,
                f"Poor interval quality ({performance_metrics.avg_interval_adherence:.1%}) - "
                f"athlete struggling with prescribed zones",
                performance_metrics,
            )

        # Priority 3: High zone drift (fatigue)
        if performance_metrics.zone_drift_score > 0.5:
            return (
                True,
                AdaptationTrigger.HIGH_TRAINING_LOAD,
                f"Significant HR drift ({performance_metrics.zone_drift_score:.1%}) during intervals - "
                f"accumulated fatigue",
                performance_metrics,
            )

        # Priority 4: Performance improving - override low readiness
        if (performance_metrics.performance_direction == "improving"
            and performance_metrics.confidence > 0.7
            and basic_trigger == AdaptationTrigger.LOW_READINESS):

            # Even if readiness is moderate, keep intensity if performance improving
            return (
                False,
                None,
                f"Performance improving (FTP: {performance_metrics.ftp_change_pct:+.1f}%, "
                f"VO2max: {performance_metrics.vo2max_change_pct:+.1f}%) - "
                f"continue as planned despite moderate readiness",
                performance_metrics,
            )

        # Priority 5: Use basic adaptation if triggered
        if basic_adapt:
            return (True, basic_trigger, basic_details, performance_metrics)

        # No adaptation needed
        return (
            False,
            None,
            "Performance and readiness metrics within normal range",
            performance_metrics
        )

    def adapt_upcoming_workouts(
        self,
        plan: TrainingPlan,
        trigger: AdaptationTrigger,
        trigger_details: str,
        readiness_score: int | None = None,
        days_ahead: int = 7,
    ) -> AdaptationDecision:
        """
        Adapt upcoming workouts based on trigger.

        Args:
            plan: Current training plan
            trigger: Why adaptation is needed
            trigger_details: Details about trigger
            readiness_score: Current readiness score
            days_ahead: Number of days ahead to adapt

        Returns:
            AdaptationDecision with changes
        """
        # Get upcoming workouts
        upcoming = plan.upcoming_workouts(days=days_ahead)

        if not upcoming:
            return self._create_no_change_decision(trigger, trigger_details)

        # Apply adaptation strategy based on trigger
        if trigger == AdaptationTrigger.LOW_READINESS:
            adapted_workouts = self._adapt_for_low_readiness(upcoming, readiness_score)
            reasoning = "Reduced intensity and volume to allow recovery"

        elif trigger == AdaptationTrigger.HIGH_TRAINING_LOAD:
            adapted_workouts = self._adapt_for_high_load(upcoming)
            reasoning = "Reduced training load to prevent overtraining"

        elif trigger == AdaptationTrigger.MISSED_WORKOUTS:
            adapted_workouts = self._adapt_for_missed_workouts(upcoming, plan)
            reasoning = "Simplified plan and rescheduled key workouts"

        elif trigger == AdaptationTrigger.POOR_PERFORMANCE:
            adapted_workouts = self._adapt_for_poor_performance(upcoming)
            reasoning = "Reduced intensity to rebuild confidence and fitness"

        else:
            # For other triggers, use conservative approach
            adapted_workouts = self._adapt_conservative(upcoming)
            reasoning = "Conservative adaptation to address concerns"

        # Apply changes to plan
        affected_workout_ids = []
        original_summaries = []
        adapted_summaries = []

        for orig_workout, adapted_workout in zip(upcoming, adapted_workouts):
            if adapted_workout is not None:
                affected_workout_ids.append(orig_workout.workout_id)
                original_summaries.append(
                    f"{orig_workout.date}: {orig_workout.workout.name}"
                )
                adapted_summaries.append(
                    f"{adapted_workout.date}: {adapted_workout.workout.name}"
                )

                # Update workout in plan
                self._update_workout_in_plan(plan, orig_workout.workout_id, adapted_workout)

        # Create adaptation decision
        decision = AdaptationDecision(
            adaptation_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            trigger=trigger,
            trigger_details=trigger_details,
            affected_workouts=affected_workout_ids,
            original_plan_summary="\n".join(original_summaries),
            adapted_plan_summary="\n".join(adapted_summaries),
            reasoning=reasoning,
            confidence=0.8,  # Could be made more sophisticated
            requires_approval=self._requires_approval(trigger, adapted_workouts),
        )

        return decision

    def _adapt_for_low_readiness(
        self,
        workouts: list[PlannedWorkout],
        readiness_score: int | None,
    ) -> list[PlannedWorkout | None]:
        """Adapt workouts for low readiness scenario."""
        adapted = []

        for workout in workouts:
            # Skip hard sessions, convert to recovery
            if workout.workout.workout_type in [
                WorkoutType.THRESHOLD,
                WorkoutType.VO2MAX,
                WorkoutType.SPEED,
            ]:
                # Generate recovery workout instead
                recovery_workout = self.workout_generator.generate_workout(
                    sport=workout.workout.sport,
                    workout_type=WorkoutType.RECOVERY,
                    duration_minutes=min(45, workout.workout.duration_minutes),
                    athlete_zones={},  # Will use defaults
                    readiness_score=readiness_score or 50,
                )

                adapted_planned = PlannedWorkout(
                    workout_id=workout.workout_id,
                    date=workout.date,
                    workout=recovery_workout,
                    priority=WorkoutPriority.BENEFICIAL,  # Downgrade priority
                    rationale=f"Adapted from {workout.workout.workout_type.value} due to low readiness",
                    phase_id=workout.phase_id,
                    week_number=workout.week_number,
                )
                adapted.append(adapted_planned)

            # Reduce endurance/tempo by 25-30%
            elif workout.workout.workout_type in [WorkoutType.ENDURANCE, WorkoutType.TEMPO]:
                reduced_duration = int(workout.workout.duration_minutes * 0.70)

                reduced_workout = self.workout_generator.generate_workout(
                    sport=workout.workout.sport,
                    workout_type=workout.workout.workout_type,
                    duration_minutes=reduced_duration,
                    athlete_zones={},
                    readiness_score=readiness_score or 60,
                )

                adapted_planned = PlannedWorkout(
                    workout_id=workout.workout_id,
                    date=workout.date,
                    workout=reduced_workout,
                    priority=workout.priority,
                    rationale=f"Reduced volume by 30% due to low readiness",
                    phase_id=workout.phase_id,
                    week_number=workout.week_number,
                )
                adapted.append(adapted_planned)

            else:
                # Keep recovery workouts as-is
                adapted.append(workout)

        return adapted

    def _adapt_for_high_load(
        self, workouts: list[PlannedWorkout]
    ) -> list[PlannedWorkout | None]:
        """Adapt workouts for high training load."""
        adapted = []

        # Insert recovery day at start of week
        if workouts:
            first_workout = workouts[0]
            recovery_workout = self.workout_generator.generate_workout(
                sport=first_workout.workout.sport,
                workout_type=WorkoutType.RECOVERY,
                duration_minutes=45,
                athlete_zones={},
                readiness_score=60,
            )

            adapted.append(
                PlannedWorkout(
                    workout_id=first_workout.workout_id,
                    date=first_workout.date,
                    workout=recovery_workout,
                    priority=WorkoutPriority.IMPORTANT,
                    rationale="Recovery day added due to high training load",
                    phase_id=first_workout.phase_id,
                    week_number=first_workout.week_number,
                )
            )

        # Reduce intensity of remaining hard workouts
        for workout in workouts[1:]:
            if workout.workout.workout_type in [WorkoutType.THRESHOLD, WorkoutType.VO2MAX]:
                # Convert to tempo
                tempo_workout = self.workout_generator.generate_workout(
                    sport=workout.workout.sport,
                    workout_type=WorkoutType.TEMPO,
                    duration_minutes=workout.workout.duration_minutes,
                    athlete_zones={},
                    readiness_score=70,
                )

                adapted.append(
                    PlannedWorkout(
                        workout_id=workout.workout_id,
                        date=workout.date,
                        workout=tempo_workout,
                        priority=workout.priority,
                        rationale="Reduced from high intensity due to training load",
                        phase_id=workout.phase_id,
                        week_number=workout.week_number,
                    )
                )
            else:
                adapted.append(workout)

        return adapted

    def _adapt_for_missed_workouts(
        self, workouts: list[PlannedWorkout], plan: TrainingPlan
    ) -> list[PlannedWorkout | None]:
        """Adapt for pattern of missed workouts."""
        # Strategy: Simplify plan, reduce session count

        if len(workouts) <= 3:
            return workouts  # Already minimal

        # Keep only key and important workouts
        essential_workouts = [
            w for w in workouts
            if w.priority in [WorkoutPriority.KEY, WorkoutPriority.IMPORTANT]
        ]

        # If we removed too many, add back some beneficial ones
        if len(essential_workouts) < 3:
            beneficial = [
                w for w in workouts
                if w.priority == WorkoutPriority.BENEFICIAL
            ]
            essential_workouts.extend(beneficial[: 3 - len(essential_workouts)])

        return essential_workouts

    def _adapt_for_poor_performance(
        self, workouts: list[PlannedWorkout]
    ) -> list[PlannedWorkout | None]:
        """Adapt for declining performance."""
        adapted = []

        for workout in workouts:
            # Reduce all hard workouts to tempo
            if workout.workout.workout_type in [WorkoutType.THRESHOLD, WorkoutType.VO2MAX, WorkoutType.SPEED]:
                tempo_workout = self.workout_generator.generate_workout(
                    sport=workout.workout.sport,
                    workout_type=WorkoutType.TEMPO,
                    duration_minutes=workout.workout.duration_minutes,
                    athlete_zones={},
                    readiness_score=70,
                )

                adapted.append(
                    PlannedWorkout(
                        workout_id=workout.workout_id,
                        date=workout.date,
                        workout=tempo_workout,
                        priority=workout.priority,
                        rationale="Reduced intensity to rebuild fitness foundation",
                        phase_id=workout.phase_id,
                        week_number=workout.week_number,
                    )
                )
            else:
                adapted.append(workout)

        return adapted

    def _adapt_conservative(
        self, workouts: list[PlannedWorkout]
    ) -> list[PlannedWorkout | None]:
        """Conservative adaptation - minimal changes."""
        # Just reduce volume by 15-20% across board
        adapted = []

        for workout in workouts:
            reduced_duration = int(workout.workout.duration_minutes * 0.85)

            reduced_workout = self.workout_generator.generate_workout(
                sport=workout.workout.sport,
                workout_type=workout.workout.workout_type,
                duration_minutes=reduced_duration,
                athlete_zones={},
                readiness_score=75,
            )

            adapted.append(
                PlannedWorkout(
                    workout_id=workout.workout_id,
                    date=workout.date,
                    workout=reduced_workout,
                    priority=workout.priority,
                    rationale="Minor volume reduction as precaution",
                    phase_id=workout.phase_id,
                    week_number=workout.week_number,
                )
            )

        return adapted

    def _requires_approval(
        self, trigger: AdaptationTrigger, adapted_workouts: list[PlannedWorkout | None]
    ) -> bool:
        """Determine if adaptation requires human approval."""
        # Major changes require approval
        if trigger in [
            AdaptationTrigger.ILLNESS_INJURY,
            AdaptationTrigger.RACE_CHANGE,
        ]:
            return True

        # Significant workout modifications
        if len([w for w in adapted_workouts if w]) > 5:
            return True

        # Otherwise automatic
        return False

    def _update_workout_in_plan(
        self,
        plan: TrainingPlan,
        workout_id: str,
        new_workout: PlannedWorkout,
    ) -> None:
        """Update a workout in the plan."""
        for week in plan.weekly_schedules:
            for i, workout in enumerate(week.planned_workouts):
                if workout.workout_id == workout_id:
                    week.planned_workouts[i] = new_workout
                    week.adaptation_status = AdaptationStatus.MINOR_ADJUSTMENT
                    week.adaptations_made.append(
                        f"{datetime.now().strftime('%Y-%m-%d')}: {new_workout.rationale}"
                    )
                    return

    def _create_no_change_decision(
        self, trigger: AdaptationTrigger, details: str
    ) -> AdaptationDecision:
        """Create decision indicating no changes needed."""
        return AdaptationDecision(
            adaptation_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            trigger=trigger,
            trigger_details=details,
            affected_workouts=[],
            original_plan_summary="No changes needed",
            adapted_plan_summary="Plan continues as scheduled",
            reasoning="Insufficient upcoming workouts or adaptation not warranted",
            confidence=0.9,
            requires_approval=False,
        )

    def reschedule_missed_key_workout(
        self,
        plan: TrainingPlan,
        missed_workout: PlannedWorkout,
        target_date: date | None = None,
    ) -> AdaptationDecision | None:
        """
        Reschedule a missed key workout to a future date.

        Args:
            plan: Training plan
            missed_workout: Workout that was missed
            target_date: Optional target date (defaults to next available)

        Returns:
            AdaptationDecision if successful, None otherwise
        """
        if not missed_workout.can_reschedule:
            return None

        # Find next available slot
        if target_date is None:
            target_date = missed_workout.date + timedelta(days=1)
            max_date = missed_workout.date + timedelta(days=missed_workout.reschedule_window_days)

            # Find first day without key workout
            while target_date <= max_date:
                existing = [
                    w for w in plan.upcoming_workouts(days=(target_date - date.today()).days)
                    if w.date == target_date and w.priority == WorkoutPriority.KEY
                ]
                if not existing:
                    break
                target_date += timedelta(days=1)

            if target_date > max_date:
                return None  # No slot available

        # Create rescheduled workout
        rescheduled = PlannedWorkout(
            workout_id=missed_workout.workout_id,
            date=target_date,
            workout=missed_workout.workout,
            priority=missed_workout.priority,
            rationale=f"Rescheduled from {missed_workout.date} (was missed)",
            phase_id=missed_workout.phase_id,
            week_number=missed_workout.week_number,
            can_reschedule=False,  # Don't reschedule again
        )

        # Update plan
        self._update_workout_in_plan(plan, missed_workout.workout_id, rescheduled)

        return AdaptationDecision(
            adaptation_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            trigger=AdaptationTrigger.MISSED_WORKOUTS,
            trigger_details=f"Key workout missed on {missed_workout.date}",
            affected_workouts=[missed_workout.workout_id],
            original_plan_summary=f"{missed_workout.date}: {missed_workout.workout.name}",
            adapted_plan_summary=f"{target_date}: {rescheduled.workout.name} (rescheduled)",
            reasoning="Rescheduled missed key workout to preserve training stimulus",
            confidence=0.85,
            requires_approval=False,
        )
