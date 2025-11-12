"""
Workout data models and structures.

Defines structured workout sessions with intervals, zones, and coaching guidance.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Sport(Enum):
    """Sport type for workout."""

    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH = "strength"
    CROSS_TRAINING = "cross_training"


class WorkoutType(Enum):
    """Type of workout session."""

    RECOVERY = "recovery"  # Very easy, recovery focused
    ENDURANCE = "endurance"  # Long, steady aerobic
    TEMPO = "tempo"  # Sustained moderate intensity
    THRESHOLD = "threshold"  # At or near lactate threshold
    VO2MAX = "vo2max"  # High intensity intervals
    SPEED = "speed"  # Short, fast intervals
    RACE_PACE = "race_pace"  # Race-specific pacing
    BRICK = "brick"  # Multi-sport transition work


class IntensityZone(Enum):
    """Training intensity zones (5-zone model)."""

    Z1 = "z1"  # Recovery (50-60% max HR)
    Z2 = "z2"  # Endurance (60-70% max HR)
    Z3 = "z3"  # Tempo (70-80% max HR)
    Z4 = "z4"  # Threshold (80-90% max HR)
    Z5 = "z5"  # VO2max (90-100% max HR)


class Terrain(Enum):
    """Terrain type for outdoor workouts."""

    FLAT = "flat"
    ROLLING = "rolling"
    HILLY = "hilly"
    MOUNTAINOUS = "mountainous"
    INDOOR = "indoor"


@dataclass
class Interval:
    """Single interval within a workout."""

    duration_minutes: float
    intensity_zone: IntensityZone
    description: str
    target_hr_low: int | None = None
    target_hr_high: int | None = None
    target_power: int | None = None  # Watts for cycling
    target_pace: str | None = None  # e.g., "4:30 /km"
    rest_after_minutes: float = 0.0
    repetitions: int = 1
    coaching_cue: str | None = None


@dataclass
class WorkoutSegment:
    """Major segment of workout (warm-up, main set, cool-down)."""

    name: str  # "Warm-up", "Main Set", "Cool-down"
    intervals: list[Interval]
    total_duration_minutes: float = 0.0
    description: str = ""

    def __post_init__(self):
        """Calculate total duration from intervals."""
        if not self.total_duration_minutes:
            self.total_duration_minutes = sum(
                interval.duration_minutes * interval.repetitions + interval.rest_after_minutes
                for interval in self.intervals
            )


@dataclass
class StructuredWorkout:
    """Complete structured workout with all details."""

    workout_id: str
    name: str
    sport: Sport
    workout_type: WorkoutType
    duration_minutes: int
    segments: list[WorkoutSegment]

    # Intensity info
    average_intensity: IntensityZone
    peak_intensity: IntensityZone

    # Context
    goal: str  # "Improve lactate threshold", "Build aerobic base", etc.
    terrain: Terrain = Terrain.FLAT
    equipment_needed: list[str] = field(default_factory=list)

    # Guidance
    description: str = ""
    expected_adaptations: list[str] = field(default_factory=list)
    coaching_cues: list[str] = field(default_factory=list)
    alternatives_if_fatigued: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Readiness adaptation
    original_readiness: int | None = None
    adapted_for_readiness: bool = False
    readiness_modifications: list[str] = field(default_factory=list)

    def get_total_duration(self) -> float:
        """Calculate total workout duration."""
        return sum(segment.total_duration_minutes for segment in self.segments)

    def to_markdown(self) -> str:
        """Format workout as markdown."""
        lines = []

        # Header
        lines.append(f"# {self.name}")
        lines.append("")
        lines.append(f"**Sport:** {self.sport.value.title()}")
        lines.append(f"**Type:** {self.workout_type.value.replace('_', ' ').title()}")
        lines.append(f"**Duration:** {self.duration_minutes} minutes")
        lines.append(f"**Average Intensity:** Zone {self.average_intensity.value.upper()}")
        lines.append("")

        if self.description:
            lines.append(f"**Description:** {self.description}")
            lines.append("")

        # Goal
        lines.append(f"**Goal:** {self.goal}")
        lines.append("")

        # Readiness adaptation
        if self.adapted_for_readiness:
            lines.append("### 🎯 Adapted for Your Readiness")
            if self.original_readiness:
                lines.append(f"Original readiness score: {self.original_readiness}/100")
            for mod in self.readiness_modifications:
                lines.append(f"- {mod}")
            lines.append("")

        # Segments
        lines.append("## Workout Structure")
        lines.append("")

        for segment in self.segments:
            lines.append(f"### {segment.name} ({segment.total_duration_minutes:.0f} min)")
            if segment.description:
                lines.append(f"*{segment.description}*")
            lines.append("")

            for interval in segment.intervals:
                if interval.repetitions > 1:
                    lines.append(f"**{interval.repetitions}x {interval.duration_minutes:.0f} min**")
                else:
                    lines.append(f"**{interval.duration_minutes:.0f} min**")

                lines.append(f"- Zone: {interval.intensity_zone.value.upper()}")
                lines.append(f"- {interval.description}")

                if interval.target_hr_low and interval.target_hr_high:
                    lines.append(f"- Target HR: {interval.target_hr_low}-{interval.target_hr_high} bpm")
                elif interval.target_pace:
                    lines.append(f"- Target Pace: {interval.target_pace}")
                elif interval.target_power:
                    lines.append(f"- Target Power: {interval.target_power}W")

                if interval.coaching_cue:
                    lines.append(f"- 💡 *{interval.coaching_cue}*")

                if interval.rest_after_minutes > 0:
                    lines.append(f"- Recovery: {interval.rest_after_minutes:.0f} min")

                lines.append("")

        # Expected adaptations
        if self.expected_adaptations:
            lines.append("## Expected Adaptations")
            lines.append("")
            for adaptation in self.expected_adaptations:
                lines.append(f"- {adaptation}")
            lines.append("")

        # Coaching cues
        if self.coaching_cues:
            lines.append("## Coaching Cues")
            lines.append("")
            for cue in self.coaching_cues:
                lines.append(f"- {cue}")
            lines.append("")

        # Alternatives
        if self.alternatives_if_fatigued:
            lines.append("## Alternatives if Fatigued")
            lines.append("")
            for alt in self.alternatives_if_fatigued:
                lines.append(f"- {alt}")
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("## ⚠️ Important Notes")
            lines.append("")
            for warning in self.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert workout to dictionary."""
        return {
            "workout_id": self.workout_id,
            "name": self.name,
            "sport": self.sport.value,
            "workout_type": self.workout_type.value,
            "duration_minutes": self.duration_minutes,
            "average_intensity": self.average_intensity.value,
            "peak_intensity": self.peak_intensity.value,
            "goal": self.goal,
            "terrain": self.terrain.value,
            "equipment_needed": self.equipment_needed,
            "description": self.description,
            "segments": [
                {
                    "name": seg.name,
                    "duration": seg.total_duration_minutes,
                    "intervals": [
                        {
                            "duration": interval.duration_minutes,
                            "zone": interval.intensity_zone.value,
                            "description": interval.description,
                            "repetitions": interval.repetitions,
                        }
                        for interval in seg.intervals
                    ],
                }
                for seg in self.segments
            ],
            "expected_adaptations": self.expected_adaptations,
            "coaching_cues": self.coaching_cues,
            "adapted_for_readiness": self.adapted_for_readiness,
            "readiness_modifications": self.readiness_modifications,
        }


