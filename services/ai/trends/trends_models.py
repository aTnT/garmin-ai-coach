"""
Historical Performance Trends Models

Data structures for tracking long-term performance progression.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class TrendDirection(Enum):
    """Direction of trend over time."""

    IMPROVING = "improving"  # Positive trend
    STABLE = "stable"  # No significant change
    DECLINING = "declining"  # Negative trend
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough data points


class MetricType(Enum):
    """Type of performance metric."""

    VO2MAX = "vo2max"
    RESTING_HR = "resting_hr"
    TRAINING_LOAD = "training_load"
    RACE_PERFORMANCE = "race_performance"
    POWER_OUTPUT = "power_output"
    PACE = "pace"
    HRV = "hrv"
    BODY_COMPOSITION = "body_composition"


@dataclass
class DataPoint:
    """Single data point in time series."""

    date: date
    value: float
    context: str | None = None  # Optional context (e.g., "Post-race", "Altitude camp")


@dataclass
class TrendAnalysis:
    """Analysis of a single metric trend."""

    metric_name: str
    metric_type: MetricType
    direction: TrendDirection

    # Data points
    data_points: list[DataPoint]
    start_date: date
    end_date: date

    # Statistical measures
    baseline_value: float | None  # First period average
    current_value: float | None  # Recent period average
    change_absolute: float | None  # Absolute change
    change_percentage: float | None  # Percentage change

    # Trend characteristics
    trend_line_slope: float | None  # Linear regression slope
    r_squared: float | None  # Fit quality
    volatility: float | None  # Standard deviation / mean

    # Peaks and nadirs
    peak_value: float | None
    peak_date: date | None
    nadir_value: float | None
    nadir_date: date | None

    # Interpretation
    interpretation: str
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type.value,
            "direction": self.direction.value,
            "period": {
                "start": self.start_date.isoformat(),
                "end": self.end_date.isoformat(),
                "days": (self.end_date - self.start_date).days,
            },
            "values": {
                "baseline": self.baseline_value,
                "current": self.current_value,
                "change_abs": self.change_absolute,
                "change_pct": self.change_percentage,
            },
            "statistics": {
                "slope": self.trend_line_slope,
                "r_squared": self.r_squared,
                "volatility": self.volatility,
            },
            "extremes": {
                "peak": {"value": self.peak_value, "date": self.peak_date.isoformat() if self.peak_date else None},
                "nadir": {"value": self.nadir_value, "date": self.nadir_date.isoformat() if self.nadir_date else None},
            },
            "interpretation": self.interpretation,
            "recommendations": self.recommendations,
        }


@dataclass
class SeasonalPattern:
    """Identified seasonal pattern in performance."""

    pattern_name: str
    months_affected: list[int]  # Month numbers (1-12)
    typical_change: str  # Description of typical change
    average_effect_percentage: float | None
    confidence: float  # 0.0-1.0


@dataclass
class YearOverYearComparison:
    """Year-over-year comparison of performance."""

    metric_name: str
    year_1: int
    year_2: int

    # Values
    year_1_average: float
    year_2_average: float
    change_percentage: float

    # Context
    year_1_training_volume: float | None  # Hours/week average
    year_2_training_volume: float | None

    # Analysis
    interpretation: str
    contributing_factors: list[str] = field(default_factory=list)


@dataclass
class PerformanceTrajectory:
    """Long-term performance trajectory assessment."""

    athlete_name: str
    analysis_period_years: int

    # Overall assessment
    overall_direction: TrendDirection
    fitness_age_years: float | None  # Estimated fitness age vs chronological

    # Individual metrics
    metric_trends: list[TrendAnalysis]

    # Patterns
    seasonal_patterns: list[SeasonalPattern]
    year_over_year: list[YearOverYearComparison]

    # Key milestones
    breakthrough_performances: list[dict[str, Any]]  # Notable improvements
    setbacks: list[dict[str, Any]]  # Injuries, performance drops

    # Predictions
    projected_peak_date: date | None  # When athlete likely to peak
    projected_plateau_date: date | None  # When plateau expected

    # Recommendations
    strategic_recommendations: list[str] = field(default_factory=list)

    # Metadata
    analysis_date: date = field(default_factory=date.today)
    confidence: float = 0.0  # Overall confidence in analysis

    def to_markdown(self) -> str:
        """Format as markdown report."""
        lines = []

        lines.append("# Historical Performance Trends Analysis")
        lines.append("")
        lines.append(f"**Athlete:** {self.athlete_name}")
        lines.append(f"**Analysis Period:** {self.analysis_period_years} years")
        lines.append(f"**Analysis Date:** {self.analysis_date.isoformat()}")
        lines.append(f"**Overall Trend:** {self.overall_direction.value.upper()}")
        if self.fitness_age_years:
            lines.append(f"**Fitness Age:** {self.fitness_age_years:.1f} years")
        lines.append("")

        # Executive summary
        lines.append("## Executive Summary")
        lines.append("")

        improving = [t for t in self.metric_trends if t.direction == TrendDirection.IMPROVING]
        declining = [t for t in self.metric_trends if t.direction == TrendDirection.DECLINING]
        stable = [t for t in self.metric_trends if t.direction == TrendDirection.STABLE]

        lines.append(f"**Metrics Analyzed:** {len(self.metric_trends)}")
        lines.append(f"- ✅ Improving: {len(improving)}")
        lines.append(f"- ➡️  Stable: {len(stable)}")
        lines.append(f"- ⚠️  Declining: {len(declining)}")
        lines.append("")

        # Metric trends
        lines.append("## Metric Trends")
        lines.append("")

        for trend in self.metric_trends:
            emoji = {
                TrendDirection.IMPROVING: "📈",
                TrendDirection.STABLE: "➡️",
                TrendDirection.DECLINING: "📉",
                TrendDirection.INSUFFICIENT_DATA: "❓",
            }[trend.direction]

            lines.append(f"### {emoji} {trend.metric_name}")
            lines.append("")
            lines.append(f"**Period:** {trend.start_date.isoformat()} to {trend.end_date.isoformat()}")
            lines.append(f"**Trend:** {trend.direction.value.title()}")

            if trend.baseline_value and trend.current_value:
                lines.append(f"**Baseline:** {trend.baseline_value:.1f}")
                lines.append(f"**Current:** {trend.current_value:.1f}")

                if trend.change_percentage:
                    sign = "+" if trend.change_percentage > 0 else ""
                    lines.append(f"**Change:** {sign}{trend.change_percentage:.1f}%")

            if trend.peak_value:
                lines.append(f"**Peak:** {trend.peak_value:.1f} on {trend.peak_date.isoformat() if trend.peak_date else 'unknown'}")

            lines.append("")
            lines.append(f"*{trend.interpretation}*")
            lines.append("")

            if trend.recommendations:
                lines.append("**Recommendations:**")
                for rec in trend.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

        # Seasonal patterns
        if self.seasonal_patterns:
            lines.append("## Seasonal Patterns")
            lines.append("")

            for pattern in self.seasonal_patterns:
                months = [
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
                ]
                affected_months = ", ".join(months[m - 1] for m in pattern.months_affected)

                lines.append(f"**{pattern.pattern_name}**")
                lines.append(f"- Months: {affected_months}")
                lines.append(f"- Effect: {pattern.typical_change}")
                if pattern.average_effect_percentage:
                    lines.append(f"- Average Impact: {pattern.average_effect_percentage:+.1f}%")
                lines.append(f"- Confidence: {pattern.confidence:.0%}")
                lines.append("")

        # Year over year
        if self.year_over_year:
            lines.append("## Year-over-Year Comparison")
            lines.append("")

            for yoy in self.year_over_year:
                sign = "+" if yoy.change_percentage > 0 else ""
                lines.append(f"**{yoy.metric_name}** ({yoy.year_1} → {yoy.year_2})")
                lines.append(f"- {yoy.year_1}: {yoy.year_1_average:.1f}")
                lines.append(f"- {yoy.year_2}: {yoy.year_2_average:.1f}")
                lines.append(f"- Change: {sign}{yoy.change_percentage:.1f}%")
                lines.append(f"- *{yoy.interpretation}*")

                if yoy.contributing_factors:
                    lines.append("- Contributing factors:")
                    for factor in yoy.contributing_factors:
                        lines.append(f"  - {factor}")
                lines.append("")

        # Breakthrough performances
        if self.breakthrough_performances:
            lines.append("## Breakthrough Performances")
            lines.append("")

            for breakthrough in self.breakthrough_performances:
                lines.append(f"**{breakthrough['date']}** - {breakthrough['description']}")
                lines.append(f"- Achievement: {breakthrough['achievement']}")
                if "context" in breakthrough:
                    lines.append(f"- Context: {breakthrough['context']}")
                lines.append("")

        # Strategic recommendations
        if self.strategic_recommendations:
            lines.append("## Strategic Recommendations")
            lines.append("")

            for i, rec in enumerate(self.strategic_recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # Predictions
        if self.projected_peak_date or self.projected_plateau_date:
            lines.append("## Projections")
            lines.append("")

            if self.projected_peak_date:
                lines.append(f"**Projected Peak Performance:** {self.projected_peak_date.isoformat()}")
                lines.append("*Based on current trajectory and typical training cycles*")
                lines.append("")

            if self.projected_plateau_date:
                lines.append(f"**Plateau Risk:** {self.projected_plateau_date.isoformat()}")
                lines.append("*Consider periodization adjustments or new stimulus*")
                lines.append("")

        lines.append("---")
        lines.append(f"*Analysis confidence: {self.confidence:.0%}*")

        return "\n".join(lines)
