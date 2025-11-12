"""
Training Plan Data Models

Comprehensive data structures for dynamic, adaptive training plans.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from services.ai.workouts.workout_models import StructuredWorkout, WorkoutType


class TrainingPhaseType(str, Enum):
    """Types of training phases in periodization."""

    BASE = "base"  # Aerobic foundation building
    BUILD = "build"  # Intensity and volume increase
    PEAK = "peak"  # Race-specific sharpening
    TAPER = "taper"  # Pre-race recovery
    RECOVERY = "recovery"  # Post-race or planned rest
    TRANSITION = "transition"  # Off-season
    MAINTENANCE = "maintenance"  # Fitness maintenance


class AdaptationStatus(str, Enum):
    """Status of plan adaptation."""

    ON_TRACK = "on_track"  # Executing as planned
    MINOR_ADJUSTMENT = "minor_adjustment"  # Small changes made
    MAJOR_ADAPTATION = "major_adaptation"  # Significant re-planning
    FALLING_BEHIND = "falling_behind"  # Poor completion rate
    OVERREACHING = "overreaching"  # Load too high


class AdaptationTrigger(str, Enum):
    """Reasons for plan adaptation."""

    LOW_READINESS = "low_readiness"  # Persistent low readiness scores
    MISSED_WORKOUTS = "missed_workouts"  # Key sessions skipped
    HIGH_TRAINING_LOAD = "high_training_load"  # ACWR > 1.5
    POOR_PERFORMANCE = "poor_performance"  # Declining metrics
    ILLNESS_INJURY = "illness_injury"  # User-reported issue
    LIFE_EVENT = "life_event"  # Travel, work, family
    AHEAD_OF_SCHEDULE = "ahead_of_schedule"  # Exceeding expectations
    RACE_CHANGE = "race_change"  # Goal race date/type changed
    MANUAL_OVERRIDE = "manual_override"  # User/coach decision


class WorkoutPriority(str, Enum):
    """Priority level for workouts."""

    KEY = "key"  # Critical session, should not be missed/moved
    IMPORTANT = "important"  # High priority but some flexibility
    BENEFICIAL = "beneficial"  # Good to do but can be skipped
    OPTIONAL = "optional"  # Nice to have, easily substituted


class CompletionQuality(str, Enum):
    """Quality of workout execution."""

    EXCELLENT = "excellent"  # Exceeded targets
    GOOD = "good"  # Met targets
    ADEQUATE = "adequate"  # Completed but struggled
    POOR = "poor"  # Completed at low quality
    PARTIAL = "partial"  # Only part completed
    SKIPPED = "skipped"  # Not attempted
    UNKNOWN = "unknown"  # No matching activity found


@dataclass
class VolumeRange:
    """Training volume range for a phase."""

    min_hours_per_week: float
    max_hours_per_week: float
    target_hours_per_week: float
    min_sessions_per_week: int
    max_sessions_per_week: int

    def contains(self, hours: float) -> bool:
        """Check if hours are within range."""
        return self.min_hours_per_week <= hours <= self.max_hours_per_week


@dataclass
class IntensityDistribution:
    """Distribution of training time across intensity zones."""

    zone1_percent: float  # Recovery
    zone2_percent: float  # Endurance
    zone3_percent: float  # Tempo
    zone4_percent: float  # Threshold
    zone5_percent: float  # VO2max/Speed

    def __post_init__(self):
        """Validate percentages sum to 100."""
        total = (
            self.zone1_percent
            + self.zone2_percent
            + self.zone3_percent
            + self.zone4_percent
            + self.zone5_percent
        )
        if abs(total - 100.0) > 0.1:
            raise ValueError(f"Intensity distribution must sum to 100%, got {total}")

    @classmethod
    def polarized(cls) -> "IntensityDistribution":
        """Create polarized training distribution (80/20 rule)."""
        return cls(
            zone1_percent=75.0,
            zone2_percent=5.0,
            zone3_percent=0.0,
            zone4_percent=5.0,
            zone5_percent=15.0,
        )

    @classmethod
    def pyramidal(cls) -> "IntensityDistribution":
        """Create pyramidal training distribution."""
        return cls(
            zone1_percent=60.0,
            zone2_percent=20.0,
            zone3_percent=10.0,
            zone4_percent=7.0,
            zone5_percent=3.0,
        )

    @classmethod
    def threshold_focused(cls) -> "IntensityDistribution":
        """Create threshold-focused distribution."""
        return cls(
            zone1_percent=50.0,
            zone2_percent=15.0,
            zone3_percent=15.0,
            zone4_percent=15.0,
            zone5_percent=5.0,
        )


@dataclass
class TrainingPhase:
    """A phase in the training plan (e.g., Base, Build, Peak)."""

    phase_id: str
    phase_type: TrainingPhaseType
    name: str  # "Base Building Phase 1"
    start_date: date
    end_date: date
    duration_weeks: int

    # Training prescription
    focus: str  # "Build aerobic base and endurance"
    volume_range: VolumeRange
    intensity_distribution: IntensityDistribution
    key_workout_types: list[WorkoutType]  # Primary workout types for this phase

    # Phase goals
    goals: list[str]  # "Increase weekly volume to 10 hours", etc.
    success_criteria: list[str]  # "Complete 80% of key workouts", etc.

    # Progression
    progression_notes: str | None = None
    transition_criteria: list[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        """Check if phase is currently active."""
        today = date.today()
        return self.start_date <= today <= self.end_date

    @property
    def days_remaining(self) -> int:
        """Days remaining in phase."""
        today = date.today()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days

    @property
    def progress_percentage(self) -> float:
        """Percentage of phase completed (0-100)."""
        total_days = (self.end_date - self.start_date).days
        elapsed_days = (date.today() - self.start_date).days
        return min(100.0, max(0.0, (elapsed_days / total_days) * 100))


@dataclass
class PlannedWorkout:
    """A planned workout in the training schedule."""

    workout_id: str
    date: date
    workout: StructuredWorkout
    priority: WorkoutPriority

    # Context
    rationale: str  # Why this workout on this day
    phase_id: str  # Which training phase this belongs to
    week_number: int  # Week number in plan

    # Adaptability
    alternative_workouts: list[StructuredWorkout] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)  # "48h since last hard", etc.
    can_reschedule: bool = True
    reschedule_window_days: int = 3

    # Execution
    completed: bool = False
    completion_date: date | None = None
    completion_quality: CompletionQuality = CompletionQuality.UNKNOWN

    @property
    def is_overdue(self) -> bool:
        """Check if workout is overdue."""
        return not self.completed and date.today() > self.date

    @property
    def days_until(self) -> int:
        """Days until scheduled (negative if past)."""
        return (self.date - date.today()).days


@dataclass
class WorkoutCompletion:
    """Records completion of a planned workout."""

    planned_workout_id: str
    completed_date: datetime
    activity_id: str | None  # Garmin activity ID

    # Quality metrics
    completion_percentage: float  # 0-100
    duration_adherence: float  # Actual duration / planned duration
    intensity_adherence: float  # How well zones were hit
    quality_rating: CompletionQuality

    # Subjective feedback
    perceived_exertion: int | None = None  # 1-10 RPE
    enjoyment: int | None = None  # 1-10
    notes: str | None = None

    # Performance indicators
    average_hr: int | None = None
    average_power: float | None = None
    average_pace: str | None = None
    total_tss: float | None = None  # Training Stress Score


@dataclass
class WeeklySchedule:
    """A week in the training plan."""

    week_number: int
    start_date: date
    end_date: date
    phase_id: str

    # Planned workouts
    planned_workouts: list[PlannedWorkout]

    # Weekly targets
    target_volume_hours: float
    target_tss: float | None = None
    key_sessions: list[str] = field(default_factory=list)  # IDs of key workouts

    # Execution tracking
    completed_workouts: list[WorkoutCompletion] = field(default_factory=list)
    actual_volume_hours: float = 0.0
    actual_tss: float = 0.0

    # Status
    adaptation_status: AdaptationStatus = AdaptationStatus.ON_TRACK
    adaptations_made: list[str] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        """Percentage of workouts completed (0-100)."""
        if not self.planned_workouts:
            return 0.0
        completed = sum(1 for w in self.planned_workouts if w.completed)
        return (completed / len(self.planned_workouts)) * 100

    @property
    def key_workout_completion_rate(self) -> float:
        """Percentage of key workouts completed."""
        key_workouts = [w for w in self.planned_workouts if w.priority == WorkoutPriority.KEY]
        if not key_workouts:
            return 100.0
        completed = sum(1 for w in key_workouts if w.completed)
        return (completed / len(key_workouts)) * 100

    @property
    def volume_adherence(self) -> float:
        """Actual volume / target volume."""
        if self.target_volume_hours == 0:
            return 0.0
        return self.actual_volume_hours / self.target_volume_hours


@dataclass
class AdaptationDecision:
    """Records a decision to adapt the training plan."""

    adaptation_id: str
    timestamp: datetime
    trigger: AdaptationTrigger
    trigger_details: str

    # What changed
    affected_workouts: list[str]  # Workout IDs
    original_plan_summary: str
    adapted_plan_summary: str

    # Rationale
    reasoning: str
    confidence: float  # 0-1

    # Approval
    requires_approval: bool = False
    approved: bool | None = None
    approved_by: str | None = None
    approval_timestamp: datetime | None = None


@dataclass
class TrainingPlan:
    """Complete training plan for an athlete."""

    plan_id: str
    athlete_id: str
    athlete_name: str

    # Timeline
    created_date: datetime
    start_date: date
    end_date: date
    last_updated: datetime

    # Goals
    primary_goal: dict[str, Any]  # Competition dict
    secondary_goals: list[dict[str, Any]] = field(default_factory=list)
    target_metrics: dict[str, Any] = field(default_factory=dict)  # "FTP": 300, etc.

    # Periodization
    phases: list[TrainingPhase]
    current_phase_id: str | None = None

    # Schedule
    weekly_schedules: list[WeeklySchedule] = field(default_factory=list)

    # Adaptation
    adaptations: list[AdaptationDecision] = field(default_factory=list)
    adaptation_enabled: bool = True
    adaptation_sensitivity: float = 1.0  # 0.5 (conservative) to 2.0 (aggressive)

    # Metadata
    version: int = 1
    season_plan_text: str | None = None  # Original LLM season plan
    notes: str | None = None

    @property
    def current_phase(self) -> TrainingPhase | None:
        """Get currently active phase."""
        if self.current_phase_id:
            return next((p for p in self.phases if p.phase_id == self.current_phase_id), None)
        # Fallback: find phase containing today
        today = date.today()
        for phase in self.phases:
            if phase.start_date <= today <= phase.end_date:
                return phase
        return None

    @property
    def current_week(self) -> WeeklySchedule | None:
        """Get current week's schedule."""
        today = date.today()
        for week in self.weekly_schedules:
            if week.start_date <= today <= week.end_date:
                return week
        return None

    @property
    def upcoming_workouts(self, days: int = 7) -> list[PlannedWorkout]:
        """Get workouts in next N days."""
        today = date.today()
        cutoff = today + timedelta(days=days)
        upcoming = []
        for week in self.weekly_schedules:
            for workout in week.planned_workouts:
                if today <= workout.date <= cutoff and not workout.completed:
                    upcoming.append(workout)
        return sorted(upcoming, key=lambda w: w.date)

    @property
    def overdue_workouts(self) -> list[PlannedWorkout]:
        """Get workouts that are past due and not completed."""
        return [
            workout
            for week in self.weekly_schedules
            for workout in week.planned_workouts
            if workout.is_overdue
        ]

    @property
    def days_to_goal(self) -> int:
        """Days until primary goal race."""
        if not self.primary_goal:
            return 0
        goal_date = self.primary_goal.get("date")
        if isinstance(goal_date, str):
            goal_date = datetime.strptime(goal_date, "%Y-%m-%d").date()
        return (goal_date - date.today()).days

    @property
    def weeks_remaining(self) -> int:
        """Weeks remaining in plan."""
        return (self.end_date - date.today()).days // 7

    @property
    def overall_completion_rate(self) -> float:
        """Overall workout completion rate across all weeks."""
        total_workouts = sum(len(w.planned_workouts) for w in self.weekly_schedules)
        if total_workouts == 0:
            return 0.0
        completed = sum(
            sum(1 for wo in w.planned_workouts if wo.completed)
            for w in self.weekly_schedules
        )
        return (completed / total_workouts) * 100

    def get_week(self, week_number: int) -> WeeklySchedule | None:
        """Get specific week by number."""
        return next((w for w in self.weekly_schedules if w.week_number == week_number), None)

    def get_workout(self, workout_id: str) -> PlannedWorkout | None:
        """Get specific workout by ID."""
        for week in self.weekly_schedules:
            for workout in week.planned_workouts:
                if workout.workout_id == workout_id:
                    return workout
        return None

    def get_phase(self, phase_id: str) -> TrainingPhase | None:
        """Get specific phase by ID."""
        return next((p for p in self.phases if p.phase_id == phase_id), None)


