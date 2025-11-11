"""
Workout Generator

Generates sport-specific structured workouts adapted to athlete's readiness and zones.
"""

import logging
from datetime import datetime
from typing import Any

from .workout_models import (
    Interval,
    IntensityZone,
    Sport,
    StructuredWorkout,
    Terrain,
    WorkoutSegment,
    WorkoutType,
)

logger = logging.getLogger(__name__)


class WorkoutGenerator:
    """
    Generate structured workouts based on sport, type, duration, and athlete zones.

    Adapts workouts based on training readiness score and current fitness markers.
    """

    def __init__(self):
        """Initialize workout generator."""
        self.workout_counter = 0

    def generate_workout(
        self,
        sport: Sport,
        workout_type: WorkoutType,
        duration_minutes: int,
        athlete_zones: dict[str, Any] | None = None,
        readiness_score: int | None = None,
        terrain: Terrain = Terrain.FLAT,
        equipment_available: list[str] | None = None,
    ) -> StructuredWorkout:
        """
        Generate a structured workout.

        Args:
            sport: Sport type (running, cycling, swimming)
            workout_type: Type of session (recovery, endurance, threshold, etc.)
            duration_minutes: Target duration in minutes
            athlete_zones: Dict with zone information (hr_max, lthr, ftp, etc.)
            readiness_score: Current readiness score (0-100) for adaptation
            terrain: Terrain type for outdoor workouts
            equipment_available: List of available equipment

        Returns:
            StructuredWorkout with complete session details
        """
        self.workout_counter += 1
        workout_id = f"{sport.value}_{workout_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.workout_counter}"

        # Get base workout structure based on type
        if workout_type == WorkoutType.RECOVERY:
            workout = self._generate_recovery_workout(sport, duration_minutes, athlete_zones)
        elif workout_type == WorkoutType.ENDURANCE:
            workout = self._generate_endurance_workout(sport, duration_minutes, athlete_zones)
        elif workout_type == WorkoutType.TEMPO:
            workout = self._generate_tempo_workout(sport, duration_minutes, athlete_zones)
        elif workout_type == WorkoutType.THRESHOLD:
            workout = self._generate_threshold_workout(sport, duration_minutes, athlete_zones)
        elif workout_type == WorkoutType.VO2MAX:
            workout = self._generate_vo2max_workout(sport, duration_minutes, athlete_zones)
        elif workout_type == WorkoutType.SPEED:
            workout = self._generate_speed_workout(sport, duration_minutes, athlete_zones)
        else:
            # Default to endurance
            workout = self._generate_endurance_workout(sport, duration_minutes, athlete_zones)

        workout.workout_id = workout_id
        workout.terrain = terrain
        workout.equipment_needed = equipment_available or []

        # Adapt for readiness if provided
        if readiness_score is not None:
            workout = self._adapt_for_readiness(workout, readiness_score)

        logger.info(
            f"Generated {sport.value} {workout_type.value} workout: "
            f"{duration_minutes}min, readiness={readiness_score}"
        )

        return workout

    def _generate_recovery_workout(
        self, sport: Sport, duration_minutes: int, zones: dict | None
    ) -> StructuredWorkout:
        """Generate easy recovery workout."""
        hr_max = zones.get("hr_max", 190) if zones else 190
        z1_low = int(hr_max * 0.50)
        z1_high = int(hr_max * 0.60)
        z2_high = int(hr_max * 0.70)

        # All Z1-Z2
        main_interval = Interval(
            duration_minutes=duration_minutes,
            intensity_zone=IntensityZone.Z1,
            description="Very easy effort, focus on recovery",
            target_hr_low=z1_low,
            target_hr_high=z2_high,
            coaching_cue="Should be able to hold full conversation",
        )

        segments = [
            WorkoutSegment(
                name="Main Set",
                intervals=[main_interval],
                description="Continuous easy effort for active recovery",
            )
        ]

        return StructuredWorkout(
            workout_id="",
            name=f"{sport.value.title()} Recovery Session",
            sport=sport,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=duration_minutes,
            segments=segments,
            average_intensity=IntensityZone.Z1,
            peak_intensity=IntensityZone.Z2,
            goal="Active recovery and adaptation facilitation",
            description="Very easy session to promote recovery while maintaining movement patterns",
            expected_adaptations=[
                "Improved blood flow for muscle repair",
                "Nervous system recovery",
                "Maintenance of movement patterns",
            ],
            coaching_cues=[
                "Keep effort extremely low",
                "Focus on form and relaxation",
                "If breathing gets heavy, slow down",
                "Should feel refreshed, not tired, after this session",
            ],
            alternatives_if_fatigued=["Complete rest day", "Gentle walk or swim"],
        )

    def _generate_endurance_workout(
        self, sport: Sport, duration_minutes: int, zones: dict | None
    ) -> StructuredWorkout:
        """Generate long steady endurance workout."""
        hr_max = zones.get("hr_max", 190) if zones else 190
        z2_low = int(hr_max * 0.60)
        z2_high = int(hr_max * 0.70)

        # Warm-up: 10-15% of total
        warmup_duration = max(10, int(duration_minutes * 0.10))
        main_duration = duration_minutes - warmup_duration

        warmup = Interval(
            duration_minutes=warmup_duration,
            intensity_zone=IntensityZone.Z1,
            description="Gradual warm-up, start very easy",
            target_hr_low=int(hr_max * 0.50),
            target_hr_high=int(hr_max * 0.65),
            coaching_cue="First 5 minutes should feel ridiculously easy",
        )

        main_set = Interval(
            duration_minutes=main_duration,
            intensity_zone=IntensityZone.Z2,
            description="Steady aerobic effort",
            target_hr_low=z2_low,
            target_hr_high=z2_high,
            coaching_cue="Comfortable pace, breathing controlled but elevated",
        )

        segments = [
            WorkoutSegment(name="Warm-up", intervals=[warmup]),
            WorkoutSegment(
                name="Main Set",
                intervals=[main_set],
                description="Sustained aerobic work for endurance development",
            ),
        ]

        return StructuredWorkout(
            workout_id="",
            name=f"{sport.value.title()} Endurance Build",
            sport=sport,
            workout_type=WorkoutType.ENDURANCE,
            duration_minutes=duration_minutes,
            segments=segments,
            average_intensity=IntensityZone.Z2,
            peak_intensity=IntensityZone.Z2,
            goal="Build aerobic base and metabolic efficiency",
            description=f"Long steady session at aerobic intensity ({duration_minutes} min)",
            expected_adaptations=[
                "Increased mitochondrial density",
                "Improved fat oxidation",
                "Enhanced aerobic capacity",
                "Strengthened aerobic base",
            ],
            coaching_cues=[
                "Maintain steady effort throughout",
                "HR should stabilize after 15-20 minutes",
                "Don't drift into Z3 - check HR regularly",
                "Focus on efficient form as fatigue sets in",
            ],
            alternatives_if_fatigued=[
                f"Reduce to {int(duration_minutes * 0.75)} minutes",
                "Keep all Z1 if feeling very fatigued",
            ],
        )

    def _generate_tempo_workout(
        self, sport: Sport, duration_minutes: int, zones: dict | None
    ) -> StructuredWorkout:
        """Generate tempo workout (sustained Z3)."""
        hr_max = zones.get("hr_max", 190) if zones else 190
        z2_low = int(hr_max * 0.60)
        z2_high = int(hr_max * 0.70)
        z3_low = int(hr_max * 0.70)
        z3_high = int(hr_max * 0.80)

        # Structure: Warm-up 15min, Tempo 20-40min, Cool-down 10min
        warmup_duration = 15
        cooldown_duration = 10
        tempo_duration = min(duration_minutes - warmup_duration - cooldown_duration, 40)

        if tempo_duration < 15:
            tempo_duration = max(15, duration_minutes - 20)
            warmup_duration = (duration_minutes - tempo_duration) // 2
            cooldown_duration = duration_minutes - tempo_duration - warmup_duration

        warmup_intervals = [
            Interval(
                duration_minutes=warmup_duration - 3,
                intensity_zone=IntensityZone.Z1,
                description="Easy warm-up",
                target_hr_high=z2_high,
            ),
            Interval(
                duration_minutes=1,
                intensity_zone=IntensityZone.Z3,
                description="Short build to tempo",
                repetitions=3,
                rest_after_minutes=1,
                coaching_cue="Progressive build each rep",
            ),
        ]

        tempo_interval = Interval(
            duration_minutes=tempo_duration,
            intensity_zone=IntensityZone.Z3,
            description="Sustained tempo effort",
            target_hr_low=z3_low,
            target_hr_high=z3_high,
            coaching_cue="Comfortably hard - could sustain for an hour if needed",
        )

        cooldown = Interval(
            duration_minutes=cooldown_duration,
            intensity_zone=IntensityZone.Z1,
            description="Easy cool-down",
            target_hr_high=z2_high,
        )

        segments = [
            WorkoutSegment(name="Warm-up", intervals=warmup_intervals),
            WorkoutSegment(
                name="Tempo Block",
                intervals=[tempo_interval],
                description="Sustained moderate-hard effort",
            ),
            WorkoutSegment(name="Cool-down", intervals=[cooldown]),
        ]

        return StructuredWorkout(
            workout_id="",
            name=f"{sport.value.title()} Tempo Session",
            sport=sport,
            workout_type=WorkoutType.TEMPO,
            duration_minutes=duration_minutes,
            segments=segments,
            average_intensity=IntensityZone.Z3,
            peak_intensity=IntensityZone.Z3,
            goal="Improve aerobic power and tempo endurance",
            description=f"{tempo_duration}-minute sustained tempo effort",
            expected_adaptations=[
                "Increased aerobic power at submaximal intensity",
                "Improved lactate buffering",
                "Enhanced mental toughness",
            ],
            coaching_cues=[
                "Effort should feel 'comfortably hard'",
                "Breathing elevated but controlled",
                "Should be able to speak short sentences",
                "Focus on staying relaxed despite effort",
            ],
            alternatives_if_fatigued=[
                f"Reduce tempo block to {int(tempo_duration * 0.75)} minutes",
                "Break into 2x half duration with 5min recovery",
            ],
        )

    def _generate_threshold_workout(
        self, sport: Sport, duration_minutes: int, zones: dict | None
    ) -> StructuredWorkout:
        """Generate lactate threshold interval workout."""
        hr_max = zones.get("hr_max", 190) if zones else 190
        lthr = zones.get("lthr", int(hr_max * 0.85)) if zones else int(hr_max * 0.85)
        z4_low = int(lthr * 0.95)
        z4_high = int(lthr * 1.02)

        # Warm-up 15-20min
        warmup_duration = 20
        cooldown_duration = 10
        main_duration = duration_minutes - warmup_duration - cooldown_duration

        # Determine interval structure based on duration
        if main_duration >= 32:
            # 4x 8min
            interval_count = 4
            interval_duration = 8
            recovery_duration = 2
        elif main_duration >= 24:
            # 3x 8min
            interval_count = 3
            interval_duration = 8
            recovery_duration = 2
        else:
            # 4x 5min
            interval_count = 4
            interval_duration = 5
            recovery_duration = 2

        warmup = [
            Interval(
                duration_minutes=15,
                intensity_zone=IntensityZone.Z2,
                description="Progressive warm-up",
                target_hr_high=int(hr_max * 0.70),
            ),
            Interval(
                duration_minutes=1,
                intensity_zone=IntensityZone.Z4,
                description="Threshold strides",
                repetitions=3,
                rest_after_minutes=1,
                coaching_cue="Get legs ready for threshold work",
            ),
        ]

        threshold_interval = Interval(
            duration_minutes=interval_duration,
            intensity_zone=IntensityZone.Z4,
            description=f"Threshold effort at {z4_low}-{z4_high} bpm",
            target_hr_low=z4_low,
            target_hr_high=z4_high,
            repetitions=interval_count,
            rest_after_minutes=recovery_duration,
            coaching_cue="Sustainable hard effort - could hold 20-30 minutes if continuous",
        )

        cooldown = Interval(
            duration_minutes=cooldown_duration,
            intensity_zone=IntensityZone.Z1,
            description="Easy cool-down",
            target_hr_high=int(hr_max * 0.65),
        )

        segments = [
            WorkoutSegment(name="Warm-up", intervals=warmup),
            WorkoutSegment(
                name="Threshold Intervals",
                intervals=[threshold_interval],
                description=f"{interval_count}x {interval_duration}min at threshold",
            ),
            WorkoutSegment(name="Cool-down", intervals=[cooldown]),
        ]

        return StructuredWorkout(
            workout_id="",
            name=f"{sport.value.title()} Threshold Development",
            sport=sport,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=duration_minutes,
            segments=segments,
            average_intensity=IntensityZone.Z3,
            peak_intensity=IntensityZone.Z4,
            goal="Improve lactate threshold and sustainable pace",
            description=f"{interval_count}x {interval_duration}min threshold intervals",
            expected_adaptations=[
                "Improved lactate clearance capacity",
                "Enhanced sustainable race pace",
                "Increased aerobic power at threshold",
                "Better mental resilience at high efforts",
            ],
            coaching_cues=[
                "First interval should feel 'comfortably hard'",
                "Hold consistent effort across all intervals",
                "If HR drifts >5 bpm above target, ease off slightly",
                "Focus on smooth, efficient form",
                "Recovery should be active but very easy",
            ],
            alternatives_if_fatigued=[
                f"Reduce to {interval_count - 1}x {interval_duration}min",
                f"Keep {interval_count} intervals but reduce to {interval_duration - 2}min each",
                "Lower target HR by 5 bpm",
            ],
            warnings=[
                "High-quality session - requires good readiness",
                "Skip if feeling unwell or overly fatigued",
                "Full recovery needed before next hard session (48-72h)",
            ],
        )

    def _generate_vo2max_workout(
        self, sport: Sport, duration_minutes: int, zones: dict | None
    ) -> StructuredWorkout:
        """Generate VO2max interval workout."""
        hr_max = zones.get("hr_max", 190) if zones else 190
        z5_low = int(hr_max * 0.90)
        z5_high = int(hr_max * 0.98)

        warmup_duration = 20
        cooldown_duration = 10
        main_duration = duration_minutes - warmup_duration - cooldown_duration

        # Typical VO2max: 5x 3-5min or 8x 2-3min
        if main_duration >= 35:
            # 5x 4min
            interval_count = 5
            interval_duration = 4
            recovery_duration = 3
        else:
            # 6x 3min
            interval_count = 6
            interval_duration = 3
            recovery_duration = 2

        warmup = [
            Interval(
                duration_minutes=15,
                intensity_zone=IntensityZone.Z2,
                description="Progressive warm-up",
                target_hr_high=int(hr_max * 0.70),
            ),
            Interval(
                duration_minutes=0.5,
                intensity_zone=IntensityZone.Z5,
                description="Short surges",
                repetitions=4,
                rest_after_minutes=1,
                coaching_cue="Wake up the legs",
            ),
        ]

        vo2max_interval = Interval(
            duration_minutes=interval_duration,
            intensity_zone=IntensityZone.Z5,
            description=f"Hard effort at VO2max",
            target_hr_low=z5_low,
            target_hr_high=z5_high,
            repetitions=interval_count,
            rest_after_minutes=recovery_duration,
            coaching_cue="Hard but controlled - not a sprint",
        )

        cooldown = Interval(
            duration_minutes=cooldown_duration,
            intensity_zone=IntensityZone.Z1,
            description="Easy cool-down",
        )

        segments = [
            WorkoutSegment(name="Warm-up", intervals=warmup),
            WorkoutSegment(
                name="VO2max Intervals",
                intervals=[vo2max_interval],
                description=f"{interval_count}x {interval_duration}min at VO2max intensity",
            ),
            WorkoutSegment(name="Cool-down", intervals=[cooldown]),
        ]

        return StructuredWorkout(
            workout_id="",
            name=f"{sport.value.title()} VO2max Development",
            sport=sport,
            workout_type=WorkoutType.VO2MAX,
            duration_minutes=duration_minutes,
            segments=segments,
            average_intensity=IntensityZone.Z4,
            peak_intensity=IntensityZone.Z5,
            goal="Improve maximal aerobic capacity",
            description=f"{interval_count}x {interval_duration}min VO2max intervals",
            expected_adaptations=[
                "Increased VO2max",
                "Improved oxygen delivery to muscles",
                "Enhanced high-intensity endurance",
                "Better lactate tolerance",
            ],
            coaching_cues=[
                "Effort should be hard but sustainable for interval duration",
                "HR will climb during each interval - this is normal",
                "Focus on breathing deeply and rhythmically",
                "Recovery should be very easy - don't rush",
                "Last intervals will be toughest - embrace the challenge",
            ],
            alternatives_if_fatigued=[
                f"Reduce to {interval_count - 2} intervals",
                "Increase recovery to 4 minutes between intervals",
                "Lower target intensity slightly (Z4 instead of Z5)",
            ],
            warnings=[
                "Very high intensity - excellent readiness required",
                "Not for beginners or during high fatigue",
                "Requires 72h+ recovery before next hard session",
            ],
        )

    def _generate_speed_workout(
        self, sport: Sport, duration_minutes: int, zones: dict | None
    ) -> StructuredWorkout:
        """Generate speed/anaerobic workout."""
        # Speed work: short, very fast intervals
        warmup_duration = 25
        cooldown_duration = 10
        main_duration = duration_minutes - warmup_duration - cooldown_duration

        # 8-12x 30-90sec @ >VO2max with full recovery
        interval_count = 10
        interval_duration = 1.0
        recovery_duration = 3

        warmup = [
            Interval(
                duration_minutes=15,
                intensity_zone=IntensityZone.Z2,
                description="Easy warm-up",
            ),
            Interval(
                duration_minutes=0.5,
                intensity_zone=IntensityZone.Z4,
                description="Progressive build",
                repetitions=4,
                rest_after_minutes=1,
            ),
            Interval(
                duration_minutes=0.25,
                intensity_zone=IntensityZone.Z5,
                description="Fast strides",
                repetitions=4,
                rest_after_minutes=1,
                coaching_cue="Near-max effort to prime neuromuscular system",
            ),
        ]

        speed_interval = Interval(
            duration_minutes=interval_duration,
            intensity_zone=IntensityZone.Z5,
            description="Very fast, near-maximal effort",
            repetitions=interval_count,
            rest_after_minutes=recovery_duration,
            coaching_cue="Fast but not all-out sprint - focus on form",
        )

        cooldown = Interval(
            duration_minutes=cooldown_duration,
            intensity_zone=IntensityZone.Z1,
            description="Easy cool-down",
        )

        segments = [
            WorkoutSegment(name="Warm-up", intervals=warmup),
            WorkoutSegment(
                name="Speed Intervals",
                intervals=[speed_interval],
                description=f"{interval_count}x {interval_duration}min speed work",
            ),
            WorkoutSegment(name="Cool-down", intervals=[cooldown]),
        ]

        return StructuredWorkout(
            workout_id="",
            name=f"{sport.value.title()} Speed Development",
            sport=sport,
            workout_type=WorkoutType.SPEED,
            duration_minutes=duration_minutes,
            segments=segments,
            average_intensity=IntensityZone.Z3,
            peak_intensity=IntensityZone.Z5,
            goal="Improve neuromuscular power and speed",
            description=f"{interval_count}x {interval_duration}min speed intervals",
            expected_adaptations=[
                "Improved neuromuscular coordination",
                "Enhanced anaerobic capacity",
                "Better top-end speed",
                "Increased running economy / cycling efficiency",
            ],
            coaching_cues=[
                "Focus on perfect form at high speed",
                "Fast but not all-out sprinting",
                "Quick, light, efficient movements",
                "Full recovery between intervals - walk if needed",
                "Stop if form degrades",
            ],
            alternatives_if_fatigued=[
                "Reduce to 6-8 intervals",
                "Extend recovery to 4-5 minutes",
                "Skip entirely if legs feel heavy",
            ],
            warnings=[
                "High injury risk if fatigued",
                "Requires excellent warm-up",
                "Not recommended during high training load",
            ],
        )

    def _adapt_for_readiness(
        self, workout: StructuredWorkout, readiness_score: int
    ) -> StructuredWorkout:
        """
        Adapt workout based on readiness score.

        Args:
            workout: Original workout structure
            readiness_score: Readiness score (0-100)

        Returns:
            Adapted workout with modifications noted
        """
        workout.original_readiness = readiness_score
        workout.adapted_for_readiness = True
        modifications = []

        if readiness_score < 40:
            # REST recommendation
            modifications.append(
                f"⚠️ Readiness {readiness_score}/100 suggests REST. Consider skipping this session."
            )
            modifications.append("Alternative: Very easy recovery session or complete rest")
            workout.warnings.append(
                f"Original readiness score ({readiness_score}/100) suggests this workout may be too demanding"
            )

        elif readiness_score < 55:
            # EASY recommendation - major modifications
            modifications.append(
                f"⚠️ Readiness {readiness_score}/100 suggests EASY day. Workout significantly modified."
            )

            if workout.workout_type != WorkoutType.RECOVERY:
                modifications.append("Converted to easy recovery session")
                workout.name = f"{workout.sport.value.title()} Modified Recovery (Readiness-Adapted)"
                workout.workout_type = WorkoutType.RECOVERY
                workout.average_intensity = IntensityZone.Z1
                workout.peak_intensity = IntensityZone.Z2

                # Simplify to single easy interval
                easy_duration = min(workout.duration_minutes, 45)
                workout.segments = [
                    WorkoutSegment(
                        name="Easy Recovery",
                        intervals=[
                            Interval(
                                duration_minutes=easy_duration,
                                intensity_zone=IntensityZone.Z1,
                                description="Very easy recovery effort",
                                coaching_cue="Keep HR below aerobic threshold",
                            )
                        ],
                    )
                ]
                workout.duration_minutes = easy_duration

        elif readiness_score < 70:
            # MODERATE recommendation - reduce intensity/volume
            modifications.append(
                f"⚠️ Readiness {readiness_score}/100 suggests MODERATE training. Workout adjusted."
            )

            if workout.workout_type in [WorkoutType.THRESHOLD, WorkoutType.VO2MAX, WorkoutType.SPEED]:
                modifications.append("Reduced interval count by 25-30%")
                modifications.append("Extended recovery periods")

                # Reduce intervals in main set
                for segment in workout.segments:
                    if "interval" in segment.name.lower() or "main" in segment.name.lower():
                        for interval in segment.intervals:
                            if interval.repetitions > 1:
                                original_reps = interval.repetitions
                                interval.repetitions = max(1, int(interval.repetitions * 0.7))
                                modifications.append(
                                    f"Reduced {segment.name} from {original_reps} to {interval.repetitions} reps"
                                )
                                interval.rest_after_minutes *= 1.3

            elif workout.workout_type == WorkoutType.ENDURANCE:
                modifications.append("Reduced duration by 15%")
                original_duration = workout.duration_minutes
                workout.duration_minutes = int(workout.duration_minutes * 0.85)
                modifications.append(f"Duration: {original_duration}min → {workout.duration_minutes}min")

                # Adjust intervals proportionally
                for segment in workout.segments:
                    for interval in segment.intervals:
                        interval.duration_minutes *= 0.85

        elif readiness_score < 85:
            # NORMAL recommendation - proceed as planned
            modifications.append(
                f"✅ Readiness {readiness_score}/100 is good. Proceed with workout as planned."
            )
            modifications.append("Monitor how you feel during warm-up and adjust if needed")

        else:
            # PEAK recommendation - opportunity for quality
            modifications.append(
                f"🚀 Readiness {readiness_score}/100 is excellent! Great day for this quality session."
            )
            modifications.append("Full execution possible - embrace the opportunity")

        workout.readiness_modifications = modifications
        return workout
