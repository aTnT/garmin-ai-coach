"""
Comprehensive tests for PlanStorage - pushing coverage from 55% to 80%+
"""

import json
import tempfile
import time
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
    TrainingPhaseType,
    TrainingPlan,
    VolumeRange,
    IntensityDistribution,
    WeeklySchedule,
    WorkoutCompletion,
    WorkoutPriority,
    WorkoutType,
)
from services.ai.planning.plan_storage import PlanStorage
from services.ai.workouts.workout_models import (
    IntensityZone,
    Interval,
    Sport,
    StructuredWorkout,
    Terrain,
    WorkoutSegment,
)


def create_test_plan(plan_id: str = "test-plan", athlete_id: str = "athlete1") -> TrainingPlan:
    """Create a test training plan with all components."""
    start_date = date.today()

    # Create phase
    phase = TrainingPhase(
        phase_id="phase-1",
        phase_type=TrainingPhaseType.BASE,
        name="Base Phase",
        start_date=start_date,
        end_date=start_date + timedelta(weeks=4),
        duration_weeks=4,
        focus="Aerobic development",
        volume_range=VolumeRange(
            min_hours_per_week=5.0,
            max_hours_per_week=10.0,
            target_hours_per_week=7.5,
            min_sessions_per_week=3,
            max_sessions_per_week=6,
        ),
        intensity_distribution=IntensityDistribution(
            zone1_percent=20,
            zone2_percent=60,
            zone3_percent=15,
            zone4_percent=5,
            zone5_percent=0,
        ),
        key_workout_types=[WorkoutType.ENDURANCE, WorkoutType.TEMPO],
        goals=["Build aerobic base"],
        success_criteria=["Complete 90% of workouts"],
    )

    # Create planned workout
    workout = StructuredWorkout(
        workout_id="wo-1",
        name="Easy Run",
        sport=Sport.RUNNING,
        workout_type=WorkoutType.ENDURANCE,
        duration_minutes=60,
        segments=[
            WorkoutSegment(
                name="Easy running",
                intervals=[
                    Interval(
                        duration_minutes=60,
                        intensity_zone=IntensityZone.Z2,
                        description="Easy aerobic pace",
                    )
                ],
            )
        ],
        average_intensity=IntensityZone.Z2,
        peak_intensity=IntensityZone.Z2,
        goal="Build aerobic base",
        description="Easy aerobic run",
    )

    planned_workout = PlannedWorkout(
        workout_id="wo-1",
        date=start_date,
        workout=workout,
        priority=WorkoutPriority.KEY,
        rationale="Build aerobic base",
        phase_id="phase-1",
        week_number=1,
    )

    # Create weekly schedule
    weekly_schedule = WeeklySchedule(
        week_number=1,
        start_date=start_date,
        end_date=start_date + timedelta(days=7),
        phase_id="phase-1",
        planned_workouts=[planned_workout],
        target_volume_hours=7.5,
    )

    # Create adaptation decision
    adaptation = AdaptationDecision(
        adaptation_id="adapt-1",
        timestamp=datetime.now(),
        trigger=AdaptationTrigger.LOW_READINESS,
        trigger_details="Readiness below 60",
        affected_workouts=["wo-1"],
        original_plan_summary="Original schedule",
        adapted_plan_summary="Reduced volume",
        reasoning="Low readiness requires recovery",
        confidence=0.85,
    )

    return TrainingPlan(
        plan_id=plan_id,
        athlete_id=athlete_id,
        athlete_name="Test Athlete",
        created_date=datetime.now(),
        start_date=start_date,
        end_date=start_date + timedelta(weeks=12),
        last_updated=datetime.now(),
        primary_goal={"name": "Test Race", "date": (start_date + timedelta(weeks=12)).isoformat()},
        secondary_goals=["Build fitness", "Stay healthy"],
        target_metrics={"ftp": 250, "vo2max": 55},
        phases=[phase],
        current_phase_id="phase-1",
        weekly_schedules=[weekly_schedule],
        adaptations=[adaptation],
        adaptation_enabled=True,
        adaptation_sensitivity=1.0,
        version=1,
        season_plan_text="Test season plan",
        notes="Test notes",
    )