@dataclass
class PlanSummary:
    """Summary statistics for a training plan."""

    plan_id: str
    athlete_name: str

    # Timeline
    start_date: date
    end_date: date
    weeks_total: int
    weeks_completed: int
    weeks_remaining: int

    # Goals
    primary_goal_name: str
    days_to_goal: int

    # Current status
    current_phase_name: str
    current_week_number: int

    # Execution metrics
    overall_completion_rate: float
    key_workout_completion_rate: float
    average_weekly_volume: float
    total_adaptations: int
    recent_adaptation_triggers: list[str]

    # Readiness
    average_readiness_score: float | None = None
    readiness_trend: str | None = None  # "improving", "stable", "declining"

    # Recommendations
    current_status: AdaptationStatus
    recommendations: list[str] = field(default_factory=list)


# Helper functions for creating common patterns

def create_base_phase(
    start_date: date, duration_weeks: int, phase_number: int = 1
) -> TrainingPhase:
    """Create a standard base building phase."""
    end_date = start_date + timedelta(weeks=duration_weeks)
    return TrainingPhase(
        phase_id=f"base_{phase_number}",
        phase_type=TrainingPhaseType.BASE,
        name=f"Base Building Phase {phase_number}",
        start_date=start_date,
        end_date=end_date,
        duration_weeks=duration_weeks,
        focus="Build aerobic foundation and endurance",
        volume_range=VolumeRange(
            min_hours_per_week=5.0,
            max_hours_per_week=10.0,
            target_hours_per_week=7.5,
            min_sessions_per_week=3,
            max_sessions_per_week=5,
        ),
        intensity_distribution=IntensityDistribution.polarized(),
        key_workout_types=[WorkoutType.ENDURANCE, WorkoutType.RECOVERY],
        goals=[
            "Build aerobic base",
            "Establish consistent training routine",
            "Increase weekly volume gradually",
        ],
        success_criteria=["Complete 80% of scheduled workouts", "No injuries"],
    )


