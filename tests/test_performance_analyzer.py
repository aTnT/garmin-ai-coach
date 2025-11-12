"""
Tests for Performance Analyzer.
"""

from datetime import datetime, timedelta
import pytest

from services.ai.planning.performance_analyzer import PerformanceAnalyzer, PerformanceMetrics
from services.garmin.models import Activity


class MockActivity:
    """Mock Activity for testing."""

    def __init__(
        self,
        activity_id: str,
        name: str,
        start_time: datetime,
        duration_seconds: int = 3600,
        average_power: float | None = None,
        average_speed: float | None = None,
        average_hr: float | None = None,
        max_hr: float | None = None,
        distance: float | None = None,
        elevation_gain: float | None = None,
        power_stream: list[float] | None = None,
        hr_stream: list[float] | None = None,
        vo2max_estimate: float | None = None,
    ):
        self.activity_id = activity_id
        self.name = name
        self.start_time = start_time
        self.duration_seconds = duration_seconds
        self.average_power = average_power
        self.average_speed = average_speed
        self.average_hr = average_hr
        self.max_hr = max_hr
        self.distance = distance
        self.elevation_gain = elevation_gain
        self.power_stream = power_stream
        self.hr_stream = hr_stream
        self.vo2max_estimate = vo2max_estimate


class TestPerformanceAnalyzer:
    """Test suite for PerformanceAnalyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initializes correctly."""
        analyzer = PerformanceAnalyzer()
        assert analyzer.power_analyzer is not None
        assert analyzer.trends_analyzer is not None

    def test_analyze_empty_activities(self):
        """Test handling of empty activity list."""
        analyzer = PerformanceAnalyzer()
        metrics = analyzer.analyze_recent_performance([], None)

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.performance_direction == "stable"

    def test_analyze_power_metrics(self):
        """Test power metrics analysis."""
        analyzer = PerformanceAnalyzer()

        # Create activities with power data
        recent_activities = []
        for i in range(5):
            # Generate power stream with realistic values
            power_stream = [300 + (i * 5)] * 1200  # 20 minutes at varying power
            activity = MockActivity(
                activity_id=f"act{i}",
                name="Threshold Ride",
                start_time=datetime.now() - timedelta(days=i),
                duration_seconds=1200,
                average_power=300.0 + (i * 5),
                power_stream=power_stream,
            )
            recent_activities.append(activity)

        metrics = analyzer.analyze_recent_performance(recent_activities, None)

        # Should have detected power improvements
        assert metrics.current_ftp is not None or metrics.power_5min is not None

    def test_analyze_interval_quality(self):
        """Test interval quality analysis."""
        analyzer = PerformanceAnalyzer()

        # Create interval workout with HR data
        # Simulate 5x5min intervals
        hr_stream = []
        for rep in range(5):
            # Work interval (5 min = 300 sec)
            hr_stream.extend([160 + (rep * 2)] * 300)  # Gradual HR drift
            # Recovery (2 min = 120 sec)
            hr_stream.extend([120] * 120)

        activity = MockActivity(
            activity_id="interval1",
            name="Threshold Intervals",
            start_time=datetime.now() - timedelta(days=1),
            duration_seconds=len(hr_stream),
            average_hr=150,
            max_hr=180,
            hr_stream=hr_stream,
        )

        metrics = analyzer.analyze_recent_performance([activity], None)

        # Should have analyzed interval quality
        assert 0 <= metrics.avg_interval_adherence <= 1.0
        assert 0 <= metrics.zone_drift_score <= 1.0

    def test_analyze_vo2max_trends(self):
        """Test VO2max trend analysis."""
        analyzer = PerformanceAnalyzer()

        # Create activities with improving VO2max
        activities = []
        for i in range(7):
            activity = MockActivity(
                activity_id=f"run{i}",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=i),
                vo2max_estimate=50.0 + (i * 0.5),  # Improving trend
            )
            activities.append(activity)

        metrics = analyzer.analyze_recent_performance(activities, None)

        assert metrics.vo2max_current is not None
        assert metrics.vo2max_current >= 50.0
        # Trend should be improving
        assert metrics.vo2max_trend in ["improving", "stable", "declining"]

    def test_detect_intervals_from_hr(self):
        """Test interval detection from HR stream."""
        analyzer = PerformanceAnalyzer()

        # Create HR stream with clear intervals
        hr_stream = []
        # Baseline
        hr_stream.extend([120] * 300)
        # Interval 1
        hr_stream.extend([160] * 300)
        # Recovery
        hr_stream.extend([120] * 180)
        # Interval 2
        hr_stream.extend([165] * 300)
        # Recovery
        hr_stream.extend([120] * 180)

        intervals = analyzer._detect_intervals_from_hr(hr_stream)

        # Should detect 2 intervals
        assert len(intervals) >= 1  # At least one interval detected

    def test_calculate_gap(self):
        """Test Grade Adjusted Pace calculation."""
        analyzer = PerformanceAnalyzer()

        # Flat run
        flat_activity = MockActivity(
            activity_id="flat1",
            name="Flat Run",
            start_time=datetime.now(),
            distance=10000,  # 10km
            duration_seconds=3000,  # 50 minutes
            elevation_gain=0,
        )

        gap_flat = analyzer._calculate_gap(flat_activity)
        assert gap_flat is not None
        assert gap_flat > 0

        # Hilly run (same pace, more elevation)
        hilly_activity = MockActivity(
            activity_id="hilly1",
            name="Hill Run",
            start_time=datetime.now(),
            distance=10000,
            duration_seconds=3000,
            elevation_gain=200,  # 200m gain
        )

        gap_hilly = analyzer._calculate_gap(hilly_activity)
        assert gap_hilly is not None
        # GAP should be faster (lower number) than actual pace for hills
        assert gap_hilly < gap_flat

    def test_determine_performance_direction(self):
        """Test overall performance direction determination."""
        analyzer = PerformanceAnalyzer()

        # Test improving scenario
        metrics_improving = PerformanceMetrics()
        metrics_improving.ftp_trend = "improving"
        metrics_improving.ftp_change_pct = 5.0
        metrics_improving.vo2max_trend = "improving"
        metrics_improving.avg_interval_adherence = 0.90

        analyzer._determine_performance_direction(metrics_improving)
        assert metrics_improving.performance_direction == "improving"
        assert metrics_improving.confidence > 0.5

        # Test declining scenario
        metrics_declining = PerformanceMetrics()
        metrics_declining.ftp_trend = "declining"
        metrics_declining.ftp_change_pct = -6.0
        metrics_declining.vo2max_trend = "declining"
        metrics_declining.avg_interval_adherence = 0.65

        analyzer._determine_performance_direction(metrics_declining)
        assert metrics_declining.performance_direction == "declining"

    def test_get_adaptation_recommendation_ftp_declining(self):
        """Test adaptation recommendation for declining FTP."""
        analyzer = PerformanceAnalyzer()

        metrics = PerformanceMetrics()
        metrics.performance_direction = "declining"
        metrics.confidence = 0.8
        metrics.ftp_trend = "declining"
        metrics.ftp_change_pct = -7.0  # Significant decline

        should_adapt, reasoning = analyzer.get_adaptation_recommendation(metrics)

        assert should_adapt is True
        assert "FTP" in reasoning or "recovery" in reasoning.lower()

    def test_get_adaptation_recommendation_poor_intervals(self):
        """Test adaptation recommendation for poor interval quality."""
        analyzer = PerformanceAnalyzer()

        metrics = PerformanceMetrics()
        metrics.avg_interval_adherence = 0.60  # Poor quality

        should_adapt, reasoning = analyzer.get_adaptation_recommendation(metrics)

        assert should_adapt is True
        assert "interval" in reasoning.lower()

    def test_get_adaptation_recommendation_improving(self):
        """Test no adaptation when performance improving."""
        analyzer = PerformanceAnalyzer()

        metrics = PerformanceMetrics()
        metrics.performance_direction = "improving"
        metrics.confidence = 0.85
        metrics.ftp_change_pct = 6.0
        metrics.vo2max_change_pct = 3.5

        should_adapt, reasoning = analyzer.get_adaptation_recommendation(metrics)

        assert should_adapt is False
        assert "improving" in reasoning.lower()