class TestPlanStorageBackups:
    """Test backup functionality."""

    def test_save_with_backup_creates_backup(self):
        """Test that saving with backup=True creates a backup file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Save initial plan
            storage.save_plan(plan, backup=False)

            # Modify and save again with backup
            plan.notes = "Modified notes"
            storage.save_plan(plan, backup=True)

            # Check backup was created
            backups = list(storage.backups_dir.glob(f"{plan.plan_id}_backup_*.json"))
            assert len(backups) == 1

    def test_save_without_backup_no_backup_file(self):
        """Test that saving with backup=False doesn't create backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Save with backup=False
            storage.save_plan(plan, backup=False)

            # Check no backup created
            backups = list(storage.backups_dir.glob(f"{plan.plan_id}_backup_*.json"))
            assert len(backups) == 0

    def test_get_plan_history(self):
        """Test retrieving plan version history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Save initial version
            storage.save_plan(plan, backup=False)

            # Save multiple versions with backups
            for i in range(3):
                time.sleep(1.1)  # Ensure unique timestamps (seconds precision)
                plan.notes = f"Version {i+1}"
                plan.version = i + 1
                storage.save_plan(plan, backup=True)

            # Get history
            history = storage.get_plan_history(plan.plan_id)

            assert len(history) == 3
            assert all("timestamp" in h for h in history)
            assert all("version" in h for h in history)
            assert all("file_path" in h for h in history)
            # Should be sorted by timestamp, newest first
            assert history[0]["timestamp"] >= history[-1]["timestamp"]


class TestPlanStorageArchive:
    """Test archive and delete functionality."""

    def test_load_from_archive(self):
        """Test loading a plan from archive directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Save and archive
            storage.save_plan(plan, backup=False)
            storage.archive_plan(plan.plan_id)

            # Load from archive
            loaded = storage.load_plan(plan.plan_id)

            assert loaded is not None
            assert loaded.plan_id == plan.plan_id

    def test_load_nonexistent_plan_returns_none(self):
        """Test loading a plan that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            loaded = storage.load_plan("nonexistent-plan")

            assert loaded is None

    def test_archive_plan_success(self):
        """Test successfully archiving a plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            storage.save_plan(plan, backup=False)

            # Archive the plan
            result = storage.archive_plan(plan.plan_id)

            assert result is True
            # Check plan moved to archive
            active_path = storage.active_dir / f"{plan.plan_id}.json"
            archive_path = storage.archive_dir / f"{plan.plan_id}.json"
            assert not active_path.exists()
            assert archive_path.exists()

    def test_archive_nonexistent_plan_returns_false(self):
        """Test archiving a plan that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            result = storage.archive_plan("nonexistent-plan")

            assert result is False

    def test_delete_plan_archives_by_default(self):
        """Test that delete without permanent flag archives the plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            storage.save_plan(plan, backup=False)

            # Delete (should archive)
            result = storage.delete_plan(plan.plan_id, permanent=False)

            assert result is True
            # Check plan in archive
            active_path = storage.active_dir / f"{plan.plan_id}.json"
            archive_path = storage.archive_dir / f"{plan.plan_id}.json"
            assert not active_path.exists()
            assert archive_path.exists()

    def test_delete_plan_permanent(self):
        """Test permanently deleting a plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            storage.save_plan(plan, backup=False)

            # Delete permanently
            result = storage.delete_plan(plan.plan_id, permanent=True)

            assert result is True
            # Check plan doesn't exist anywhere
            active_path = storage.active_dir / f"{plan.plan_id}.json"
            archive_path = storage.archive_dir / f"{plan.plan_id}.json"
            assert not active_path.exists()
            assert not archive_path.exists()

    def test_delete_nonexistent_plan_returns_false(self):
        """Test deleting a plan that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            result = storage.delete_plan("nonexistent-plan")

            assert result is False


class TestPlanStorageAthleteQueries:
    """Test athlete-specific queries."""

    def test_load_active_plan_for_athlete(self):
        """Test loading the most recent active plan for an athlete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            # Create multiple plans for same athlete
            plan1 = create_test_plan("plan-1", "athlete1")
            plan1.last_updated = datetime.now() - timedelta(days=2)

            plan2 = create_test_plan("plan-2", "athlete1")
            plan2.last_updated = datetime.now() - timedelta(days=1)

            plan3 = create_test_plan("plan-3", "athlete1")
            plan3.last_updated = datetime.now()  # Most recent

            storage.save_plan(plan1, backup=False)
            storage.save_plan(plan2, backup=False)
            storage.save_plan(plan3, backup=False)

            # Load active plan for athlete
            loaded = storage.load_active_plan("athlete1")

            assert loaded is not None
            assert loaded.plan_id == "plan-3"  # Most recent

    def test_load_active_plan_no_plans_for_athlete(self):
        """Test loading active plan when athlete has no plans."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            # Create plan for different athlete
            plan = create_test_plan("plan-1", "athlete2")
            storage.save_plan(plan, backup=False)

            # Try to load for athlete1
            loaded = storage.load_active_plan("athlete1")

            assert loaded is None

    def test_load_active_plan_handles_corrupted_files(self):
        """Test that load_active_plan skips corrupted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            # Create valid plan
            plan = create_test_plan("plan-1", "athlete1")
            storage.save_plan(plan, backup=False)

            # Create corrupted file
            corrupted_path = storage.active_dir / "corrupted.json"
            corrupted_path.write_text("invalid json {{{")

            # Should still load the valid plan
            loaded = storage.load_active_plan("athlete1")

            assert loaded is not None
            assert loaded.plan_id == "plan-1"


class TestPlanStorageListPlans:
    """Test listing plans."""

    def test_list_active_plans_with_corrupted_file(self):
        """Test that list_active_plans handles corrupted files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)

            # Create valid plans
            plan1 = create_test_plan("plan-1", "athlete1")
            plan2 = create_test_plan("plan-2", "athlete2")
            storage.save_plan(plan1, backup=False)
            storage.save_plan(plan2, backup=False)

            # Create corrupted file
            corrupted_path = storage.active_dir / "corrupted.json"
            corrupted_path.write_text("invalid json")

            # List plans (should skip corrupted file)
            summaries = storage.list_active_plans()

            assert len(summaries) == 2
            plan_ids = [s.plan_id for s in summaries]
            assert "plan-1" in plan_ids
            assert "plan-2" in plan_ids


