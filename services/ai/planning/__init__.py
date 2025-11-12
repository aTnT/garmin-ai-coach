"""
Dynamic Training Plan Management

Provides adaptive, goal-driven training plan generation and management.
"""

from .plan_models import (
    # Core models
    TrainingPlan,
    TrainingPhase,
    TrainingPhaseType,
    WeeklySchedule,
    PlannedWorkout,
    WorkoutCompletion,
    AdaptationDecision,
    PlanSummary,
    # Enums
    WorkoutPriority,
    CompletionQuality,
    AdaptationStatus,
    AdaptationTrigger,
    # Utilities
    VolumeRange,
    IntensityDistribution,
    # Factory functions
    create_base_phase,
    create_build_phase,
    create_peak_phase,
    create_taper_phase,
)

from .plan_storage import PlanStorage
from .activity_matcher import ActivityMatcher
from .adaptation_engine import AdaptationEngine
from .workout_selector import WorkoutSelector
from .performance_analyzer import PerformanceAnalyzer, PerformanceMetrics

__all__ = [
    # Core models
    "TrainingPlan",
    "TrainingPhase",
    "TrainingPhaseType",
    "WeeklySchedule",
    "PlannedWorkout",
    "WorkoutCompletion",
    "AdaptationDecision",
    "PlanSummary",
    # Enums
    "WorkoutPriority",
    "CompletionQuality",
    "AdaptationStatus",
    "AdaptationTrigger",
    # Utilities
    "VolumeRange",
    "IntensityDistribution",
    # Services
    "PlanStorage",
    "ActivityMatcher",
    "AdaptationEngine",
    "WorkoutSelector",
    "PerformanceAnalyzer",
    "PerformanceMetrics",
    # Factory functions
    "create_base_phase",
    "create_build_phase",
    "create_peak_phase",
    "create_taper_phase",
]
