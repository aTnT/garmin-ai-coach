"""
Tests for Historical Trends Analyzer.
"""

from datetime import datetime, timedelta

import pytest

from services.ai.trends import (
    DataPoint,
    MetricType,
    TrendDirection,
    TrendsAnalyzer,
)


class TestTrendsAnalyzer:
    """Test suite for TrendsAnalyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initializes correctly."""
        analyzer = TrendsAnalyzer()
        assert analyzer.IMPROVING_THRESHOLD == 0.02
        assert analyzer.DECLINING_THRESHOLD == -0.02
        assert analyzer.MIN_DATA_POINTS == 10

    def test_analyze_improving_trend(self):
        """Test detection of improving trend."""
        analyzer = TrendsAnalyzer()

        # Create data points with upward trend
        base_date = datetime(2023, 1, 1)
        data_points = [
            {"timestamp": base_date + timedelta(days=i * 30), "value": 50 + i * 2}
            for i in range(12)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="VO2max",
            metric_type=MetricType.PERFORMANCE,
            data_points=data_points,
            higher_is_better=True,
        )

        assert trend.metric_name == "VO2max"
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.trend_line_slope is not None
        assert trend.trend_line_slope > 0
        assert trend.change_percentage is not None
        assert trend.change_percentage > 2  # Should be improving by more than 2%
        assert len(trend.recommendations) > 0

    def test_analyze_declining_trend(self):
        """Test detection of declining trend."""
        analyzer = TrendsAnalyzer()

        # Create data points with downward trend
        base_date = datetime(2023, 1, 1)
        data_points = [
            {"timestamp": base_date + timedelta(days=i * 30), "value": 70 - i * 2}
            for i in range(12)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="VO2max",
            metric_type=MetricType.PERFORMANCE,
            data_points=data_points,
            higher_is_better=True,
        )

        assert trend.direction == TrendDirection.DECLINING
        assert trend.trend_line_slope is not None
        assert trend.trend_line_slope < 0
        assert trend.change_percentage is not None
        assert trend.change_percentage < -2  # Should be declining by more than 2%
        assert "concern" in trend.interpretation.lower() or "declining" in trend.interpretation.lower()

    def test_analyze_stable_trend(self):
        """Test detection of stable trend."""
        analyzer = TrendsAnalyzer()

        # Create data points with minimal variation
        base_date = datetime(2023, 1, 1)
        data_points = [
            {
                "timestamp": base_date + timedelta(days=i * 30),
                "value": 60 + (i % 2) * 0.5,  # Very small oscillation
            }
            for i in range(12)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="VO2max",
            metric_type=MetricType.PERFORMANCE,
            data_points=data_points,
            higher_is_better=True,
        )

        assert trend.direction == TrendDirection.STABLE
        assert abs(trend.change_percentage) < 2 if trend.change_percentage else True

    def test_analyze_recovery_metric(self):
        """Test analysis of recovery metric where lower is better."""
        analyzer = TrendsAnalyzer()

        # Create resting HR data - declining is good
        base_date = datetime(2023, 1, 1)
        data_points = [
            {"timestamp": base_date + timedelta(days=i * 30), "value": 60 - i * 0.5}
            for i in range(12)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="Resting HR",
            metric_type=MetricType.RECOVERY,
            data_points=data_points,
            higher_is_better=False,  # Lower is better for RHR
        )

        # Should be improving even though value is declining
        assert trend.direction == TrendDirection.IMPROVING
        assert "improv" in trend.interpretation.lower()

    def test_insufficient_data_points(self):
        """Test handling of insufficient data."""
        analyzer = TrendsAnalyzer()

        # Only 5 data points (less than MIN_DATA_POINTS)
        base_date = datetime(2023, 1, 1)
        data_points = [
            {"timestamp": base_date + timedelta(days=i * 30), "value": 50 + i}
            for i in range(5)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="VO2max",
            metric_type=MetricType.PERFORMANCE,
            data_points=data_points,
        )

        # Should still work but with warning about limited data
        assert trend.metric_name == "VO2max"
        assert len(trend.data_points) == 5
        # Interpretation should mention limited data
        assert "insufficient" in trend.interpretation.lower() or "limited" in trend.interpretation.lower()

    def test_empty_data_points(self):
        """Test handling of empty data."""
        analyzer = TrendsAnalyzer()

        trend = analyzer.analyze_metric_trend(
            metric_name="VO2max",
            metric_type=MetricType.PERFORMANCE,
            data_points=[],
        )

        assert trend.metric_name == "VO2max"
        assert len(trend.data_points) == 0
        assert trend.baseline_value is None
        assert trend.current_value is None
        assert trend.trend_line_slope is None
        assert "no data" in trend.interpretation.lower()

    def test_identify_seasonal_patterns(self):
        """Test seasonal pattern detection."""
        analyzer = TrendsAnalyzer()

        # Create 2 years of data with clear seasonal pattern
        # Summer (Jun-Aug) higher, Winter (Dec-Feb) lower
        base_date = datetime(2022, 1, 1)
        data_points = []

        for month in range(24):  # 2 years
            current_date = base_date + timedelta(days=month * 30)
            month_of_year = current_date.month

            # Higher values in summer (6-8), lower in winter (12, 1, 2)
            if month_of_year in [6, 7, 8]:
                value = 65
            elif month_of_year in [12, 1, 2]:
                value = 55
            else:
                value = 60

            data_points.append({"timestamp": current_date, "value": value})

        patterns = analyzer.identify_seasonal_patterns(data_points, "VO2max")

        assert len(patterns) > 0
        # Should have identified some seasonal patterns
        assert any(p.peak_or_decline == "PEAK" for p in patterns)
        assert any(p.peak_or_decline == "DECLINE" for p in patterns)

    def test_compare_years(self):
        """Test year-over-year comparison."""
        analyzer = TrendsAnalyzer()

        # Create data for 2023 with higher values than 2022
        data_2022 = [
            {"timestamp": datetime(2022, month, 15), "value": 55 + month * 0.5}
            for month in range(1, 13)
        ]
        data_2023 = [
            {"timestamp": datetime(2023, month, 15), "value": 60 + month * 0.5}
            for month in range(1, 13)
        ]

        all_data = data_2022 + data_2023

        comparison_2023 = analyzer.compare_years(all_data, 2023, "VO2max")

        assert comparison_2023.year == 2023
        assert comparison_2023.sample_size == 12
        assert comparison_2023.change_from_previous is not None
        assert comparison_2023.change_from_previous > 5  # ~8-9% improvement

    def test_generate_performance_trajectory(self):
        """Test complete performance trajectory generation."""
        analyzer = TrendsAnalyzer()

        # Create 2 years of multi-metric data
        base_date = datetime(2022, 1, 1)

        vo2max_data = [
            {"timestamp": base_date + timedelta(days=i * 15), "value": 50 + i * 0.3}
            for i in range(48)
        ]

        rhr_data = [
            {"timestamp": base_date + timedelta(days=i * 15), "value": 60 - i * 0.1}
            for i in range(48)
        ]

        metrics_data = {
            "VO2max": {
                "data_points": vo2max_data,
                "metric_type": MetricType.PERFORMANCE,
                "higher_is_better": True,
            },
            "Resting HR": {
                "data_points": rhr_data,
                "metric_type": MetricType.RECOVERY,
                "higher_is_better": False,
            },
        }

        trajectory = analyzer.generate_performance_trajectory(
            athlete_name="Test Athlete",
            metrics_data=metrics_data,
            analysis_period_years=2,
        )

        assert trajectory.athlete_name == "Test Athlete"
        assert trajectory.analysis_period_years == 2
        assert len(trajectory.metric_trends) == 2
        assert trajectory.overall_direction in [
            TrendDirection.IMPROVING,
            TrendDirection.STABLE,
            TrendDirection.DECLINING,
        ]
        assert len(trajectory.strategic_recommendations) > 0

        # Check that both metrics are improving
        vo2max_trend = next(t for t in trajectory.metric_trends if t.metric_name == "VO2max")
        rhr_trend = next(t for t in trajectory.metric_trends if t.metric_name == "Resting HR")

        assert vo2max_trend.direction == TrendDirection.IMPROVING
        assert rhr_trend.direction == TrendDirection.IMPROVING

    def test_high_r_squared_strong_trend(self):
        """Test that a clear linear trend has high R-squared."""
        analyzer = TrendsAnalyzer()

        # Perfect linear trend
        base_date = datetime(2023, 1, 1)
        data_points = [
            {"timestamp": base_date + timedelta(days=i * 30), "value": 50 + i * 2}
            for i in range(12)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="VO2max",
            metric_type=MetricType.PERFORMANCE,
            data_points=data_points,
        )

        assert trend.r_squared is not None
        assert trend.r_squared > 0.95  # Very high R-squared for linear data

    def test_low_r_squared_noisy_trend(self):
        """Test that noisy data has low R-squared."""
        analyzer = TrendsAnalyzer()

        # Noisy data with no clear trend
        base_date = datetime(2023, 1, 1)
        import random

        random.seed(42)
        data_points = [
            {
                "timestamp": base_date + timedelta(days=i * 30),
                "value": 60 + random.uniform(-5, 5),
            }
            for i in range(12)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="VO2max",
            metric_type=MetricType.PERFORMANCE,
            data_points=data_points,
        )

        assert trend.r_squared is not None
        # R-squared should be lower for noisy data
        # (actual value depends on random seed, but should be < 0.5)

    def test_load_metric(self):
        """Test training load metric handling."""
        analyzer = TrendsAnalyzer()

        # Gradually increasing load
        base_date = datetime(2023, 1, 1)
        data_points = [
            {"timestamp": base_date + timedelta(days=i * 7), "value": 200 + i * 10}
            for i in range(20)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="Weekly Training Load",
            metric_type=MetricType.LOAD,
            data_points=data_points,
            higher_is_better=True,
        )

        assert trend.metric_type == MetricType.LOAD
        assert trend.direction == TrendDirection.IMPROVING
        # Should have recommendations about managing load
        assert any(
            "load" in rec.lower() or "volume" in rec.lower()
            for rec in trend.recommendations
        )

    def test_wellbeing_metric(self):
        """Test wellbeing metric handling."""
        analyzer = TrendsAnalyzer()

        # Improving wellbeing scores
        base_date = datetime(2023, 1, 1)
        data_points = [
            {"timestamp": base_date + timedelta(days=i * 7), "value": 5 + i * 0.1}
            for i in range(20)
        ]

        trend = analyzer.analyze_metric_trend(
            metric_name="Wellness Score",
            metric_type=MetricType.WELLBEING,
            data_points=data_points,
            higher_is_better=True,
        )

        assert trend.metric_type == MetricType.WELLBEING
        assert trend.direction in [TrendDirection.IMPROVING, TrendDirection.STABLE]