class TestPlanStorageSerialization:
    """Test full serialization and deserialization."""

    def test_serialize_plan_with_completed_workouts(self):
        """Test serializing a plan with completed workouts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Add workout completion
            completion = WorkoutCompletion(
                planned_workout_id="wo-1",
                completed_date=datetime.now(),
                activity_id="activity-123",
                completion_percentage=95.0,
                duration_adherence=0.98,
                intensity_adherence=0.92,
                quality_rating=CompletionQuality.EXCELLENT,
                perceived_exertion=7,
                enjoyment=8,
                notes="Felt great!",
                average_hr=150,
                average_power=200.0,
                average_pace=5.5,
                total_tss=85.0,
            )

            plan.weekly_schedules[0].completed_workouts.append(completion)

            # Save and load
            storage.save_plan(plan, backup=False)
            loaded = storage.load_plan(plan.plan_id)

            assert loaded is not None
            assert len(loaded.weekly_schedules[0].completed_workouts) == 1
            comp = loaded.weekly_schedules[0].completed_workouts[0]
            assert comp.activity_id == "activity-123"
            assert comp.quality_rating == CompletionQuality.EXCELLENT
            assert comp.perceived_exertion == 7
            assert comp.enjoyment == 8
            assert comp.notes == "Felt great!"

    def test_serialize_plan_with_alternative_workouts(self):
        """Test serializing a plan with alternative workouts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Add alternative workout
            alt_workout = StructuredWorkout(
                workout_id="wo-alt-1",
                name="Indoor Run",
                sport=Sport.RUNNING,
                workout_type=WorkoutType.ENDURANCE,
                duration_minutes=60,
                segments=[
                    WorkoutSegment(
                        name="Indoor running",
                        intervals=[
                            Interval(
                                duration_minutes=60,
                                intensity_zone=IntensityZone.Z2,
                                description="Easy pace",
                            )
                        ],
                    )
                ],
                average_intensity=IntensityZone.Z2,
                peak_intensity=IntensityZone.Z2,
                goal="Build aerobic base",
                description="Indoor alternative",
            )

            plan.weekly_schedules[0].planned_workouts[0].alternative_workouts.append(alt_workout)

            # Save and load
            storage.save_plan(plan, backup=False)
            loaded = storage.load_plan(plan.plan_id)

            assert loaded is not None
            workout = loaded.weekly_schedules[0].planned_workouts[0]
            assert len(workout.alternative_workouts) == 1
            assert workout.alternative_workouts[0].name == "Indoor Run"

    def test_serialize_completed_workout(self):
        """Test serializing a completed planned workout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Mark workout as completed
            workout = plan.weekly_schedules[0].planned_workouts[0]
            workout.completed = True
            workout.completion_date = date.today()
            workout.completion_quality = CompletionQuality.GOOD

            # Save and load
            storage.save_plan(plan, backup=False)
            loaded = storage.load_plan(plan.plan_id)

            assert loaded is not None
            loaded_workout = loaded.weekly_schedules[0].planned_workouts[0]
            assert loaded_workout.completed is True
            assert loaded_workout.completion_date == date.today()
            assert loaded_workout.completion_quality == CompletionQuality.GOOD

    def test_serialize_adaptation_with_approval(self):
        """Test serializing an adaptation decision with approval info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Update adaptation with approval
            adaptation = plan.adaptations[0]
            adaptation.requires_approval = True
            adaptation.approved = True
            adaptation.approved_by = "coach@example.com"
            adaptation.approval_timestamp = datetime.now()

            # Save and load
            storage.save_plan(plan, backup=False)
            loaded = storage.load_plan(plan.plan_id)

            assert loaded is not None
            adapt = loaded.adaptations[0]
            assert adapt.requires_approval is True
            assert adapt.approved is True
            assert adapt.approved_by == "coach@example.com"
            assert adapt.approval_timestamp is not None


