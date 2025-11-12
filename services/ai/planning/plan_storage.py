"""
Training Plan Storage and Persistence

Handles saving, loading, and versioning of training plans.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .plan_models import (
    AdaptationDecision,
    PlannedWorkout,
    PlanSummary,
    TrainingPhase,
    TrainingPlan,
    WeeklySchedule,
    WorkoutCompletion,
)
from services.ai.workouts.workout_models import StructuredWorkout


class PlanStorage:
    """Handles storage and retrieval of training plans."""

    def __init__(self, storage_dir: str | Path = "./training_plans"):
        """
        Initialize plan storage.

        Args:
            storage_dir: Directory to store plan files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories
        self.active_dir = self.storage_dir / "active"
        self.archive_dir = self.storage_dir / "archive"
        self.backups_dir = self.storage_dir / "backups"

        self.active_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)
        self.backups_dir.mkdir(exist_ok=True)

    def save_plan(
        self, plan: TrainingPlan, backup: bool = True
    ) -> Path:
        """
        Save a training plan to disk.

        Args:
            plan: TrainingPlan to save
            backup: Whether to create a backup of existing plan

        Returns:
            Path to saved file
        """
        # Backup existing plan if it exists
        if backup:
            existing_path = self.active_dir / f"{plan.plan_id}.json"
            if existing_path.exists():
                self._create_backup(plan.plan_id)

        # Convert plan to dict
        plan_dict = self._plan_to_dict(plan)

        # Save to active directory
        file_path = self.active_dir / f"{plan.plan_id}.json"
        with open(file_path, "w") as f:
            json.dump(plan_dict, f, indent=2, default=str)

        return file_path

    def load_plan(self, plan_id: str) -> TrainingPlan | None:
        """
        Load a training plan from disk.

        Args:
            plan_id: ID of plan to load

        Returns:
            TrainingPlan object or None if not found
        """
        # Try active directory first
        file_path = self.active_dir / f"{plan_id}.json"
        if not file_path.exists():
            # Try archive
            file_path = self.archive_dir / f"{plan_id}.json"
            if not file_path.exists():
                return None

        with open(file_path, "r") as f:
            plan_dict = json.load(f)

        return self._dict_to_plan(plan_dict)

    def load_active_plan(self, athlete_id: str) -> TrainingPlan | None:
        """
        Load the most recent active plan for an athlete.

        Args:
            athlete_id: Athlete ID

        Returns:
            Most recent TrainingPlan or None
        """
        # Find all plans for this athlete
        athlete_plans = []
        for file_path in self.active_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    plan_dict = json.load(f)
                if plan_dict.get("athlete_id") == athlete_id:
                    athlete_plans.append((file_path, plan_dict))
            except Exception:
                continue

        if not athlete_plans:
            return None

        # Return most recently updated plan
        latest = max(athlete_plans, key=lambda x: x[1].get("last_updated", ""))
        return self._dict_to_plan(latest[1])

    def archive_plan(self, plan_id: str) -> bool:
        """
        Move a plan from active to archive.

        Args:
            plan_id: Plan ID to archive

        Returns:
            True if successful, False otherwise
        """
        source = self.active_dir / f"{plan_id}.json"
        if not source.exists():
            return False

        destination = self.archive_dir / f"{plan_id}.json"
        source.rename(destination)
        return True

    def delete_plan(self, plan_id: str, permanent: bool = False) -> bool:
        """
        Delete a plan (archives by default).

        Args:
            plan_id: Plan ID to delete
            permanent: If True, delete permanently; if False, archive

        Returns:
            True if successful, False otherwise
        """
        file_path = self.active_dir / f"{plan_id}.json"
        if not file_path.exists():
            return False

        if permanent:
            file_path.unlink()
        else:
            self.archive_plan(plan_id)

        return True

    def list_active_plans(self) -> list[PlanSummary]:
        """
        List all active training plans.

        Returns:
            List of PlanSummary objects
        """
        summaries = []
        for file_path in self.active_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    plan_dict = json.load(f)
                summary = self._create_summary(plan_dict)
                summaries.append(summary)
            except Exception:
                continue

        return summaries

    def get_plan_history(self, plan_id: str) -> list[dict[str, Any]]:
        """
        Get version history for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            List of backup versions with timestamps
        """
        history = []
        pattern = f"{plan_id}_backup_*.json"

        for backup_file in self.backups_dir.glob(pattern):
            try:
                timestamp_str = backup_file.stem.split("_backup_")[1]
                # Restore colons that were replaced with dashes for filename safety
                # Format is: YYYY-MM-DDTHH-MM-SS, need to restore colons in time part only
                if "T" in timestamp_str:
                    date_part, time_part = timestamp_str.split("T")
                    time_part = time_part.replace("-", ":")
                    timestamp_str = f"{date_part}T{time_part}"
                timestamp = datetime.fromisoformat(timestamp_str)

                with open(backup_file, "r") as f:
                    plan_dict = json.load(f)

                history.append({
                    "timestamp": timestamp,
                    "version": plan_dict.get("version", 1),
                    "file_path": str(backup_file),
                    "adaptations": len(plan_dict.get("adaptations", [])),
                })
            except Exception:
                continue

        return sorted(history, key=lambda x: x["timestamp"], reverse=True)

    def _create_backup(self, plan_id: str) -> Path | None:
        """Create a backup of a plan."""
        source = self.active_dir / f"{plan_id}.json"
        if not source.exists():
            return None

        timestamp = datetime.now().isoformat(timespec="seconds").replace(":", "-")
        backup_name = f"{plan_id}_backup_{timestamp}.json"
        destination = self.backups_dir / backup_name

        with open(source, "r") as f:
            content = f.read()
        with open(destination, "w") as f:
            f.write(content)

        return destination

    def _plan_to_dict(self, plan: TrainingPlan) -> dict[str, Any]:
        """Convert TrainingPlan to JSON-serializable dict."""
        return {
            "plan_id": plan.plan_id,
            "athlete_id": plan.athlete_id,
            "athlete_name": plan.athlete_name,
            "created_date": plan.created_date.isoformat(),
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "last_updated": plan.last_updated.isoformat(),
            "primary_goal": plan.primary_goal,
            "secondary_goals": plan.secondary_goals,
            "target_metrics": plan.target_metrics,
            "phases": [self._phase_to_dict(p) for p in plan.phases],
            "current_phase_id": plan.current_phase_id,
            "weekly_schedules": [self._week_to_dict(w) for w in plan.weekly_schedules],
            "adaptations": [self._adaptation_to_dict(a) for a in plan.adaptations],
            "adaptation_enabled": plan.adaptation_enabled,
            "adaptation_sensitivity": plan.adaptation_sensitivity,
            "version": plan.version,
            "season_plan_text": plan.season_plan_text,
            "notes": plan.notes,
        }

    def _phase_to_dict(self, phase: TrainingPhase) -> dict[str, Any]:
        """Convert TrainingPhase to dict."""
        return {
            "phase_id": phase.phase_id,
            "phase_type": phase.phase_type.value,
            "name": phase.name,
            "start_date": phase.start_date.isoformat(),
            "end_date": phase.end_date.isoformat(),
            "duration_weeks": phase.duration_weeks,
            "focus": phase.focus,
            "volume_range": {
                "min_hours_per_week": phase.volume_range.min_hours_per_week,
                "max_hours_per_week": phase.volume_range.max_hours_per_week,
                "target_hours_per_week": phase.volume_range.target_hours_per_week,
                "min_sessions_per_week": phase.volume_range.min_sessions_per_week,
                "max_sessions_per_week": phase.volume_range.max_sessions_per_week,
            },
            "intensity_distribution": {
                "zone1_percent": phase.intensity_distribution.zone1_percent,
                "zone2_percent": phase.intensity_distribution.zone2_percent,
                "zone3_percent": phase.intensity_distribution.zone3_percent,
                "zone4_percent": phase.intensity_distribution.zone4_percent,
                "zone5_percent": phase.intensity_distribution.zone5_percent,
            },
            "key_workout_types": [wt.value for wt in phase.key_workout_types],
            "goals": phase.goals,
            "success_criteria": phase.success_criteria,
            "progression_notes": phase.progression_notes,
            "transition_criteria": phase.transition_criteria,
        }

    def _week_to_dict(self, week: WeeklySchedule) -> dict[str, Any]:
        """Convert WeeklySchedule to dict."""
        return {
            "week_number": week.week_number,
            "start_date": week.start_date.isoformat(),
            "end_date": week.end_date.isoformat(),
            "phase_id": week.phase_id,
            "planned_workouts": [self._planned_workout_to_dict(w) for w in week.planned_workouts],
            "target_volume_hours": week.target_volume_hours,
            "target_tss": week.target_tss,
            "key_sessions": week.key_sessions,
            "completed_workouts": [self._completion_to_dict(c) for c in week.completed_workouts],
            "actual_volume_hours": week.actual_volume_hours,
            "actual_tss": week.actual_tss,
            "adaptation_status": week.adaptation_status.value,
            "adaptations_made": week.adaptations_made,
        }

    def _planned_workout_to_dict(self, workout: PlannedWorkout) -> dict[str, Any]:
        """Convert PlannedWorkout to dict."""
        # Import here to avoid circular dependency
        from services.ai.workouts.workout_models import workout_to_dict

        return {
            "workout_id": workout.workout_id,
            "date": workout.date.isoformat(),
            "workout": workout_to_dict(workout.workout),
            "priority": workout.priority.value,
            "rationale": workout.rationale,
            "phase_id": workout.phase_id,
            "week_number": workout.week_number,
            "alternative_workouts": [
                workout_to_dict(w) for w in workout.alternative_workouts
            ],
            "prerequisites": workout.prerequisites,
            "can_reschedule": workout.can_reschedule,
            "reschedule_window_days": workout.reschedule_window_days,
            "completed": workout.completed,
            "completion_date": workout.completion_date.isoformat() if workout.completion_date else None,
            "completion_quality": workout.completion_quality.value,
        }

    def _completion_to_dict(self, completion: WorkoutCompletion) -> dict[str, Any]:
        """Convert WorkoutCompletion to dict."""
        return {
            "planned_workout_id": completion.planned_workout_id,
            "completed_date": completion.completed_date.isoformat(),
            "activity_id": completion.activity_id,
            "completion_percentage": completion.completion_percentage,
            "duration_adherence": completion.duration_adherence,
            "intensity_adherence": completion.intensity_adherence,
            "quality_rating": completion.quality_rating.value,
            "perceived_exertion": completion.perceived_exertion,
            "enjoyment": completion.enjoyment,
            "notes": completion.notes,
            "average_hr": completion.average_hr,
            "average_power": completion.average_power,
            "average_pace": completion.average_pace,
            "total_tss": completion.total_tss,
        }

    def _adaptation_to_dict(self, adaptation: AdaptationDecision) -> dict[str, Any]:
        """Convert AdaptationDecision to dict."""
        return {
            "adaptation_id": adaptation.adaptation_id,
            "timestamp": adaptation.timestamp.isoformat(),
            "trigger": adaptation.trigger.value,
            "trigger_details": adaptation.trigger_details,
            "affected_workouts": adaptation.affected_workouts,
            "original_plan_summary": adaptation.original_plan_summary,
            "adapted_plan_summary": adaptation.adapted_plan_summary,
            "reasoning": adaptation.reasoning,
            "confidence": adaptation.confidence,
            "requires_approval": adaptation.requires_approval,
            "approved": adaptation.approved,
            "approved_by": adaptation.approved_by,
            "approval_timestamp": adaptation.approval_timestamp.isoformat() if adaptation.approval_timestamp else None,
        }

    def _dict_to_plan(self, data: dict[str, Any]) -> TrainingPlan:
        """Convert dict to TrainingPlan."""
        # Import here to avoid circular dependency
        from services.ai.workouts.workout_models import dict_to_workout
        from .plan_models import (
            TrainingPhaseType,
            VolumeRange,
            IntensityDistribution,
            WorkoutType,
            WorkoutPriority,
            CompletionQuality,
            AdaptationStatus,
            AdaptationTrigger,
        )

        # Reconstruct phases
        phases = []
        for phase_data in data.get("phases", []):
            phases.append(
                TrainingPhase(
                    phase_id=phase_data["phase_id"],
                    phase_type=TrainingPhaseType(phase_data["phase_type"]),
                    name=phase_data["name"],
                    start_date=date.fromisoformat(phase_data["start_date"]),
                    end_date=date.fromisoformat(phase_data["end_date"]),
                    duration_weeks=phase_data["duration_weeks"],
                    focus=phase_data["focus"],
                    volume_range=VolumeRange(**phase_data["volume_range"]),
                    intensity_distribution=IntensityDistribution(**phase_data["intensity_distribution"]),
                    key_workout_types=[WorkoutType(wt) for wt in phase_data["key_workout_types"]],
                    goals=phase_data["goals"],
                    success_criteria=phase_data["success_criteria"],
                    progression_notes=phase_data.get("progression_notes"),
                    transition_criteria=phase_data.get("transition_criteria", []),
                )
            )

        # Reconstruct weekly schedules
        weekly_schedules = []
        for week_data in data.get("weekly_schedules", []):
            planned_workouts = []
            for wo_data in week_data.get("planned_workouts", []):
                planned_workouts.append(
                    PlannedWorkout(
                        workout_id=wo_data["workout_id"],
                        date=date.fromisoformat(wo_data["date"]),
                        workout=dict_to_workout(wo_data["workout"]),
                        priority=WorkoutPriority(wo_data["priority"]),
                        rationale=wo_data["rationale"],
                        phase_id=wo_data["phase_id"],
                        week_number=wo_data["week_number"],
                        alternative_workouts=[
                            dict_to_workout(w) for w in wo_data.get("alternative_workouts", [])
                        ],
                        prerequisites=wo_data.get("prerequisites", []),
                        can_reschedule=wo_data.get("can_reschedule", True),
                        reschedule_window_days=wo_data.get("reschedule_window_days", 3),
                        completed=wo_data.get("completed", False),
                        completion_date=date.fromisoformat(wo_data["completion_date"]) if wo_data.get("completion_date") else None,
                        completion_quality=CompletionQuality(wo_data.get("completion_quality", "unknown")),
                    )
                )

            completed_workouts = []
            for comp_data in week_data.get("completed_workouts", []):
                completed_workouts.append(
                    WorkoutCompletion(
                        planned_workout_id=comp_data["planned_workout_id"],
                        completed_date=datetime.fromisoformat(comp_data["completed_date"]),
                        activity_id=comp_data.get("activity_id"),
                        completion_percentage=comp_data["completion_percentage"],
                        duration_adherence=comp_data["duration_adherence"],
                        intensity_adherence=comp_data["intensity_adherence"],
                        quality_rating=CompletionQuality(comp_data["quality_rating"]),
                        perceived_exertion=comp_data.get("perceived_exertion"),
                        enjoyment=comp_data.get("enjoyment"),
                        notes=comp_data.get("notes"),
                        average_hr=comp_data.get("average_hr"),
                        average_power=comp_data.get("average_power"),
                        average_pace=comp_data.get("average_pace"),
                        total_tss=comp_data.get("total_tss"),
                    )
                )

            weekly_schedules.append(
                WeeklySchedule(
                    week_number=week_data["week_number"],
                    start_date=date.fromisoformat(week_data["start_date"]),
                    end_date=date.fromisoformat(week_data["end_date"]),
                    phase_id=week_data["phase_id"],
                    planned_workouts=planned_workouts,
                    target_volume_hours=week_data["target_volume_hours"],
                    target_tss=week_data.get("target_tss"),
                    key_sessions=week_data.get("key_sessions", []),
                    completed_workouts=completed_workouts,
                    actual_volume_hours=week_data.get("actual_volume_hours", 0.0),
                    actual_tss=week_data.get("actual_tss", 0.0),
                    adaptation_status=AdaptationStatus(week_data.get("adaptation_status", "on_track")),
                    adaptations_made=week_data.get("adaptations_made", []),
                )
            )

        # Reconstruct adaptations
        adaptations = []
        for adapt_data in data.get("adaptations", []):
            adaptations.append(
                AdaptationDecision(
                    adaptation_id=adapt_data["adaptation_id"],
                    timestamp=datetime.fromisoformat(adapt_data["timestamp"]),
                    trigger=AdaptationTrigger(adapt_data["trigger"]),
                    trigger_details=adapt_data["trigger_details"],
                    affected_workouts=adapt_data["affected_workouts"],
                    original_plan_summary=adapt_data["original_plan_summary"],
                    adapted_plan_summary=adapt_data["adapted_plan_summary"],
                    reasoning=adapt_data["reasoning"],
                    confidence=adapt_data["confidence"],
                    requires_approval=adapt_data.get("requires_approval", False),
                    approved=adapt_data.get("approved"),
                    approved_by=adapt_data.get("approved_by"),
                    approval_timestamp=datetime.fromisoformat(adapt_data["approval_timestamp"]) if adapt_data.get("approval_timestamp") else None,
                )
            )

        return TrainingPlan(
            plan_id=data["plan_id"],
            athlete_id=data["athlete_id"],
            athlete_name=data["athlete_name"],
            created_date=datetime.fromisoformat(data["created_date"]),
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            primary_goal=data["primary_goal"],
            secondary_goals=data.get("secondary_goals", []),
            target_metrics=data.get("target_metrics", {}),
            phases=phases,
            current_phase_id=data.get("current_phase_id"),
            weekly_schedules=weekly_schedules,
            adaptations=adaptations,
            adaptation_enabled=data.get("adaptation_enabled", True),
            adaptation_sensitivity=data.get("adaptation_sensitivity", 1.0),
            version=data.get("version", 1),
            season_plan_text=data.get("season_plan_text"),
            notes=data.get("notes"),
        )

    def _create_summary(self, plan_dict: dict[str, Any]) -> PlanSummary:
        """Create PlanSummary from plan dict."""
        from .plan_models import AdaptationStatus

        start_date = date.fromisoformat(plan_dict["start_date"])
        end_date = date.fromisoformat(plan_dict["end_date"])
        today = date.today()

        weeks_total = (end_date - start_date).days // 7
        weeks_completed = max(0, (today - start_date).days // 7)
        weeks_remaining = max(0, (end_date - today).days // 7)

        # Calculate completion rates
        total_workouts = 0
        completed_workouts = 0
        key_workouts = 0
        completed_key_workouts = 0

        for week_data in plan_dict.get("weekly_schedules", []):
            for wo_data in week_data.get("planned_workouts", []):
                total_workouts += 1
                if wo_data.get("completed", False):
                    completed_workouts += 1
                if wo_data.get("priority") == "key":
                    key_workouts += 1
                    if wo_data.get("completed", False):
                        completed_key_workouts += 1

        overall_completion = (completed_workouts / total_workouts * 100) if total_workouts > 0 else 0
        key_completion = (completed_key_workouts / key_workouts * 100) if key_workouts > 0 else 100

        # Current phase
        current_phase_name = "Unknown"
        for phase_data in plan_dict.get("phases", []):
            phase_start = date.fromisoformat(phase_data["start_date"])
            phase_end = date.fromisoformat(phase_data["end_date"])
            if phase_start <= today <= phase_end:
                current_phase_name = phase_data["name"]
                break

        # Current week
        current_week_number = weeks_completed + 1

        # Adaptations
        adaptations = plan_dict.get("adaptations", [])
        recent_triggers = [a["trigger"] for a in adaptations[-3:]]  # Last 3

        # Goal info
        primary_goal = plan_dict.get("primary_goal", {})
        goal_name = primary_goal.get("name", "Unknown")
        goal_date_str = primary_goal.get("date", str(end_date))
        goal_date = datetime.strptime(goal_date_str, "%Y-%m-%d").date() if isinstance(goal_date_str, str) else goal_date_str
        days_to_goal = (goal_date - today).days

        # Current status - simplified for summary
        current_status = AdaptationStatus.ON_TRACK
        if overall_completion < 70:
            current_status = AdaptationStatus.FALLING_BEHIND
        elif len(adaptations) > 5:
            current_status = AdaptationStatus.MAJOR_ADAPTATION

        return PlanSummary(
            plan_id=plan_dict["plan_id"],
            athlete_name=plan_dict["athlete_name"],
            start_date=start_date,
            end_date=end_date,
            weeks_total=weeks_total,
            weeks_completed=weeks_completed,
            weeks_remaining=weeks_remaining,
            primary_goal_name=goal_name,
            days_to_goal=days_to_goal,
            current_phase_name=current_phase_name,
            current_week_number=current_week_number,
            overall_completion_rate=overall_completion,
            key_workout_completion_rate=key_completion,
            average_weekly_volume=0.0,  # Would need to calculate from actuals
            total_adaptations=len(adaptations),
            recent_adaptation_triggers=recent_triggers,
            current_status=current_status,
            recommendations=[],
        )