# Helper functions for serialization

def workout_to_dict(workout: StructuredWorkout) -> dict[str, Any]:
    """Convert StructuredWorkout to dict (convenience wrapper)."""
    return workout.to_dict()


def dict_to_workout(data: dict[str, Any]) -> StructuredWorkout:
    """Convert dict back to StructuredWorkout."""
    # Reconstruct segments
    segments = []
    for seg_data in data.get("segments", []):
        intervals = []
        for interval_data in seg_data.get("intervals", []):
            intervals.append(
                Interval(
                    duration_minutes=interval_data["duration"],
                    intensity_zone=IntensityZone(interval_data["zone"]),
                    description=interval_data["description"],
                    repetitions=interval_data.get("repetitions", 1),
                    rest_after_minutes=interval_data.get("rest_duration", 0),
                    target_hr_low=interval_data.get("target_hr_low"),
                    target_hr_high=interval_data.get("target_hr_high"),
                    target_power=interval_data.get("target_power"),
                    target_pace=interval_data.get("target_pace"),
                )
            )

        segments.append(
            WorkoutSegment(
                name=seg_data["name"],
                intervals=intervals,
            )
        )

    return StructuredWorkout(
        workout_id=data["workout_id"],
        name=data["name"],
        sport=Sport(data["sport"]),
        workout_type=WorkoutType(data["workout_type"]),
        duration_minutes=data["duration_minutes"],
        segments=segments,
        average_intensity=IntensityZone(data["average_intensity"]),
        peak_intensity=IntensityZone(data["peak_intensity"]),
        goal=data["goal"],
        expected_adaptations=data.get("expected_adaptations", []),
        coaching_cues=data.get("coaching_cues", []),
        terrain=Terrain(data.get("terrain", "flat")),
        equipment_needed=data.get("equipment_needed", []),
        description=data.get("description", ""),
        adapted_for_readiness=data.get("adapted_for_readiness", False),
        readiness_modifications=data.get("readiness_modifications", []),
    )