class TestPlanSummaryGeneration:
    """Test plan summary generation."""

    def test_create_summary_calculates_completion_rates(self):
        """Test that summary correctly calculates completion rates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Add multiple workouts with some completed
            for i in range(10):
                workout = PlannedWorkout(
                    workout_id=f"wo-{i}",
                    date=date.today() + timedelta(days=i),
                    workout=StructuredWorkout(
                        workout_id=f"wo-struct-{i}",
                        name=f"Workout {i}",
                        sport=Sport.RUNNING,
                        workout_type=WorkoutType.ENDURANCE,
                        duration_minutes=60,
                        segments=[
                            WorkoutSegment(
                                name="Training run",
                                intervals=[
                                    Interval(
                                        duration_minutes=60,
                                        intensity_zone=IntensityZone.Z2,
                                        description="Steady pace",
                                    )
                                ],
                            )
                        ],
                        average_intensity=IntensityZone.Z2,
                        peak_intensity=IntensityZone.Z2,
                        goal="Training",
                    ),
                    priority=WorkoutPriority.KEY if i % 2 == 0 else WorkoutPriority.BENEFICIAL,
                    rationale="Training",
                    phase_id="phase-1",
                    week_number=1,
                    completed=(i < 7),  # 7 out of 10 completed (70%)
                )
                plan.weekly_schedules[0].planned_workouts.append(workout)

            # Save and list
            storage.save_plan(plan, backup=False)
            summaries = storage.list_active_plans()

            assert len(summaries) == 1
            summary = summaries[0]
            # 7 completed out of 11 total (1 original unmarked + 10 new, 7 of 10 marked completed)
            # = 63.6%
            assert 60 <= summary.overall_completion_rate <= 70

    def test_create_summary_identifies_current_phase(self):
        """Test that summary correctly identifies current phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Add another phase in the future
            future_phase = TrainingPhase(
                phase_id="phase-2",
                phase_type=TrainingPhaseType.BUILD,
                name="Build Phase",
                start_date=date.today() + timedelta(weeks=5),
                end_date=date.today() + timedelta(weeks=9),
                duration_weeks=4,
                focus="Intensity",
                volume_range=VolumeRange(
                    min_hours_per_week=6.0,
                    max_hours_per_week=12.0,
                    target_hours_per_week=9.0,
                    min_sessions_per_week=4,
                    max_sessions_per_week=7,
                ),
                intensity_distribution=IntensityDistribution(
                    zone1_percent=15,
                    zone2_percent=50,
                    zone3_percent=20,
                    zone4_percent=10,
                    zone5_percent=5,
                ),
                key_workout_types=[WorkoutType.THRESHOLD, WorkoutType.VO2MAX],
                goals=["Build race fitness"],
                success_criteria=["Complete key workouts"],
            )
            plan.phases.append(future_phase)

            # Save and list
            storage.save_plan(plan, backup=False)
            summaries = storage.list_active_plans()

            assert len(summaries) == 1
            summary = summaries[0]
            assert summary.current_phase_name == "Base Phase"  # Current phase

    def test_create_summary_adaptation_status(self):
        """Test that summary determines adaptation status correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PlanStorage(tmpdir)
            plan = create_test_plan()

            # Mark workout as completed to avoid FALLING_BEHIND status
            plan.weekly_schedules[0].planned_workouts[0].completed = True

            # Add many adaptations to trigger MAJOR_ADAPTATION status
            for i in range(6):
                adaptation = AdaptationDecision(
                    adaptation_id=f"adapt-{i}",
                    timestamp=datetime.now() - timedelta(days=i),
                    trigger=AdaptationTrigger.LOW_READINESS,
                    trigger_details=f"Adaptation {i}",
                    affected_workouts=[],
                    original_plan_summary="Original",
                    adapted_plan_summary="Adapted",
                    reasoning="Test",
                    confidence=0.8,
                )
                plan.adaptations.append(adaptation)

            # Save and list
            storage.save_plan(plan, backup=False)
            summaries = storage.list_active_plans()

            assert len(summaries) == 1
            summary = summaries[0]
            # 7 total adaptations (1 original + 6 new) should trigger MAJOR_ADAPTATION
            assert summary.current_status == AdaptationStatus.MAJOR_ADAPTATION
            assert summary.total_adaptations == 7
