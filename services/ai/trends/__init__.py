"""
Historical Trends Analysis Module

Provides comprehensive analysis of performance trends over time,
including seasonal patterns, year-over-year comparisons, and trajectory analysis.
"""

from .trends_analyzer import TrendsAnalyzer
from .trends_models import (
    DataPoint,
    MetricType,
    PerformanceTrajectory,
    SeasonalPattern,
    TrendAnalysis,
    TrendDirection,
    YearOverYearComparison,
)
from .trends_plotter import TrendsPlotter

__all__ = [
    # Analyzer
    "TrendsAnalyzer",
    # Plotter
    "TrendsPlotter",
    # Models
    "DataPoint",
    "MetricType",
    "TrendDirection",
    "TrendAnalysis",
    "SeasonalPattern",
    "YearOverYearComparison",
    "PerformanceTrajectory",
]