def create_build_phase(
    start_date: date, duration_weeks: int, phase_number: int = 1
) -> TrainingPhase:
    """Create a standard build phase."""
    end_date = start_date + timedelta(weeks=duration_weeks)
    return TrainingPhase(
        phase_id=f"build_{phase_number}",
        phase_type=TrainingPhaseType.BUILD,
        name=f"Build Phase {phase_number}",
        start_date=start_date,
        end_date=end_date,
        duration_weeks=duration_weeks,
        focus="Increase volume and intensity, develop race-specific fitness",
        volume_range=VolumeRange(
            min_hours_per_week=8.0,
            max_hours_per_week=15.0,
            target_hours_per_week=12.0,
            min_sessions_per_week=4,
            max_sessions_per_week=6,
        ),
        intensity_distribution=IntensityDistribution.pyramidal(),
        key_workout_types=[
            WorkoutType.TEMPO,
            WorkoutType.THRESHOLD,
            WorkoutType.ENDURANCE,
        ],
        goals=[
            "Increase lactate threshold",
            "Build muscular endurance",
            "Maintain aerobic base",
        ],
        success_criteria=[
            "Complete 85% of key workouts",
            "Increase FTP by 5-10W",
        ],
    )


def create_peak_phase(start_date: date, duration_weeks: int = 3) -> TrainingPhase:
    """Create a standard peak/sharpening phase."""
    end_date = start_date + timedelta(weeks=duration_weeks)
    return TrainingPhase(
        phase_id="peak",
        phase_type=TrainingPhaseType.PEAK,
        name="Peak/Sharpening Phase",
        start_date=start_date,
        end_date=end_date,
        duration_weeks=duration_weeks,
        focus="Race-specific intensity, sharpen fitness",
        volume_range=VolumeRange(
            min_hours_per_week=8.0,
            max_hours_per_week=12.0,
            target_hours_per_week=10.0,
            min_sessions_per_week=4,
            max_sessions_per_week=5,
        ),
        intensity_distribution=IntensityDistribution.threshold_focused(),
        key_workout_types=[WorkoutType.THRESHOLD, WorkoutType.VO2MAX, WorkoutType.SPEED],
        goals=[
            "Maximize race readiness",
            "Practice race pace",
            "Build confidence",
        ],
        success_criteria=[
            "Complete all key race-pace sessions",
            "Maintain high readiness scores",
        ],
    )


