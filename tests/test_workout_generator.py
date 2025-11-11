"""
Tests for Workout Generator.
"""

import pytest

from services.ai.workouts import (
    IntensityZone,
    Sport,
    Terrain,
    WorkoutGenerator,
    WorkoutType,
)


class TestWorkoutGenerator:
    """Test suite for WorkoutGenerator."""

    def test_generate_recovery_workout(self):
        """Test recovery workout generation."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=45,
            athlete_zones={"hr_max": 190},
        )

        assert workout.name == "Running Recovery Session"
        assert workout.sport == Sport.RUNNING
        assert workout.workout_type == WorkoutType.RECOVERY
        assert workout.duration_minutes == 45
        assert workout.average_intensity == IntensityZone.Z1
        assert workout.peak_intensity == IntensityZone.Z2
        assert len(workout.segments) == 1
        assert "recovery" in workout.goal.lower()

    def test_generate_endurance_workout(self):
        """Test endurance workout generation."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.CYCLING,
            workout_type=WorkoutType.ENDURANCE,
            duration_minutes=120,
            athlete_zones={"hr_max": 185},
        )

        assert workout.sport == Sport.CYCLING
        assert workout.workout_type == WorkoutType.ENDURANCE
        assert workout.duration_minutes == 120
        assert workout.average_intensity == IntensityZone.Z2
        assert len(workout.segments) == 2  # Warm-up + main
        assert "aerobic" in workout.goal.lower() or "endurance" in workout.goal.lower()

    def test_generate_tempo_workout(self):
        """Test tempo workout generation."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.TEMPO,
            duration_minutes=60,
            athlete_zones={"hr_max": 190},
        )

        assert workout.workout_type == WorkoutType.TEMPO
        assert workout.average_intensity == IntensityZone.Z3
        assert len(workout.segments) == 3  # Warm-up + tempo + cool-down
        assert any("tempo" in seg.name.lower() for seg in workout.segments)

    def test_generate_threshold_workout(self):
        """Test threshold workout generation."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            athlete_zones={"hr_max": 190, "lthr": 173},
        )

        assert workout.workout_type == WorkoutType.THRESHOLD
        assert workout.peak_intensity == IntensityZone.Z4
        assert len(workout.segments) == 3  # Warm-up + intervals + cool-down
        assert "threshold" in workout.name.lower()

        # Check intervals structure
        interval_segment = next(
            (seg for seg in workout.segments if "interval" in seg.name.lower()), None
        )
        assert interval_segment is not None
        assert len(interval_segment.intervals) > 0

    def test_generate_vo2max_workout(self):
        """Test VO2max workout generation."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.CYCLING,
            workout_type=WorkoutType.VO2MAX,
            duration_minutes=60,
            athlete_zones={"hr_max": 185},
        )

        assert workout.workout_type == WorkoutType.VO2MAX
        assert workout.peak_intensity == IntensityZone.Z5
        assert len(workout.warnings) > 0  # Should have warnings about intensity

    def test_generate_speed_workout(self):
        """Test speed workout generation."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.SPEED,
            duration_minutes=60,
        )

        assert workout.workout_type == WorkoutType.SPEED
        assert workout.peak_intensity == IntensityZone.Z5
        assert "speed" in workout.name.lower()

    def test_workout_with_terrain(self):
        """Test workout with terrain specification."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.ENDURANCE,
            duration_minutes=90,
            terrain=Terrain.HILLY,
        )

        assert workout.terrain == Terrain.HILLY

    def test_workout_with_equipment(self):
        """Test workout with equipment list."""
        generator = WorkoutGenerator()

        equipment = ["heart rate monitor", "power meter"]
        workout = generator.generate_workout(
            sport=Sport.CYCLING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            equipment_available=equipment,
        )

        assert workout.equipment_needed == equipment

    def test_readiness_adaptation_rest(self):
        """Test workout adaptation for REST readiness (score < 40)."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            readiness_score=35,
        )

        assert workout.adapted_for_readiness
        assert workout.original_readiness == 35
        assert len(workout.readiness_modifications) > 0
        assert any("REST" in mod or "rest" in mod for mod in workout.readiness_modifications)
        assert len(workout.warnings) > 0

    def test_readiness_adaptation_easy(self):
        """Test workout adaptation for EASY readiness (score 40-54)."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            readiness_score=48,
        )

        assert workout.adapted_for_readiness
        assert workout.original_readiness == 48
        # Should be converted to recovery
        assert workout.workout_type == WorkoutType.RECOVERY
        assert workout.average_intensity == IntensityZone.Z1

    def test_readiness_adaptation_moderate(self):
        """Test workout adaptation for MODERATE readiness (score 55-69)."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            athlete_zones={"hr_max": 190},
            readiness_score=62,
        )

        assert workout.adapted_for_readiness
        assert workout.original_readiness == 62

        # Should reduce intervals
        interval_segment = next(
            (seg for seg in workout.segments if "interval" in seg.name.lower()), None
        )
        if interval_segment:
            # Check that modifications mention reduction
            assert any(
                "reduce" in mod.lower() or "adjusted" in mod.lower()
                for mod in workout.readiness_modifications
            )

    def test_readiness_adaptation_normal(self):
        """Test workout adaptation for NORMAL readiness (score 70-84)."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.ENDURANCE,
            duration_minutes=90,
            readiness_score=75,
        )

        assert workout.adapted_for_readiness
        assert workout.original_readiness == 75
        # Should proceed as planned
        assert any("good" in mod.lower() or "proceed" in mod.lower() for mod in workout.readiness_modifications)

    def test_readiness_adaptation_peak(self):
        """Test workout adaptation for PEAK readiness (score >= 85)."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            readiness_score=92,
        )

        assert workout.adapted_for_readiness
        assert workout.original_readiness == 92
        # Should encourage quality
        assert any(
            "excellent" in mod.lower() or "peak" in mod.lower()
            for mod in workout.readiness_modifications
        )

    def test_workout_to_markdown(self):
        """Test markdown formatting."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.TEMPO,
            duration_minutes=60,
            athlete_zones={"hr_max": 190},
        )

        markdown = workout.to_markdown()

        assert workout.name in markdown
        assert "Sport:" in markdown
        assert "Duration:" in markdown
        assert "Workout Structure" in markdown
        assert "Expected Adaptations" in markdown
        assert "Coaching Cues" in markdown

    def test_workout_to_dict(self):
        """Test dictionary conversion."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.CYCLING,
            workout_type=WorkoutType.ENDURANCE,
            duration_minutes=120,
        )

        workout_dict = workout.to_dict()

        assert workout_dict["workout_id"] == workout.workout_id
        assert workout_dict["name"] == workout.name
        assert workout_dict["sport"] == workout.sport.value
        assert workout_dict["workout_type"] == workout.workout_type.value
        assert workout_dict["duration_minutes"] == workout.duration_minutes
        assert "segments" in workout_dict
        assert isinstance(workout_dict["segments"], list)

    def test_workout_duration_calculation(self):
        """Test total duration calculation."""
        generator = WorkoutGenerator()

        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
        )

        total_duration = workout.get_total_duration()
        assert total_duration > 0
        # Should be approximately equal to target duration (within 10%)
        assert abs(total_duration - workout.duration_minutes) / workout.duration_minutes < 0.1

    def test_different_sports_generate_successfully(self):
        """Test that all sports generate successfully."""
        generator = WorkoutGenerator()

        for sport in [Sport.RUNNING, Sport.CYCLING, Sport.SWIMMING]:
            workout = generator.generate_workout(
                sport=sport,
                workout_type=WorkoutType.ENDURANCE,
                duration_minutes=60,
            )

            assert workout.sport == sport
            assert len(workout.segments) > 0

    def test_all_workout_types_generate_successfully(self):
        """Test that all workout types generate successfully."""
        generator = WorkoutGenerator()

        workout_types = [
            WorkoutType.RECOVERY,
            WorkoutType.ENDURANCE,
            WorkoutType.TEMPO,
            WorkoutType.THRESHOLD,
            WorkoutType.VO2MAX,
            WorkoutType.SPEED,
        ]

        for wtype in workout_types:
            workout = generator.generate_workout(
                sport=Sport.RUNNING,
                workout_type=wtype,
                duration_minutes=60,
            )

            assert workout.workout_type == wtype
            assert len(workout.segments) > 0
            assert len(workout.expected_adaptations) > 0
            assert len(workout.coaching_cues) > 0

    def test_zone_calculation_with_custom_hr_max(self):
        """Test that custom HR max is used in calculations."""
        generator = WorkoutGenerator()

        hr_max = 200
        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.ENDURANCE,
            duration_minutes=60,
            athlete_zones={"hr_max": hr_max},
        )

        # Check that intervals have appropriate HR targets
        for segment in workout.segments:
            for interval in segment.intervals:
                if interval.target_hr_high:
                    # Z2 should be around 60-70% of max
                    assert interval.target_hr_high <= int(hr_max * 0.75)

    def test_lthr_used_for_threshold_workout(self):
        """Test that LTHR is used for threshold calculations."""
        generator = WorkoutGenerator()

        lthr = 175
        workout = generator.generate_workout(
            sport=Sport.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            athlete_zones={"hr_max": 190, "lthr": lthr},
        )

        # Find threshold intervals
        threshold_segment = next(
            (seg for seg in workout.segments if "threshold" in seg.name.lower()), None
        )

        if threshold_segment:
            for interval in threshold_segment.intervals:
                if interval.intensity_zone == IntensityZone.Z4:
                    # Should be around LTHR
                    if interval.target_hr_low:
                        assert abs(interval.target_hr_low - lthr) < 20