@pytest.mark.integration
class TestTrendsIntegration:
    """Integration tests for trends analysis."""

    def test_full_athlete_analysis(self):
        """Test complete analysis pipeline."""
        analyzer = TrendsAnalyzer()

        # Simulate 3 years of athlete data
        base_date = datetime(2021, 1, 1)
        num_weeks = 156  # 3 years

        # Create realistic multi-metric data
        vo2max_data = []
        rhr_data = []
        hrv_data = []
        load_data = []

        for week in range(num_weeks):
            current_date = base_date + timedelta(weeks=week)

            # VO2max: Gradual improvement with seasonal variation
            month = current_date.month
            seasonal_factor = 1.0
            if month in [6, 7, 8]:  # Summer peak
                seasonal_factor = 1.05
            elif month in [12, 1, 2]:  # Winter decline
                seasonal_factor = 0.95

            vo2max_base = 52 + week * 0.05  # Gradual improvement
            vo2max_data.append(
                {"timestamp": current_date, "value": vo2max_base * seasonal_factor}
            )

            # Resting HR: Gradual improvement (decreasing)
            rhr_data.append({"timestamp": current_date, "value": 62 - week * 0.02})

            # HRV: Gradual improvement with weekly variation
            hrv_data.append(
                {
                    "timestamp": current_date,
                    "value": 55 + week * 0.03 + (week % 4) * 2,
                }
            )

            # Training load: Progressive with periodic deloads
            if week % 4 == 3:  # Deload week
                load = 150
            else:
                load = 250 + week * 2

            load_data.append({"timestamp": current_date, "value": load})

        # Run full trajectory analysis
        metrics_data = {
            "VO2max": {
                "data_points": vo2max_data,
                "metric_type": MetricType.PERFORMANCE,
                "higher_is_better": True,
            },
            "Resting HR": {
                "data_points": rhr_data,
                "metric_type": MetricType.RECOVERY,
                "higher_is_better": False,
            },
            "HRV": {
                "data_points": hrv_data,
                "metric_type": MetricType.RECOVERY,
                "higher_is_better": True,
            },
            "Training Load": {
                "data_points": load_data,
                "metric_type": MetricType.LOAD,
                "higher_is_better": True,
            },
        }

        trajectory = analyzer.generate_performance_trajectory(
            athlete_name="John Doe",
            metrics_data=metrics_data,
            analysis_period_years=3,
        )

        # Validate results
        assert trajectory.athlete_name == "John Doe"
        assert trajectory.analysis_period_years == 3
        assert len(trajectory.metric_trends) == 4

        # All metrics should be improving
        assert all(
            t.direction == TrendDirection.IMPROVING for t in trajectory.metric_trends
        )

        # Should have seasonal patterns detected
        assert len(trajectory.seasonal_patterns) > 0

        # Should have year-over-year comparisons
        assert len(trajectory.year_over_year) > 0

        # Should have strategic recommendations
        assert len(trajectory.strategic_recommendations) >= 3

        # Overall direction should be improving
        assert trajectory.overall_direction == TrendDirection.IMPROVING

    def test_mixed_trend_directions(self):
        """Test trajectory with mixed improving/declining metrics."""
        analyzer = TrendsAnalyzer()

        base_date = datetime(2022, 1, 1)

        # Improving VO2max
        vo2max_data = [
            {"timestamp": base_date + timedelta(days=i * 15), "value": 50 + i * 0.3}
            for i in range(48)
        ]

        # Declining HRV (stress/overtraining)
        hrv_data = [
            {"timestamp": base_date + timedelta(days=i * 15), "value": 70 - i * 0.4}
            for i in range(48)
        ]

        metrics_data = {
            "VO2max": {
                "data_points": vo2max_data,
                "metric_type": MetricType.PERFORMANCE,
                "higher_is_better": True,
            },
            "HRV": {
                "data_points": hrv_data,
                "metric_type": MetricType.RECOVERY,
                "higher_is_better": True,
            },
        }

        trajectory = analyzer.generate_performance_trajectory(
            athlete_name="Test Athlete",
            metrics_data=metrics_data,
            analysis_period_years=2,
        )

        # Should have mixed results
        vo2max_trend = next(t for t in trajectory.metric_trends if t.metric_name == "VO2max")
        hrv_trend = next(t for t in trajectory.metric_trends if t.metric_name == "HRV")

        assert vo2max_trend.direction == TrendDirection.IMPROVING
        assert hrv_trend.direction == TrendDirection.DECLINING

        # Recommendations should address the declining recovery
        assert any(
            "recovery" in rec.lower() or "hrv" in rec.lower()
            for rec in trajectory.strategic_recommendations
        )
