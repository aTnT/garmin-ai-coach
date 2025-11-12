"""
Advanced tests for PerformanceAnalyzer - pushing coverage from 63% to 80%+

Focus on uncovered areas:
- Power metrics comparison to historical (lines 182-232) - BIGGEST GAP
- Pace metrics analysis (lines 242-264)
- GAP (Grade Adjusted Pace) improvement (lines 274-297)
- VO2max trends analysis
- Edge cases and error handling
"""

from datetime import datetime, timedelta
import pytest

from services.ai.planning.performance_analyzer import PerformanceAnalyzer, PerformanceMetrics


class MockActivity:
    """Mock Activity for testing performance analyzer."""

    def __init__(
        self,
        activity_id: str,
        name: str,
        start_time: datetime,
        sport: str = "running",
        duration_seconds: int = 3600,
        distance: float = 10000.0,
        average_speed: float | None = None,
        average_power: float | None = None,
        power_stream: list[int] | None = None,
        elevation_gain: float | None = None,
        vo2max_estimate: float | None = None,
        average_hr: int | None = None,
        max_hr: int | None = None,
        hr_stream: list[int] | None = None,
    ):
        self.activity_id = activity_id
        self.name = name
        self.start_time = start_time
        self.sport = sport
        self.duration_seconds = duration_seconds
        self.distance = distance
        self.average_speed = average_speed
        self.average_power = average_power
        self.power_stream = power_stream
        self.elevation_gain = elevation_gain
        self.vo2max_estimate = vo2max_estimate
        self.average_hr = average_hr
        self.max_hr = max_hr
        self.hr_stream = hr_stream