def create_taper_phase(start_date: date, duration_weeks: int = 2) -> TrainingPhase:
    """Create a standard taper phase."""
    end_date = start_date + timedelta(weeks=duration_weeks)
    return TrainingPhase(
        phase_id="taper",
        phase_type=TrainingPhaseType.TAPER,
        name="Taper Phase",
        start_date=start_date,
        end_date=end_date,
        duration_weeks=duration_weeks,
        focus="Reduce volume, maintain intensity, maximize recovery",
        volume_range=VolumeRange(
            min_hours_per_week=3.0,
            max_hours_per_week=6.0,
            target_hours_per_week=4.5,
            min_sessions_per_week=3,
            max_sessions_per_week=4,
        ),
        intensity_distribution=IntensityDistribution(
            zone1_percent=60.0,
            zone2_percent=10.0,
            zone3_percent=10.0,
            zone4_percent=15.0,
            zone5_percent=5.0,
        ),
        key_workout_types=[WorkoutType.RECOVERY, WorkoutType.SPEED],
        goals=[
            "Arrive at race fully recovered",
            "Maintain sharpness with short intensity",
            "Peak on race day",
        ],
        success_criteria=[
            "High readiness scores (>85)",
            "Fresh legs feeling",
        ],
    )


from datetime import timedelta  # Add this import at the top