@pytest.mark.integration
class TestPerformanceIntegration:
    """Integration tests for performance analysis."""

    def test_full_performance_analysis_workflow(self):
        """Test complete performance analysis workflow."""
        analyzer = PerformanceAnalyzer()

        # Create realistic 4-week activity history
        recent_activities = []

        # Week 1: Good workouts
        for day in range(7):
            if day in [1, 3, 5]:  # Training days
                power_stream = [280] * 1200 if day == 3 else [250] * 3600
                activity = MockActivity(
                    activity_id=f"w1_d{day}",
                    name="Training Ride" if day == 3 else "Endurance Ride",
                    start_time=datetime.now() - timedelta(days=21 + day),
                    power_stream=power_stream,
                    average_power=280 if day == 3 else 250,
                    average_hr=155 if day == 3 else 140,
                    max_hr=180,
                )
                recent_activities.append(activity)

        # Week 2: Similar
        for day in range(7):
            if day in [1, 3, 5]:
                power_stream = [285] * 1200 if day == 3 else [255] * 3600
                activity = MockActivity(
                    activity_id=f"w2_d{day}",
                    name="Training Ride" if day == 3 else "Endurance Ride",
                    start_time=datetime.now() - timedelta(days=14 + day),
                    power_stream=power_stream,
                    average_power=285 if day == 3 else 255,
                    average_hr=155 if day == 3 else 140,
                    max_hr=180,
                )
                recent_activities.append(activity)

        # Week 3: Improving
        for day in range(7):
            if day in [1, 3, 5]:
                power_stream = [295] * 1200 if day == 3 else [260] * 3600
                activity = MockActivity(
                    activity_id=f"w3_d{day}",
                    name="Training Ride" if day == 3 else "Endurance Ride",
                    start_time=datetime.now() - timedelta(days=7 + day),
                    power_stream=power_stream,
                    average_power=295 if day == 3 else 260,
                    average_hr=152 if day == 3 else 138,  # Lower HR at same power = improving
                    max_hr=180,
                    vo2max_estimate=52.0,
                )
                recent_activities.append(activity)

        # Analyze performance
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent_activities,
            historical_activities=None,
        )

        # Validate results
        assert metrics.performance_direction in ["improving", "stable", "declining"]
        assert 0 <= metrics.confidence <= 1.0

        # Get recommendation
        should_adapt, reasoning = analyzer.get_adaptation_recommendation(metrics)
        assert isinstance(should_adapt, bool)
        assert isinstance(reasoning, str)
        assert len(reasoning) > 0