@pytest.mark.integration
class TestWorkoutIntegration:
    """Integration tests for workout generation."""

    def test_full_training_week_generation(self):
        """Test generating a full week of varied workouts."""
        generator = WorkoutGenerator()

        week_plan = [
            (Sport.RUNNING, WorkoutType.RECOVERY, 45),
            (Sport.CYCLING, WorkoutType.ENDURANCE, 120),
            (Sport.RUNNING, WorkoutType.THRESHOLD, 60),
            (Sport.SWIMMING, WorkoutType.ENDURANCE, 60),
            (Sport.RUNNING, WorkoutType.TEMPO, 75),
            (Sport.CYCLING, WorkoutType.VO2MAX, 90),
            (Sport.RUNNING, WorkoutType.ENDURANCE, 90),
        ]

        zones = {"hr_max": 190, "lthr": 173}
        workouts = []

        for sport, wtype, duration in week_plan:
            workout = generator.generate_workout(
                sport=sport,
                workout_type=wtype,
                duration_minutes=duration,
                athlete_zones=zones,
            )
            workouts.append(workout)

        assert len(workouts) == 7
        assert all(w.duration_minutes > 0 for w in workouts)
        assert all(len(w.segments) > 0 for w in workouts)

    def test_progressive_threshold_workouts(self):
        """Test generating progressive threshold workouts."""
        generator = WorkoutGenerator()

        durations = [50, 60, 70]
        zones = {"hr_max": 190, "lthr": 173}

        workouts = [
            generator.generate_workout(
                sport=Sport.RUNNING,
                workout_type=WorkoutType.THRESHOLD,
                duration_minutes=d,
                athlete_zones=zones,
            )
            for d in durations
        ]

        # Longer workouts should have more intervals or longer intervals
        assert workouts[0].duration_minutes < workouts[1].duration_minutes < workouts[2].duration_minutes

    def test_workout_with_full_readiness_progression(self):
        """Test workout adaptations across full readiness range."""
        generator = WorkoutGenerator()

        readiness_scores = [30, 50, 65, 75, 90]

        workouts = [
            generator.generate_workout(
                sport=Sport.RUNNING,
                workout_type=WorkoutType.THRESHOLD,
                duration_minutes=60,
                athlete_zones={"hr_max": 190},
                readiness_score=score,
            )
            for score in readiness_scores
        ]

        # Check adaptations are appropriate
        assert workouts[0].workout_type == WorkoutType.THRESHOLD  # Original plan
        assert workouts[1].workout_type == WorkoutType.RECOVERY  # Converted to recovery
        # Later workouts progressively less modified
        assert workouts[4].workout_type == WorkoutType.THRESHOLD  # High readiness keeps plan
