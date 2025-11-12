"""
Activity Matcher

Matches completed Garmin activities to planned workouts and assesses execution quality.
"""

from datetime import date, datetime, timedelta
from typing import Any

from services.garmin.models import Activity
from .plan_models import (
    CompletionQuality,
    PlannedWorkout,
    WorkoutCompletion,
)
from services.ai.workouts.workout_models import IntensityZone, WorkoutType


class ActivityMatcher:
    """Matches activities to planned workouts and evaluates execution."""

    # Workout type matching thresholds
    TYPE_MATCH_KEYWORDS = {
        WorkoutType.RECOVERY: ["easy", "recovery", "shake", "z1"],
        WorkoutType.ENDURANCE: ["long", "endurance", "steady", "z2", "aerobic"],
        WorkoutType.TEMPO: ["tempo", "sweetspot", "z3"],
        WorkoutType.THRESHOLD: ["threshold", "ftp", "lt", "z4"],
        WorkoutType.VO2MAX: ["vo2", "intervals", "hard", "z5", "5min"],
        WorkoutType.SPEED: ["speed", "sprint", "fast", "track"],
        WorkoutType.RACE_PACE: ["race", "pace"],
    }

    def __init__(self, matching_window_hours: int = 36):
        """
        Initialize activity matcher.

        Args:
            matching_window_hours: Time window for matching activities to workouts
        """
        self.matching_window_hours = matching_window_hours

    def match_activity_to_workout(
        self,
        planned_workout: PlannedWorkout,
        activities: list[Activity],
    ) -> WorkoutCompletion | None:
        """
        Match a Garmin activity to a planned workout.

        Args:
            planned_workout: Planned workout to match
            activities: List of activities to search

        Returns:
            WorkoutCompletion if match found, None otherwise
        """
        # Find activities within time window
        target_date = datetime.combine(planned_workout.date, datetime.min.time())
        window_start = target_date - timedelta(hours=self.matching_window_hours // 2)
        window_end = target_date + timedelta(hours=self.matching_window_hours // 2)

        candidates = [
            a for a in activities
            if window_start <= a.start_time <= window_end
            and self._sport_matches(planned_workout, a)
        ]

        if not candidates:
            return None

        # If multiple candidates, pick best match
        best_match = self._select_best_match(planned_workout, candidates)

        # Calculate completion metrics
        return self._create_completion(planned_workout, best_match)

    def match_activities_to_week(
        self,
        planned_workouts: list[PlannedWorkout],
        activities: list[Activity],
    ) -> list[WorkoutCompletion]:
        """
        Match all activities to planned workouts for a week.

        Args:
            planned_workouts: Planned workouts for the week
            activities: Available activities

        Returns:
            List of WorkoutCompletion objects
        """
        completions = []
        used_activity_ids = set()

        for workout in planned_workouts:
            # Filter out already matched activities
            available_activities = [
                a for a in activities
                if a.activity_id not in used_activity_ids
            ]

            completion = self.match_activity_to_workout(workout, available_activities)

            if completion:
                completions.append(completion)
                used_activity_ids.add(completion.activity_id)

        return completions

    def _sport_matches(self, workout: PlannedWorkout, activity: Activity) -> bool:
        """Check if activity sport matches workout sport."""
        workout_sport = workout.workout.sport.value.lower()
        activity_sport = activity.sport_type.lower()

        # Direct match
        if workout_sport == activity_sport:
            return True

        # Handle variations
        sport_equivalents = {
            "running": ["run", "trail run", "treadmill"],
            "cycling": ["bike", "ride", "indoor bike", "virtual ride"],
            "swimming": ["swim", "pool swim", "open water"],
        }

        for sport, equivalents in sport_equivalents.items():
            if workout_sport == sport and activity_sport in equivalents:
                return True

        return False

    def _select_best_match(
        self,
        workout: PlannedWorkout,
        candidates: list[Activity],
    ) -> Activity:
        """
        Select best matching activity from candidates.

        Scoring based on:
        - Time proximity to planned date
        - Duration similarity
        - Workout type match (via activity name)
        - Intensity match (via HR zones)

        Args:
            workout: Planned workout
            candidates: List of candidate activities

        Returns:
            Best matching activity
        """
        if len(candidates) == 1:
            return candidates[0]

        scores = []
        for activity in candidates:
            score = 0.0

            # Time proximity (max 30 points)
            target_time = datetime.combine(workout.date, datetime.min.time())
            time_diff_hours = abs((activity.start_time - target_time).total_seconds() / 3600)
            time_score = max(0, 30 - time_diff_hours)
            score += time_score

            # Duration similarity (max 25 points)
            planned_duration_sec = workout.workout.duration_minutes * 60
            actual_duration_sec = activity.duration_seconds
            duration_ratio = min(actual_duration_sec, planned_duration_sec) / max(
                actual_duration_sec, planned_duration_sec
            )
            score += duration_ratio * 25

            # Workout type match via name (max 25 points)
            if self._name_matches_type(activity.name, workout.workout.workout_type):
                score += 25

            # Intensity match via HR (max 20 points)
            intensity_match = self._calculate_intensity_match(workout, activity)
            score += intensity_match * 20

            scores.append((activity, score))

        # Return highest scoring activity
        return max(scores, key=lambda x: x[1])[0]

    def _name_matches_type(self, activity_name: str, workout_type: WorkoutType) -> bool:
        """Check if activity name suggests it matches workout type."""
        name_lower = activity_name.lower()
        keywords = self.TYPE_MATCH_KEYWORDS.get(workout_type, [])

        return any(keyword in name_lower for keyword in keywords)

    def _calculate_intensity_match(
        self, workout: PlannedWorkout, activity: Activity
    ) -> float:
        """
        Calculate how well activity intensity matches planned intensity.

        Returns:
            Match score 0-1
        """
        # Get average planned intensity
        planned_intensity = workout.workout.average_intensity

        # Map intensity zones to HR percentages (approximate)
        zone_to_hr_pct = {
            IntensityZone.Z1: 55,
            IntensityZone.Z2: 65,
            IntensityZone.Z3: 75,
            IntensityZone.Z4: 85,
            IntensityZone.Z5: 95,
        }

        planned_hr_pct = zone_to_hr_pct.get(planned_intensity, 70)

        # Get actual HR from activity
        if not activity.average_hr or not activity.max_hr:
            return 0.5  # Neutral score if no HR data

        # Estimate HR percentage (assuming max_hr from activity is close to true max)
        actual_hr_pct = (activity.average_hr / activity.max_hr) * 100

        # Calculate match (within 10% is good)
        hr_diff = abs(planned_hr_pct - actual_hr_pct)
        match_score = max(0, 1 - (hr_diff / 20))  # 20% diff = 0 score

        return match_score

    def _create_completion(
        self,
        planned_workout: PlannedWorkout,
        activity: Activity,
    ) -> WorkoutCompletion:
        """
        Create WorkoutCompletion from planned workout and activity.

        Args:
            planned_workout: Planned workout
            activity: Matched activity

        Returns:
            WorkoutCompletion object
        """
        # Calculate completion percentage
        planned_duration_sec = planned_workout.workout.duration_minutes * 60
        actual_duration_sec = activity.duration_seconds
        completion_pct = min(100, (actual_duration_sec / planned_duration_sec) * 100)

        # Duration adherence
        duration_adherence = actual_duration_sec / planned_duration_sec

        # Intensity adherence
        intensity_adherence = self._calculate_intensity_match(planned_workout, activity)

        # Determine quality rating
        quality = self._assess_quality(
            completion_pct, duration_adherence, intensity_adherence, activity
        )

        # Extract metrics from activity
        average_hr = activity.average_hr
        average_power = getattr(activity, "average_power", None)
        average_pace = self._format_pace(activity) if hasattr(activity, "average_speed") else None
        total_tss = self._estimate_tss(activity)

        return WorkoutCompletion(
            planned_workout_id=planned_workout.workout_id,
            completed_date=activity.start_time,
            activity_id=activity.activity_id,
            completion_percentage=completion_pct,
            duration_adherence=duration_adherence,
            intensity_adherence=intensity_adherence,
            quality_rating=quality,
            average_hr=average_hr,
            average_power=average_power,
            average_pace=average_pace,
            total_tss=total_tss,
            notes=f"Matched activity: {activity.name}",
        )

    def _assess_quality(
        self,
        completion_pct: float,
        duration_adherence: float,
        intensity_adherence: float,
        activity: Activity,
    ) -> CompletionQuality:
        """
        Assess overall quality of workout execution.

        Args:
            completion_pct: Percentage completed
            duration_adherence: Duration ratio
            intensity_adherence: Intensity match score
            activity: Activity object

        Returns:
            CompletionQuality enum
        """
        # Not completed if < 70% of planned duration
        if completion_pct < 70:
            return CompletionQuality.PARTIAL

        # Excellent: >95% duration, >0.9 intensity match
        if duration_adherence >= 0.95 and intensity_adherence >= 0.9:
            return CompletionQuality.EXCELLENT

        # Good: >85% duration, >0.75 intensity match
        if duration_adherence >= 0.85 and intensity_adherence >= 0.75:
            return CompletionQuality.GOOD

        # Adequate: >75% duration, >0.6 intensity match
        if duration_adherence >= 0.75 and intensity_adherence >= 0.6:
            return CompletionQuality.ADEQUATE

        # Otherwise poor (completed but low quality)
        return CompletionQuality.POOR

    def _format_pace(self, activity: Activity) -> str | None:
        """Format pace from activity speed."""
        if not hasattr(activity, "average_speed") or not activity.average_speed:
            return None

        # Convert m/s to min/km
        speed_mps = activity.average_speed
        if speed_mps == 0:
            return None

        pace_min_per_km = 1000 / (speed_mps * 60)
        minutes = int(pace_min_per_km)
        seconds = int((pace_min_per_km - minutes) * 60)

        return f"{minutes}:{seconds:02d}/km"

    def _estimate_tss(self, activity: Activity) -> float | None:
        """
        Estimate Training Stress Score from activity.

        TSS = (duration_hours × IF^2 × 100)
        Where IF (Intensity Factor) is estimated from HR

        Args:
            activity: Activity object

        Returns:
            Estimated TSS or None
        """
        if not activity.average_hr or not activity.duration_seconds:
            return None

        duration_hours = activity.duration_seconds / 3600

        # Estimate IF from HR (simplified)
        # Assume average_hr / max_hr as proxy for IF
        if activity.max_hr and activity.max_hr > 0:
            intensity_factor = activity.average_hr / activity.max_hr
        else:
            # Fallback: assume max HR = 190 (rough estimate)
            intensity_factor = activity.average_hr / 190

        # Calculate TSS
        tss = duration_hours * (intensity_factor ** 2) * 100

        return round(tss, 1)

    def calculate_weekly_adherence(
        self, completions: list[WorkoutCompletion]
    ) -> dict[str, float]:
        """
        Calculate overall weekly adherence metrics.

        Args:
            completions: List of workout completions for the week

        Returns:
            Dict with adherence metrics
        """
        if not completions:
            return {
                "completion_rate": 0.0,
                "average_completion_pct": 0.0,
                "average_duration_adherence": 0.0,
                "average_intensity_adherence": 0.0,
                "excellent_count": 0,
                "good_count": 0,
                "adequate_count": 0,
                "poor_count": 0,
            }

        total = len(completions)

        return {
            "completion_rate": 100.0,  # If we have completions, they were completed
            "average_completion_pct": sum(c.completion_percentage for c in completions) / total,
            "average_duration_adherence": sum(c.duration_adherence for c in completions) / total,
            "average_intensity_adherence": sum(c.intensity_adherence for c in completions) / total,
            "excellent_count": sum(1 for c in completions if c.quality_rating == CompletionQuality.EXCELLENT),
            "good_count": sum(1 for c in completions if c.quality_rating == CompletionQuality.GOOD),
            "adequate_count": sum(1 for c in completions if c.quality_rating == CompletionQuality.ADEQUATE),
            "poor_count": sum(1 for c in completions if c.quality_rating == CompletionQuality.POOR),
        }
