"""
Historical Trends Analyzer

Analyzes long-term performance trends from Garmin data.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import numpy as np

from .trends_models import (
    DataPoint,
    MetricType,
    PerformanceTrajectory,
    SeasonalPattern,
    TrendAnalysis,
    TrendDirection,
    YearOverYearComparison,
)

logger = logging.getLogger(__name__)


class TrendsAnalyzer:
    """
    Analyze historical performance trends.

    Tracks long-term progression in fitness metrics, identifies patterns,
    and provides strategic recommendations.
    """

    # Thresholds for trend classification
    IMPROVING_THRESHOLD = 0.02  # 2% improvement = improving trend
    DECLINING_THRESHOLD = -0.02  # 2% decline = declining trend
    MIN_DATA_POINTS = 10  # Minimum points needed for analysis

    def __init__(self):
        """Initialize trends analyzer."""
        self.trends_cache = {}

    def analyze_metric_trend(
        self,
        metric_name: str,
        metric_type: MetricType,
        data_points: list[dict[str, Any]],
        higher_is_better: bool = True,
    ) -> TrendAnalysis:
        """
        Analyze trend for a single metric.

        Args:
            metric_name: Display name of metric
            metric_type: Type of metric
            data_points: List of dicts with 'date' and 'value' keys
            higher_is_better: Whether higher values indicate improvement

        Returns:
            TrendAnalysis with detailed trend information
        """
        if len(data_points) < self.MIN_DATA_POINTS:
            return self._insufficient_data_analysis(metric_name, metric_type, data_points)

        # Sort by date
        sorted_points = sorted(data_points, key=lambda x: x["date"])

        # Convert to DataPoint objects
        data_points_obj = [
            DataPoint(
                date=dp["date"] if isinstance(dp["date"], date) else date.fromisoformat(dp["date"]),
                value=float(dp["value"]),
                context=dp.get("context"),
            )
            for dp in sorted_points
        ]

        start_date = data_points_obj[0].date
        end_date = data_points_obj[-1].date

        # Calculate statistics
        values = np.array([dp.value for dp in data_points_obj])
        dates_numeric = np.array([(dp.date - start_date).days for dp in data_points_obj])

        # Baseline (first 30% of data)
        baseline_count = max(3, int(len(values) * 0.3))
        baseline_value = float(np.mean(values[:baseline_count]))

        # Current (last 30% of data)
        current_count = max(3, int(len(values) * 0.3))
        current_value = float(np.mean(values[-current_count:]))

        # Change calculations
        change_absolute = current_value - baseline_value
        change_percentage = (change_absolute / baseline_value * 100) if baseline_value != 0 else 0

        # Linear regression for trend
        if len(dates_numeric) > 1:
            coeffs = np.polyfit(dates_numeric, values, 1)
            trend_line_slope = float(coeffs[0])

            # R-squared
            y_pred = np.poly1d(coeffs)(dates_numeric)
            ss_res = np.sum((values - y_pred) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = float(1 - (ss_res / ss_tot)) if ss_tot != 0 else 0
        else:
            trend_line_slope = 0
            r_squared = 0

        # Volatility (coefficient of variation)
        volatility = float(np.std(values) / np.mean(values)) if np.mean(values) != 0 else 0

        # Peak and nadir
        peak_idx = int(np.argmax(values))
        nadir_idx = int(np.argmin(values))

        peak_value = float(values[peak_idx])
        peak_date = data_points_obj[peak_idx].date
        nadir_value = float(values[nadir_idx])
        nadir_date = data_points_obj[nadir_idx].date

        # Determine trend direction
        if higher_is_better:
            normalized_change = change_percentage / 100
        else:
            normalized_change = -change_percentage / 100

        if normalized_change >= self.IMPROVING_THRESHOLD:
            direction = TrendDirection.IMPROVING
        elif normalized_change <= self.DECLINING_THRESHOLD:
            direction = TrendDirection.DECLINING
        else:
            direction = TrendDirection.STABLE

        # Generate interpretation
        interpretation = self._generate_interpretation(
            metric_name,
            direction,
            change_percentage,
            baseline_value,
            current_value,
            higher_is_better,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            metric_name, metric_type, direction, volatility, r_squared
        )

        return TrendAnalysis(
            metric_name=metric_name,
            metric_type=metric_type,
            direction=direction,
            data_points=data_points_obj,
            start_date=start_date,
            end_date=end_date,
            baseline_value=baseline_value,
            current_value=current_value,
            change_absolute=change_absolute,
            change_percentage=change_percentage,
            trend_line_slope=trend_line_slope,
            r_squared=r_squared,
            volatility=volatility,
            peak_value=peak_value,
            peak_date=peak_date,
            nadir_value=nadir_value,
            nadir_date=nadir_date,
            interpretation=interpretation,
            recommendations=recommendations,
        )

    def identify_seasonal_patterns(
        self, data_points: list[dict[str, Any]], metric_name: str
    ) -> list[SeasonalPattern]:
        """
        Identify seasonal patterns in performance data.

        Args:
            data_points: List of dicts with 'date' and 'value'
            metric_name: Name of metric

        Returns:
            List of identified seasonal patterns
        """
        if len(data_points) < 365:  # Need at least 1 year of data
            return []

        # Group by month
        monthly_averages = defaultdict(list)

        for dp in data_points:
            dp_date = dp["date"] if isinstance(dp["date"], date) else date.fromisoformat(dp["date"])
            month = dp_date.month
            monthly_averages[month].append(float(dp["value"]))

        # Calculate average for each month
        month_stats = {}
        for month in range(1, 13):
            if month in monthly_averages and len(monthly_averages[month]) >= 3:
                month_stats[month] = {
                    "mean": np.mean(monthly_averages[month]),
                    "std": np.std(monthly_averages[month]),
                    "count": len(monthly_averages[month]),
                }

        if len(month_stats) < 6:  # Need data from at least 6 months
            return []

        overall_mean = np.mean([stats["mean"] for stats in month_stats.values()])

        patterns = []

        # Identify winter decline pattern (Dec, Jan, Feb)
        winter_months = [12, 1, 2]
        winter_data = [month_stats[m]["mean"] for m in winter_months if m in month_stats]
        if len(winter_data) >= 2:
            winter_avg = np.mean(winter_data)
            winter_effect = (winter_avg - overall_mean) / overall_mean * 100

            if abs(winter_effect) > 3:  # > 3% change
                patterns.append(
                    SeasonalPattern(
                        pattern_name="Winter Season Effect",
                        months_affected=winter_months,
                        typical_change="Decreased performance during winter months",
                        average_effect_percentage=float(winter_effect),
                        confidence=0.7,
                    )
                )

        # Identify summer peak pattern (Jun, Jul, Aug)
        summer_months = [6, 7, 8]
        summer_data = [month_stats[m]["mean"] for m in summer_months if m in month_stats]
        if len(summer_data) >= 2:
            summer_avg = np.mean(summer_data)
            summer_effect = (summer_avg - overall_mean) / overall_mean * 100

            if summer_effect > 3:  # > 3% improvement
                patterns.append(
                    SeasonalPattern(
                        pattern_name="Summer Peak Performance",
                        months_affected=summer_months,
                        typical_change="Peak performance during summer months",
                        average_effect_percentage=float(summer_effect),
                        confidence=0.8,
                    )
                )

        return patterns

    def compare_years(
        self,
        metric_name: str,
        year_1_data: list[dict[str, Any]],
        year_2_data: list[dict[str, Any]],
    ) -> YearOverYearComparison | None:
        """
        Compare performance between two years.

        Args:
            metric_name: Name of metric
            year_1_data: Data from first year
            year_2_data: Data from second year

        Returns:
            YearOverYearComparison or None if insufficient data
        """
        if len(year_1_data) < 10 or len(year_2_data) < 10:
            return None

        # Extract years
        year_1 = year_1_data[0]["date"].year if isinstance(year_1_data[0]["date"], date) else int(year_1_data[0]["date"][:4])
        year_2 = year_2_data[0]["date"].year if isinstance(year_2_data[0]["date"], date) else int(year_2_data[0]["date"][:4])

        # Calculate averages
        year_1_values = [float(dp["value"]) for dp in year_1_data]
        year_2_values = [float(dp["value"]) for dp in year_2_data]

        year_1_avg = float(np.mean(year_1_values))
        year_2_avg = float(np.mean(year_2_values))

        change_pct = (year_2_avg - year_1_avg) / year_1_avg * 100

        # Generate interpretation
        if abs(change_pct) < 2:
            interpretation = f"Performance remained stable between {year_1} and {year_2}"
        elif change_pct > 0:
            interpretation = f"Performance improved by {change_pct:.1f}% from {year_1} to {year_2}"
        else:
            interpretation = f"Performance decreased by {abs(change_pct):.1f}% from {year_1} to {year_2}"

        # Identify contributing factors
        contributing_factors = []
        if change_pct > 5:
            contributing_factors.append("Significant training adaptation")
        elif change_pct < -5:
            contributing_factors.append("Possible overtraining or reduced training")

        return YearOverYearComparison(
            metric_name=metric_name,
            year_1=year_1,
            year_2=year_2,
            year_1_average=year_1_avg,
            year_2_average=year_2_avg,
            change_percentage=float(change_pct),
            year_1_training_volume=None,  # Could be calculated if available
            year_2_training_volume=None,
            interpretation=interpretation,
            contributing_factors=contributing_factors,
        )

    def generate_performance_trajectory(
        self,
        athlete_name: str,
        garmin_data_history: list[dict[str, Any]],
        analysis_years: int = 3,
    ) -> PerformanceTrajectory:
        """
        Generate comprehensive performance trajectory analysis.

        Args:
            athlete_name: Athlete's name
            garmin_data_history: Historical Garmin data snapshots
            analysis_years: Number of years to analyze

        Returns:
            PerformanceTrajectory with complete analysis
        """
        logger.info(f"Generating {analysis_years}-year performance trajectory for {athlete_name}")

        # Extract VO2max trend
        vo2max_data = []
        for snapshot in garmin_data_history:
            if "date" in snapshot and "vo2max" in snapshot:
                vo2max_data.append({"date": snapshot["date"], "value": snapshot["vo2max"]})

        vo2max_trend = None
        if len(vo2max_data) >= self.MIN_DATA_POINTS:
            vo2max_trend = self.analyze_metric_trend(
                "VO2max", MetricType.VO2MAX, vo2max_data, higher_is_better=True
            )

        # Extract resting HR trend
        rhr_data = []
        for snapshot in garmin_data_history:
            if "date" in snapshot and "resting_hr" in snapshot:
                rhr_data.append({"date": snapshot["date"], "value": snapshot["resting_hr"]})

        rhr_trend = None
        if len(rhr_data) >= self.MIN_DATA_POINTS:
            rhr_trend = self.analyze_metric_trend(
                "Resting Heart Rate", MetricType.RESTING_HR, rhr_data, higher_is_better=False
            )

        # Compile all trends
        metric_trends = []
        if vo2max_trend:
            metric_trends.append(vo2max_trend)
        if rhr_trend:
            metric_trends.append(rhr_trend)

        # Determine overall direction
        if len(metric_trends) > 0:
            improving_count = sum(1 for t in metric_trends if t.direction == TrendDirection.IMPROVING)
            declining_count = sum(1 for t in metric_trends if t.direction == TrendDirection.DECLINING)

            if improving_count > declining_count:
                overall_direction = TrendDirection.IMPROVING
            elif declining_count > improving_count:
                overall_direction = TrendDirection.DECLINING
            else:
                overall_direction = TrendDirection.STABLE
        else:
            overall_direction = TrendDirection.INSUFFICIENT_DATA

        # Identify seasonal patterns
        seasonal_patterns = []
        if vo2max_data:
            seasonal_patterns.extend(self.identify_seasonal_patterns(vo2max_data, "VO2max"))

        # Year-over-year comparisons
        year_over_year = []
        if vo2max_data and len(vo2max_data) >= 365 * 2:
            # Split into years
            cutoff_date = date.today() - timedelta(days=365)
            year_2_data = [dp for dp in vo2max_data if dp["date"] >= cutoff_date]
            year_1_data = [dp for dp in vo2max_data if dp["date"] < cutoff_date]

            if year_1_data and year_2_data:
                yoy = self.compare_years("VO2max", year_1_data, year_2_data)
                if yoy:
                    year_over_year.append(yoy)

        # Strategic recommendations
        strategic_recommendations = self._generate_strategic_recommendations(
            metric_trends, overall_direction
        )

        # Calculate confidence
        confidence = self._calculate_confidence(metric_trends, len(garmin_data_history))

        return PerformanceTrajectory(
            athlete_name=athlete_name,
            analysis_period_years=analysis_years,
            overall_direction=overall_direction,
            fitness_age_years=None,  # Could be calculated with more data
            metric_trends=metric_trends,
            seasonal_patterns=seasonal_patterns,
            year_over_year=year_over_year,
            breakthrough_performances=[],  # Would need race data
            setbacks=[],  # Would need injury/illness data
            projected_peak_date=None,  # Would need periodization context
            projected_plateau_date=None,
            strategic_recommendations=strategic_recommendations,
            confidence=confidence,
        )

    def _insufficient_data_analysis(
        self, metric_name: str, metric_type: MetricType, data_points: list[dict]
    ) -> TrendAnalysis:
        """Create TrendAnalysis for insufficient data."""
        if len(data_points) > 0:
            sorted_points = sorted(data_points, key=lambda x: x["date"])
            data_points_obj = [
                DataPoint(
                    date=dp["date"] if isinstance(dp["date"], date) else date.fromisoformat(dp["date"]),
                    value=float(dp["value"]),
                )
                for dp in sorted_points
            ]
            start_date = data_points_obj[0].date
            end_date = data_points_obj[-1].date
        else:
            data_points_obj = []
            start_date = date.today()
            end_date = date.today()

        return TrendAnalysis(
            metric_name=metric_name,
            metric_type=metric_type,
            direction=TrendDirection.INSUFFICIENT_DATA,
            data_points=data_points_obj,
            start_date=start_date,
            end_date=end_date,
            baseline_value=None,
            current_value=None,
            change_absolute=None,
            change_percentage=None,
            trend_line_slope=None,
            r_squared=None,
            volatility=None,
            peak_value=None,
            peak_date=None,
            nadir_value=None,
            nadir_date=None,
            interpretation=f"Insufficient data for {metric_name} trend analysis (need at least {self.MIN_DATA_POINTS} data points)",
            recommendations=["Continue collecting data for at least 30-60 days"],
        )

    def _generate_interpretation(
        self,
        metric_name: str,
        direction: TrendDirection,
        change_pct: float,
        baseline: float,
        current: float,
        higher_is_better: bool,
    ) -> str:
        """Generate human-readable interpretation."""
        if direction == TrendDirection.IMPROVING:
            if higher_is_better:
                return f"{metric_name} has improved by {abs(change_pct):.1f}% from {baseline:.1f} to {current:.1f}. Positive adaptation to training."
            else:
                return f"{metric_name} has decreased by {abs(change_pct):.1f}% from {baseline:.1f} to {current:.1f}. Positive adaptation indicating better recovery."

        elif direction == TrendDirection.DECLINING:
            if higher_is_better:
                return f"{metric_name} has declined by {abs(change_pct):.1f}% from {baseline:.1f} to {current:.1f}. Consider reviewing training load and recovery."
            else:
                return f"{metric_name} has increased by {abs(change_pct):.1f}% from {baseline:.1f} to {current:.1f}. May indicate fatigue or overtraining."

        else:  # STABLE
            return f"{metric_name} has remained relatively stable around {current:.1f}. Maintaining current fitness level."

    def _generate_recommendations(
        self, metric_name: str, metric_type: MetricType, direction: TrendDirection, volatility: float, r_squared: float
    ) -> list[str]:
        """Generate recommendations based on trend."""
        recommendations = []

        if direction == TrendDirection.IMPROVING:
            recommendations.append("Continue current training approach")
            if r_squared > 0.7:
                recommendations.append("Consistent improvement - training stimulus is effective")

        elif direction == TrendDirection.DECLINING:
            recommendations.append("Review recent training load and recovery practices")
            recommendations.append("Consider deload week or increased recovery time")

            if metric_type == MetricType.VO2MAX:
                recommendations.append("Add or increase high-intensity interval work")
            elif metric_type == MetricType.RESTING_HR:
                recommendations.append("Elevated RHR may indicate overtraining - prioritize rest")

        elif direction == TrendDirection.STABLE:
            if metric_type == MetricType.VO2MAX:
                recommendations.append("Plateau detected - consider new training stimulus")
                recommendations.append("Try varying interval durations or intensities")
            else:
                recommendations.append("Stable metrics indicate consistent training effect")

        if volatility > 0.15:  # High volatility
            recommendations.append(f"High variability in {metric_name} - aim for more consistent training")

        return recommendations

    def _generate_strategic_recommendations(
        self, trends: list[TrendAnalysis], overall_direction: TrendDirection
    ) -> list[str]:
        """Generate strategic recommendations based on all trends."""
        recommendations = []

        if overall_direction == TrendDirection.IMPROVING:
            recommendations.append("Overall positive trajectory - maintain training consistency")
            recommendations.append("Consider planning peak performance for major competition")

        elif overall_direction == TrendDirection.DECLINING:
            recommendations.append("Multiple declining metrics suggest need for recovery period")
            recommendations.append("Implement 1-2 week deload with 40-50% volume reduction")
            recommendations.append("Focus on sleep, nutrition, and stress management")

        elif overall_direction == TrendDirection.STABLE:
            recommendations.append("Plateau across metrics - time for periodization change")
            recommendations.append("Introduce new training stimulus (different intensities, volumes, or modalities)")

        # Specific metric-based recommendations
        vo2max_trends = [t for t in trends if t.metric_type == MetricType.VO2MAX]
        if vo2max_trends and vo2max_trends[0].direction == TrendDirection.DECLINING:
            recommendations.append("VO2max declining - prioritize high-intensity interval training")

        rhr_trends = [t for t in trends if t.metric_type == MetricType.RESTING_HR]
        if rhr_trends and rhr_trends[0].direction == TrendDirection.DECLINING:
            recommendations.append("Elevated resting HR - reduce training load and increase recovery")

        return recommendations

    def _calculate_confidence(self, trends: list[TrendAnalysis], data_count: int) -> float:
        """Calculate overall confidence in analysis."""
        if len(trends) == 0:
            return 0.0

        # Base confidence on data quantity
        confidence = min(1.0, data_count / 365)  # Full confidence with 1 year of data

        # Adjust for R-squared quality
        avg_r_squared = np.mean([t.r_squared for t in trends if t.r_squared is not None])
        confidence *= (0.5 + 0.5 * avg_r_squared)  # Penalize low R-squared

        return float(confidence)