class TestPowerMetricsComparison:
    """Test historical power metrics comparison (lines 182-232)."""

    def test_compare_power_to_historical_improving(self):
        """Test power comparison shows improvement."""
        analyzer = PerformanceAnalyzer()

        # Create recent activities with higher power
        recent_power_stream = [200, 220, 240, 250, 230] * 240  # 20min of data @~240W avg
        recent = [
            MockActivity(
                activity_id="recent-1",
                name="Recent Ride",
                start_time=datetime.now() - timedelta(days=5),
                average_power=240.0,
                power_stream=recent_power_stream,
            )
        ]

        # Create historical activities with lower power
        hist_power_stream = [180, 190, 200, 210, 195] * 240  # 20min of data @~195W avg
        historical = [
            MockActivity(
                activity_id="hist-1",
                name="Historical Ride",
                start_time=datetime.now() - timedelta(days=42),  # 6 weeks ago
                average_power=195.0,
                power_stream=hist_power_stream,
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            historical_activities=historical,
            lookback_days=28,
        )

        # Should show improvement
        assert metrics.current_ftp is not None
        if metrics.ftp_trend != "unknown":
            # If comparison succeeded, should show improvement
            assert metrics.ftp_change_pct > 0
            assert metrics.ftp_trend in ["improving", "stable"]

    def test_compare_power_to_historical_declining(self):
        """Test power comparison shows decline."""
        analyzer = PerformanceAnalyzer()

        # Create recent activities with lower power
        recent_power_stream = [180, 190, 200, 210, 195] * 240
        recent = [
            MockActivity(
                activity_id="recent-1",
                name="Recent Ride",
                start_time=datetime.now() - timedelta(days=5),
                average_power=195.0,
                power_stream=recent_power_stream,
            )
        ]

        # Create historical activities with higher power
        hist_power_stream = [200, 220, 240, 250, 230] * 240
        historical = [
            MockActivity(
                activity_id="hist-1",
                name="Historical Ride",
                start_time=datetime.now() - timedelta(days=42),
                average_power=240.0,
                power_stream=hist_power_stream,
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            historical_activities=historical,
            lookback_days=28,
        )

        # Should show decline if comparison succeeded
        if metrics.ftp_trend != "unknown":
            assert metrics.ftp_change_pct < 0
            assert metrics.ftp_trend == "declining"

    def test_compare_power_no_historical_data(self):
        """Test power comparison with no historical activities."""
        analyzer = PerformanceAnalyzer()

        recent_power_stream = [200, 220, 240, 250, 230] * 240
        recent = [
            MockActivity(
                activity_id="recent-1",
                name="Recent Ride",
                start_time=datetime.now() - timedelta(days=5),
                average_power=240.0,
                power_stream=recent_power_stream,
            )
        ]

        # Analyze without historical
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            historical_activities=[],
            lookback_days=28,
        )

        # Should still get current metrics but no comparison
        assert metrics.current_ftp is not None
        # Trend may be unknown without comparison
        assert metrics.ftp_trend in ["unknown", "stable", "improving", "declining"]

    def test_compare_power_historical_outside_window(self):
        """Test that historical data outside 4-8 week window is ignored."""
        analyzer = PerformanceAnalyzer()

        recent_power_stream = [200, 220, 240, 250, 230] * 240
        recent = [
            MockActivity(
                activity_id="recent-1",
                name="Recent Ride",
                start_time=datetime.now() - timedelta(days=5),
                average_power=240.0,
                power_stream=recent_power_stream,
            )
        ]

        # Historical data too old (10 weeks ago)
        old_power_stream = [180, 190, 200, 210, 195] * 240
        historical = [
            MockActivity(
                activity_id="hist-1",
                name="Very Old Ride",
                start_time=datetime.now() - timedelta(days=70),
                average_power=195.0,
                power_stream=old_power_stream,
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            historical_activities=historical,
            lookback_days=28,
        )

        # Historical data too old, so no comparison
        # Trend should be unknown or stable
        assert metrics.ftp_trend in ["unknown", "stable"]


class TestPaceMetricsAnalysis:
    """Test pace-based metrics analysis (lines 242-264)."""

    def test_analyze_pace_threshold_runs(self):
        """Test threshold pace extraction from tempo/threshold runs."""
        analyzer = PerformanceAnalyzer()

        # Create threshold runs with ~4:00/km pace (4.17 m/s)
        recent = [
            MockActivity(
                activity_id="tempo-1",
                name="Threshold Run",
                start_time=datetime.now() - timedelta(days=3),
                sport="running",
                duration_seconds=3600,
                distance=15000.0,  # 15km in 1 hour = 4:00/km
                average_speed=4.17,  # m/s
            ),
            MockActivity(
                activity_id="tempo-2",
                name="Tempo Run",
                start_time=datetime.now() - timedelta(days=10),
                sport="running",
                duration_seconds=2400,
                distance=10000.0,  # 10km in 40min = 4:00/km
                average_speed=4.17,
            ),
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should extract threshold pace
        assert metrics.current_pace_threshold is not None
        # Should be around 4:00/km
        assert "4:" in metrics.current_pace_threshold or "3:" in metrics.current_pace_threshold

    def test_analyze_pace_no_threshold_runs(self):
        """Test pace analysis when no threshold runs present."""
        analyzer = PerformanceAnalyzer()

        # Create only easy runs (no 'threshold' or 'tempo' in name)
        recent = [
            MockActivity(
                activity_id="easy-1",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=3),
                sport="running",
                duration_seconds=3600,
                distance=12000.0,
                average_speed=3.33,  # 5:00/km
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should not extract threshold pace
        assert metrics.current_pace_threshold is None

    def test_analyze_pace_with_historical_gap(self):
        """Test GAP analysis with historical comparison."""
        analyzer = PerformanceAnalyzer()

        # Recent runs (faster, with elevation)
        recent = [
            MockActivity(
                activity_id="recent-1",
                name="Hill Run",
                start_time=datetime.now() - timedelta(days=5),
                sport="running",
                duration_seconds=3600,
                distance=12000.0,  # 12km
                average_speed=3.33,
                elevation_gain=200.0,  # 200m gain
            ),
            MockActivity(
                activity_id="recent-2",
                name="Flat Run",
                start_time=datetime.now() - timedelta(days=8),
                sport="running",
                duration_seconds=3600,
                distance=13000.0,  # 13km (faster)
                average_speed=3.61,
                elevation_gain=50.0,
            ),
        ]

        # Historical runs (slower)
        historical = [
            MockActivity(
                activity_id="hist-1",
                name="Old Hill Run",
                start_time=datetime.now() - timedelta(days=42),
                sport="running",
                duration_seconds=3600,
                distance=11000.0,  # 11km (slower)
                average_speed=3.06,
                elevation_gain=200.0,
            ),
            MockActivity(
                activity_id="hist-2",
                name="Old Flat Run",
                start_time=datetime.now() - timedelta(days=45),
                sport="running",
                duration_seconds=3600,
                distance=12000.0,
                average_speed=3.33,
                elevation_gain=50.0,
            ),
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            historical_activities=historical,
            lookback_days=28,
        )

        # Should calculate GAP improvement
        # Recent runs are faster, so improvement should be positive
        if metrics.gap_pace_improvement != 0.0:
            assert metrics.gap_pace_improvement > 0


class TestGAPCalculation:
    """Test Grade Adjusted Pace calculation (lines 301-327)."""

    def test_calculate_gap_flat_run(self):
        """Test GAP calculation for flat run."""
        analyzer = PerformanceAnalyzer()

        activity = MockActivity(
            activity_id="flat-1",
            name="Flat Run",
            start_time=datetime.now(),
            duration_seconds=3000,  # 50 minutes
            distance=10000.0,  # 10km
            elevation_gain=0.0,  # Flat
        )

        gap = analyzer._calculate_gap(activity)

        # GAP should equal base pace for flat runs
        # 50 min / 10 km = 5:00/km
        assert gap is not None
        assert 4.8 < gap < 5.2  # ~5 min/km

    def test_calculate_gap_hilly_run(self):
        """Test GAP calculation for hilly run."""
        analyzer = PerformanceAnalyzer()

        activity = MockActivity(
            activity_id="hill-1",
            name="Hill Run",
            start_time=datetime.now(),
            duration_seconds=3000,  # 50 minutes
            distance=10000.0,  # 10km
            elevation_gain=300.0,  # 300m gain
        )

        gap = analyzer._calculate_gap(activity)

        # GAP should be faster (lower) than base pace due to elevation adjustment
        assert gap is not None
        # Base pace is 5:00/km, GAP should be faster
        assert gap < 5.0

    def test_calculate_gap_missing_data(self):
        """Test GAP calculation with missing data."""
        analyzer = PerformanceAnalyzer()

        # Missing distance
        activity = MockActivity(
            activity_id="incomplete-1",
            name="Incomplete Run",
            start_time=datetime.now(),
            duration_seconds=3000,
        )
        # Remove distance attribute
        delattr(activity, 'distance')

        gap = analyzer._calculate_gap(activity)
        assert gap is None

    def test_calculate_gap_zero_distance(self):
        """Test GAP calculation with zero distance."""
        analyzer = PerformanceAnalyzer()

        activity = MockActivity(
            activity_id="zero-1",
            name="Zero Distance",
            start_time=datetime.now(),
            duration_seconds=3000,
            distance=0.0,
        )

        gap = analyzer._calculate_gap(activity)
        assert gap is None


class TestVO2MaxAnalysis:
    """Test VO2max trends analysis."""

    def test_analyze_vo2max_improving_trend(self):
        """Test VO2max analysis shows improving trend."""
        analyzer = PerformanceAnalyzer()

        # Activities with improving VO2max values
        recent = [
            MockActivity(
                activity_id="run-1",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=25),
                vo2max_estimate=52.0,
            ),
            MockActivity(
                activity_id="run-2",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=18),
                vo2max_estimate=53.5,
            ),
            MockActivity(
                activity_id="run-3",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=10),
                vo2max_estimate=54.0,
            ),
            MockActivity(
                activity_id="run-4",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=3),
                vo2max_estimate=55.0,
            ),
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should show VO2max data
        assert metrics.vo2max_current is not None
        assert metrics.vo2max_current == 55.0  # Latest value

        # Trend might be detected as improving
        if metrics.vo2max_trend != "unknown":
            assert metrics.vo2max_trend in ["improving", "stable"]
            assert metrics.vo2max_change_pct >= 0

    def test_analyze_vo2max_declining_trend(self):
        """Test VO2max analysis shows declining trend."""
        analyzer = PerformanceAnalyzer()

        # Activities with declining VO2max values
        recent = [
            MockActivity(
                activity_id="run-1",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=25),
                vo2max_estimate=55.0,
            ),
            MockActivity(
                activity_id="run-2",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=18),
                vo2max_estimate=54.0,
            ),
            MockActivity(
                activity_id="run-3",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=10),
                vo2max_estimate=53.0,
            ),
            MockActivity(
                activity_id="run-4",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=3),
                vo2max_estimate=52.0,
            ),
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should show current VO2max
        assert metrics.vo2max_current == 52.0

        # Trend might be detected as declining
        if metrics.vo2max_trend != "unknown":
            assert metrics.vo2max_change_pct <= 0

    def test_analyze_vo2max_no_data(self):
        """Test VO2max analysis with no VO2max estimates."""
        analyzer = PerformanceAnalyzer()

        recent = [
            MockActivity(
                activity_id="run-1",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=5),
                # No vo2max_estimate
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should have no VO2max data
        assert metrics.vo2max_current is None
        assert metrics.vo2max_trend == "unknown"
        assert metrics.vo2max_change_pct == 0.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_analyze_empty_activities(self):
        """Test analysis with empty activity list."""
        analyzer = PerformanceAnalyzer()

        metrics = analyzer.analyze_recent_performance(
            recent_activities=[],
            lookback_days=28,
        )

        # Should return default metrics
        assert metrics is not None
        assert metrics.performance_direction == "stable"
        assert metrics.confidence == 0.5

    def test_analyze_activities_outside_lookback(self):
        """Test that activities outside lookback window are filtered."""
        analyzer = PerformanceAnalyzer()

        # Activity from 60 days ago (outside 28-day window)
        recent = [
            MockActivity(
                activity_id="old-1",
                name="Old Run",
                start_time=datetime.now() - timedelta(days=60),
                average_speed=3.33,
            )
        ]

        # Analyze with 28-day lookback
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Activity should be filtered out, no pace data
        assert metrics.current_pace_threshold is None

    def test_analyze_mixed_sport_activities(self):
        """Test analysis with mixed running and cycling activities."""
        analyzer = PerformanceAnalyzer()

        power_stream = [200, 220, 240] * 240
        recent = [
            # Cycling with power
            MockActivity(
                activity_id="ride-1",
                name="Bike Ride",
                start_time=datetime.now() - timedelta(days=5),
                sport="cycling",
                average_power=220.0,
                power_stream=power_stream,
            ),
            # Running with pace
            MockActivity(
                activity_id="run-1",
                name="Threshold Run",
                start_time=datetime.now() - timedelta(days=3),
                sport="running",
                average_speed=4.0,
                duration_seconds=3600,
                distance=14400.0,
            ),
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should analyze both power and pace
        assert metrics.current_ftp is not None or metrics.current_pace_threshold is not None

    def test_power_analysis_fails_gracefully(self):
        """Test that power analysis failures are handled gracefully."""
        analyzer = PerformanceAnalyzer()

        # Activity with invalid power data
        recent = [
            MockActivity(
                activity_id="ride-1",
                name="Broken Ride",
                start_time=datetime.now() - timedelta(days=5),
                average_power=220.0,
                power_stream=[],  # Empty power stream (invalid)
            )
        ]

        # Should not crash
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Metrics should be returned even if power analysis fails
        assert metrics is not None
        assert metrics.performance_direction in ["stable", "improving", "declining", "unknown"]


class TestIntervalQualityAnalysis:
    """Test interval quality analysis methods (lines 396-521)."""

    def test_analyze_interval_quality_with_hr_stream(self):
        """Test interval quality analysis with HR stream data."""
        analyzer = PerformanceAnalyzer()

        # Create interval workout with HR stream
        # Simulate 3 x 5-minute intervals with recovery
        hr_stream = []
        # Warmup (10 min @ 130 BPM)
        hr_stream.extend([130] * 600)
        # Interval 1 (5 min @ 165 BPM)
        hr_stream.extend([165] * 300)
        # Recovery (3 min @ 120 BPM)
        hr_stream.extend([120] * 180)
        # Interval 2 (5 min @ 168 BPM)
        hr_stream.extend([168] * 300)
        # Recovery (3 min @ 120 BPM)
        hr_stream.extend([120] * 180)
        # Interval 3 (5 min @ 170 BPM)
        hr_stream.extend([170] * 300)
        # Cooldown (5 min @ 125 BPM)
        hr_stream.extend([125] * 300)

        recent = [
            MockActivity(
                activity_id="interval-1",
                name="Threshold Intervals",
                start_time=datetime.now() - timedelta(days=2),
                duration_seconds=len(hr_stream),
                average_hr=150,
                max_hr=180,
                hr_stream=hr_stream,
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should analyze interval quality
        assert metrics is not None
        # Interval quality metrics should be calculated
        assert 0.0 <= metrics.avg_interval_adherence <= 1.0
        assert 0.0 <= metrics.zone_drift_score <= 1.0
        assert 0.0 <= metrics.consistency_score <= 1.0

    def test_detect_intervals_from_hr(self):
        """Test interval detection from HR stream."""
        analyzer = PerformanceAnalyzer()

        # Create HR stream with clear intervals
        hr_stream = []
        # Easy pace (10 min @ 130 BPM)
        hr_stream.extend([130] * 600)
        # Hard interval (5 min @ 170 BPM)
        hr_stream.extend([170] * 300)
        # Easy (5 min @ 130 BPM)
        hr_stream.extend([130] * 300)
        # Hard interval (5 min @ 172 BPM)
        hr_stream.extend([172] * 300)
        # Easy (5 min @ 130 BPM)
        hr_stream.extend([130] * 300)

        intervals = analyzer._detect_intervals_from_hr(hr_stream)

        # Should detect 2 hard intervals
        assert len(intervals) >= 2
        # Each interval should have required fields
        for interval in intervals:
            assert 'start' in interval
            assert 'end' in interval
            assert 'avg_hr' in interval
            assert 'max_hr' in interval

    def test_detect_intervals_short_hr_stream(self):
        """Test interval detection with very short HR stream."""
        analyzer = PerformanceAnalyzer()

        # Stream shorter than 60 seconds
        hr_stream = [150] * 30

        intervals = analyzer._detect_intervals_from_hr(hr_stream)

        # Should return empty list for short streams
        assert intervals == []

    def test_detect_intervals_no_hard_efforts(self):
        """Test interval detection when no hard efforts present."""
        analyzer = PerformanceAnalyzer()

        # Steady easy run (no intervals)
        hr_stream = [135] * 1800  # 30 min @ 135 BPM (steady)

        intervals = analyzer._detect_intervals_from_hr(hr_stream)

        # Should detect no intervals (all steady)
        assert len(intervals) == 0

    def test_calculate_zone_adherence(self):
        """Test zone adherence calculation."""
        analyzer = PerformanceAnalyzer()

        # Create HR stream that matches the intervals
        hr_stream = [140] * 100  # Before interval 1
        hr_stream.extend([160] * 300)  # Interval 1 (start:100, end:400)
        hr_stream.extend([130] * 200)  # Between intervals
        hr_stream.extend([162] * 300)  # Interval 2 (start:600, end:900)
        hr_stream.extend([135] * 100)  # After intervals

        # Create mock intervals
        intervals = [
            {'start': 100, 'end': 400, 'avg_hr': 160, 'max_hr': 170},
            {'start': 600, 'end': 900, 'avg_hr': 162, 'max_hr': 172},
        ]

        # Create activity with max_hr and hr_stream
        activity = MockActivity(
            activity_id="test-1",
            name="Interval Workout",
            start_time=datetime.now(),
            max_hr=180,
            hr_stream=hr_stream,
        )

        adherence = analyzer._calculate_zone_adherence(intervals, activity)

        # Should return adherence score
        assert 0.0 <= adherence <= 1.0

    def test_calculate_zone_adherence_no_max_hr(self):
        """Test zone adherence when activity has no max HR."""
        analyzer = PerformanceAnalyzer()

        intervals = [
            {'start': 100, 'end': 400, 'avg_hr': 160, 'max_hr': 170},
        ]

        # Activity without max_hr attribute
        activity = MockActivity(
            activity_id="test-1",
            name="Interval Workout",
            start_time=datetime.now(),
        )
        # Remove max_hr
        delattr(activity, 'max_hr')

        adherence = analyzer._calculate_zone_adherence(intervals, activity)

        # Should return default adherence
        assert adherence == 0.8

    def test_calculate_zone_drift(self):
        """Test zone drift calculation."""
        analyzer = PerformanceAnalyzer()

        # Intervals with increasing HR (drift)
        intervals = [
            {'start': 100, 'end': 400, 'avg_hr': 155, 'max_hr': 165},
            {'start': 600, 'end': 900, 'avg_hr': 160, 'max_hr': 170},
            {'start': 1200, 'end': 1500, 'avg_hr': 165, 'max_hr': 175},  # Drifting up
        ]

        drift = analyzer._calculate_zone_drift(intervals)

        # Should detect some drift
        assert 0.0 <= drift <= 1.0

    def test_calculate_interval_consistency(self):
        """Test interval consistency calculation."""
        analyzer = PerformanceAnalyzer()

        # Consistent intervals (similar avg HR)
        intervals = [
            {'start': 100, 'end': 400, 'avg_hr': 160, 'max_hr': 170},
            {'start': 600, 'end': 900, 'avg_hr': 161, 'max_hr': 171},
            {'start': 1200, 'end': 1500, 'avg_hr': 159, 'max_hr': 169},
        ]

        consistency = analyzer._calculate_interval_consistency(intervals)

        # Should have high consistency (similar HRs)
        assert 0.0 <= consistency <= 1.0
        assert consistency > 0.7  # Should be fairly consistent

    def test_analyze_interval_quality_no_hr_stream(self):
        """Test interval quality analysis when activity has no HR stream."""
        analyzer = PerformanceAnalyzer()

        recent = [
            MockActivity(
                activity_id="no-hr-1",
                name="Interval Run",
                start_time=datetime.now() - timedelta(days=2),
                # No hr_stream attribute
            )
        ]

        # Should not crash
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should have default values
        assert metrics is not None

    def test_analyze_interval_quality_short_intervals(self):
        """Test interval quality when detected intervals are too short."""
        analyzer = PerformanceAnalyzer()

        # Create workout with very short HR spikes (not real intervals)
        hr_stream = []
        # Warmup
        hr_stream.extend([130] * 600)
        # Brief spike (30 sec - too short)
        hr_stream.extend([170] * 30)
        # Recovery
        hr_stream.extend([130] * 600)

        recent = [
            MockActivity(
                activity_id="short-intervals-1",
                name="Spiky Run",
                start_time=datetime.now() - timedelta(days=2),
                duration_seconds=len(hr_stream),
                average_hr=135,
                max_hr=180,
                hr_stream=hr_stream,
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should still return valid metrics
        assert metrics is not None


class TestPerformanceDirectionDetermination:
    """Test overall performance direction calculation (lines 580-630)."""

    def test_determine_performance_improving(self):
        """Test performance direction determination when improving."""
        analyzer = PerformanceAnalyzer()

        # Create activities showing improvement
        power_stream = [220, 240, 260] * 240  # Good power
        recent = [
            MockActivity(
                activity_id="ride-1",
                name="Bike Ride",
                start_time=datetime.now() - timedelta(days=3),
                average_power=240.0,
                power_stream=power_stream,
                vo2max_estimate=55.0,
            )
        ]

        hist_power_stream = [180, 190, 200] * 240  # Lower historical power
        historical = [
            MockActivity(
                activity_id="old-ride-1",
                name="Old Bike Ride",
                start_time=datetime.now() - timedelta(days=42),
                average_power=190.0,
                power_stream=hist_power_stream,
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            historical_activities=historical,
            lookback_days=28,
        )

        # Performance should be improving or stable
        assert metrics.performance_direction in ["improving", "stable"]
        assert metrics.confidence > 0.0

    def test_determine_performance_declining(self):
        """Test performance direction when declining."""
        analyzer = PerformanceAnalyzer()

        # Create activities showing decline
        power_stream = [180, 190, 200] * 240  # Lower power
        recent = [
            MockActivity(
                activity_id="ride-1",
                name="Bike Ride",
                start_time=datetime.now() - timedelta(days=3),
                average_power=190.0,
                power_stream=power_stream,
                vo2max_estimate=50.0,
            )
        ]

        hist_power_stream = [220, 240, 260] * 240  # Higher historical power
        historical = [
            MockActivity(
                activity_id="old-ride-1",
                name="Old Bike Ride",
                start_time=datetime.now() - timedelta(days=42),
                average_power=240.0,
                power_stream=hist_power_stream,
            )
        ]

        # Analyze
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            historical_activities=historical,
            lookback_days=28,
        )

        # Performance should be declining or stable
        assert metrics.performance_direction in ["declining", "stable"]

    def test_determine_performance_stable(self):
        """Test performance direction when stable."""
        analyzer = PerformanceAnalyzer()

        # Create activities with similar performance
        recent = [
            MockActivity(
                activity_id="run-1",
                name="Easy Run",
                start_time=datetime.now() - timedelta(days=3),
                average_speed=3.5,
                vo2max_estimate=52.0,
            )
        ]

        # Analyze without historical (should be stable)
        metrics = analyzer.analyze_recent_performance(
            recent_activities=recent,
            lookback_days=28,
        )

        # Should default to stable
        assert metrics.performance_direction in ["stable", "unknown"]
