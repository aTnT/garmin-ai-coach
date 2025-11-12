"""
Workout Selector

Context-aware selection of appropriate workouts based on phase, readiness, and schedule.
"""

from datetime import date, timedelta
from typing import Any

from services.ai.workouts.workout_models import WorkoutType, Sport
from services.ai.workouts.workout_generator import WorkoutGenerator
from .plan_models import TrainingPhase, TrainingPhaseType, WorkoutPriority


class WorkoutSelector:
    """Selects appropriate workouts based on training context."""

    def __init__(self):
        """Initialize workout selector."""
        self.generator = WorkoutGenerator()

    def select_workout_for_day(
        self,
        day_of_week: str,
        phase: TrainingPhase,
        readiness_score: int,
        days_since_last_hard: int,
        days_to_race: int | None = None,
        recent_workout_types: list[WorkoutType] | None = None,
    ) -> tuple[WorkoutType, int, WorkoutPriority]:
        """
        Select appropriate workout type, duration, and priority for a day.

        Args:
            day_of_week: Day name (Monday, Tuesday, etc.)
            phase: Current training phase
            readiness_score: Current readiness (0-100)
            days_since_last_hard: Days since last hard workout
            days_to_race: Days until goal race (None if not applicable)
            recent_workout_types: Recent workout types for variety

        Returns:
            Tuple of (workout_type, duration_minutes, priority)
        """
        recent_workout_types = recent_workout_types or []

        # Low readiness override
        if readiness_score < 55:
            return WorkoutType.RECOVERY, 45, WorkoutPriority.IMPORTANT

        # Phase-specific selection
        if phase.phase_type == TrainingPhaseType.BASE:
            return self._select_base_workout(
                day_of_week, readiness_score, days_since_last_hard, recent_workout_types
            )

        elif phase.phase_type == TrainingPhaseType.BUILD:
            return self._select_build_workout(
                day_of_week, readiness_score, days_since_last_hard, recent_workout_types
            )

        elif phase.phase_type == TrainingPhaseType.PEAK:
            return self._select_peak_workout(
                day_of_week, readiness_score, days_to_race, recent_workout_types
            )

        elif phase.phase_type == TrainingPhaseType.TAPER:
            return self._select_taper_workout(
                day_of_week, days_to_race, recent_workout_types
            )

        elif phase.phase_type == TrainingPhaseType.RECOVERY:
            return WorkoutType.RECOVERY, 45, WorkoutPriority.BENEFICIAL

        # Default fallback
        return WorkoutType.ENDURANCE, 60, WorkoutPriority.BENEFICIAL

    def _select_base_workout(
        self,
        day_of_week: str,
        readiness_score: int,
        days_since_last_hard: int,
        recent_types: list[WorkoutType],
    ) -> tuple[WorkoutType, int, WorkoutPriority]:
        """Select workout for base phase."""
        # Base phase: Focus on volume and aerobic development
        # 80% Z2, 20% Z3-Z4

        # Weekend = long endurance
        if day_of_week in ["Saturday", "Sunday"]:
            return WorkoutType.ENDURANCE, 120, WorkoutPriority.KEY

        # Mid-week tempo if recovered
        if day_of_week in ["Wednesday", "Thursday"]:
            if readiness_score >= 75 and days_since_last_hard >= 2:
                return WorkoutType.TEMPO, 60, WorkoutPriority.IMPORTANT
            else:
                return WorkoutType.ENDURANCE, 60, WorkoutPriority.BENEFICIAL

        # Other days = easy
        return WorkoutType.RECOVERY, 45, WorkoutPriority.BENEFICIAL

    def _select_build_workout(
        self,
        day_of_week: str,
        readiness_score: int,
        days_since_last_hard: int,
        recent_types: list[WorkoutType],
    ) -> tuple[WorkoutType, int, WorkoutPriority]:
        """Select workout for build phase."""
        # Build phase: Add intensity
        # Key workouts: Threshold, VO2max

        # Weekend = long endurance
        if day_of_week == "Sunday":
            return WorkoutType.ENDURANCE, 120, WorkoutPriority.KEY

        # Saturday = tempo or threshold
        if day_of_week == "Saturday":
            if readiness_score >= 80 and days_since_last_hard >= 2:
                return WorkoutType.THRESHOLD, 60, WorkoutPriority.KEY
            else:
                return WorkoutType.TEMPO, 75, WorkoutPriority.IMPORTANT

        # Tuesday or Thursday = intervals
        if day_of_week in ["Tuesday", "Thursday"]:
            if readiness_score >= 75 and days_since_last_hard >= 2:
                # Alternate between threshold and VO2max
                if WorkoutType.THRESHOLD not in recent_types[-2:]:
                    return WorkoutType.THRESHOLD, 60, WorkoutPriority.KEY
                else:
                    return WorkoutType.VO2MAX, 45, WorkoutPriority.KEY
            else:
                return WorkoutType.TEMPO, 60, WorkoutPriority.BENEFICIAL

        # Recovery days
        return WorkoutType.RECOVERY, 45, WorkoutPriority.BENEFICIAL

    def _select_peak_workout(
        self,
        day_of_week: str,
        readiness_score: int,
        days_to_race: int | None,
        recent_types: list[WorkoutType],
    ) -> tuple[WorkoutType, int, WorkoutPriority]:
        """Select workout for peak phase."""
        # Peak phase: Race-specific intensity

        # Close to race (< 10 days)
        if days_to_race and days_to_race < 10:
            return self._select_taper_workout(day_of_week, days_to_race, recent_types)

        # Weekend long run/ride with race pace segments
        if day_of_week == "Sunday":
            return WorkoutType.ENDURANCE, 90, WorkoutPriority.KEY

        # Saturday = race pace or threshold
        if day_of_week == "Saturday":
            if readiness_score >= 80:
                return WorkoutType.RACE_PACE, 60, WorkoutPriority.KEY
            else:
                return WorkoutType.TEMPO, 60, WorkoutPriority.IMPORTANT

        # Mid-week intensity
        if day_of_week in ["Tuesday", "Thursday"]:
            if readiness_score >= 80 and WorkoutType.VO2MAX not in recent_types[-2:]:
                return WorkoutType.VO2MAX, 45, WorkoutPriority.KEY
            elif readiness_score >= 75:
                return WorkoutType.THRESHOLD, 60, WorkoutPriority.IMPORTANT
            else:
                return WorkoutType.TEMPO, 45, WorkoutPriority.BENEFICIAL

        # Recovery
        return WorkoutType.RECOVERY, 45, WorkoutPriority.BENEFICIAL

    def _select_taper_workout(
        self,
        day_of_week: str,
        days_to_race: int | None,
        recent_types: list[WorkoutType],
    ) -> tuple[WorkoutType, int, WorkoutPriority]:
        """Select workout for taper phase."""
        # Taper: Reduce volume, maintain intensity

        # Very close to race (< 4 days)
        if days_to_race and days_to_race <= 3:
            return WorkoutType.RECOVERY, 30, WorkoutPriority.IMPORTANT

        # 4-7 days out: short openers
        if days_to_race and days_to_race <= 7:
            if day_of_week in ["Tuesday", "Thursday"]:
                return WorkoutType.SPEED, 30, WorkoutPriority.KEY  # Short openers
            else:
                return WorkoutType.RECOVERY, 30, WorkoutPriority.BENEFICIAL

        # 8-14 days out: reduced volume with some intensity
        if day_of_week in ["Wednesday", "Friday"]:
            return WorkoutType.TEMPO, 40, WorkoutPriority.IMPORTANT
        else:
            return WorkoutType.RECOVERY, 40, WorkoutPriority.BENEFICIAL

    def select_weekly_schedule(
        self,
        phase: TrainingPhase,
        week_start_date: date,
        average_readiness: int,
        available_days: list[str] | None = None,
        sport: Sport = Sport.RUNNING,
    ) -> list[dict[str, Any]]:
        """
        Generate a full week's workout schedule.

        Args:
            phase: Current training phase
            week_start_date: Start date of week (Monday)
            average_readiness: Average readiness score for planning
            available_days: Days athlete can train (defaults to all)
            sport: Primary sport

        Returns:
            List of workout dictionaries with date, type, duration, priority
        """
        if available_days is None:
            available_days = [
                "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
            ]

        schedule = []
        recent_types = []
        last_hard_day = -7  # Assume last hard workout was week before

        for day_offset in range(7):
            current_date = week_start_date + timedelta(days=day_offset)
            day_name = current_date.strftime("%A")

            if day_name not in available_days:
                continue  # Skip unavailable days

            days_since_last_hard = day_offset - last_hard_day

            # Select workout
            workout_type, duration, priority = self.select_workout_for_day(
                day_of_week=day_name,
                phase=phase,
                readiness_score=average_readiness,
                days_since_last_hard=days_since_last_hard,
                recent_workout_types=recent_types,
            )

            # Track hard workouts
            if workout_type in [WorkoutType.THRESHOLD, WorkoutType.VO2MAX, WorkoutType.SPEED]:
                last_hard_day = day_offset

            schedule.append({
                "date": current_date,
                "day_of_week": day_name,
                "workout_type": workout_type,
                "duration_minutes": duration,
                "priority": priority,
                "sport": sport,
            })

            recent_types.append(workout_type)
            if len(recent_types) > 3:
                recent_types.pop(0)

        return schedule

    def adjust_for_constraints(
        self,
        schedule: list[dict[str, Any]],
        max_weekly_hours: float | None = None,
        max_sessions_per_week: int | None = None,
        required_rest_days: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Adjust schedule to meet constraints.

        Args:
            schedule: Proposed weekly schedule
            max_weekly_hours: Maximum training hours per week
            max_sessions_per_week: Maximum number of sessions
            required_rest_days: Minimum rest days per week

        Returns:
            Adjusted schedule
        """
        # Calculate current totals
        total_minutes = sum(w["duration_minutes"] for w in schedule)
        total_hours = total_minutes / 60

        # Apply max hours constraint
        if max_weekly_hours and total_hours > max_weekly_hours:
            # Reduce durations proportionally
            reduction_factor = max_weekly_hours / total_hours
            for workout in schedule:
                workout["duration_minutes"] = int(workout["duration_minutes"] * reduction_factor)

        # Apply max sessions constraint
        if max_sessions_per_week and len(schedule) > max_sessions_per_week:
            # Remove lowest priority sessions
            schedule.sort(key=lambda w: (
                0 if w["priority"] == WorkoutPriority.KEY else
                1 if w["priority"] == WorkoutPriority.IMPORTANT else
                2 if w["priority"] == WorkoutPriority.BENEFICIAL else 3
            ))
            schedule = schedule[:max_sessions_per_week]

        # Ensure rest days
        recovery_count = sum(
            1 for w in schedule
            if w["workout_type"] == WorkoutType.RECOVERY
        )
        if recovery_count < required_rest_days:
            # Convert some beneficial sessions to recovery
            for workout in schedule:
                if recovery_count >= required_rest_days:
                    break
                if workout["priority"] == WorkoutPriority.BENEFICIAL:
                    workout["workout_type"] = WorkoutType.RECOVERY
                    workout["duration_minutes"] = 45
                    recovery_count += 1

        return schedule
