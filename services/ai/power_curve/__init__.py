"""
Power Curve and Critical Power Analysis Module

Provides comprehensive power/pace curve analysis and Critical Power calculations
for endurance athletes.
"""

from .power_analyzer import PowerCurveAnalyzer
from .power_models import (
    BestEffort,
    CriticalPower,
    CriticalPowerHistory,
    DurationType,
    FitnessProfile,
    FitnessSignature,
    PowerCurve,
    PowerCurveComparison,
    PowerMetric,
    TrainingZones,
)
from .power_plotter import PowerCurvePlotter

__all__ = [
    # Analyzer
    "PowerCurveAnalyzer",
    # Plotter
    "PowerCurvePlotter",
    # Models
    "BestEffort",
    "PowerCurve",
    "CriticalPower",
    "TrainingZones",
    "FitnessSignature",
    "PowerCurveComparison",
    "CriticalPowerHistory",
    # Enums
    "DurationType",
    "PowerMetric",
    "FitnessProfile",
]
