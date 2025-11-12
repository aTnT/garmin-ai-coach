"""
Performance Metrics Analyzer

Extracts and analyzes detailed workout performance data including power curves,
interval quality, FTP trends, and GAP pace for intelligent adaptation decisions.
"""

from datetime import date, datetime, timedelta
from typing import Any
import statistics

from services.garmin.models import Activity
from services.ai.power_curve import PowerCurveAnalyzer, PowerMetric
from services.ai.trends import TrendsAnalyzer, MetricType
from services.ai.workouts.workout_models import StructuredWorkout, IntensityZone, WorkoutType


class PerformanceMetrics:
    """Container for performance metrics analysis results."""

    def __init__(self):
        # FTP / Threshold metrics
        self.current_ftp: float | None = None
        self.ftp_trend: str = "unknown"  # "improving", "stable", "declining"
        self.ftp_change_pct: float = 0.0
        self.ftp_history: list[tuple[date, float]] = []

        # Power curve metrics
        self.power_5s: float | None = None
        self.power_1min: float | None = None
        self.power_5min: float | None = None
        self.power_20min: float | None = None
        self.power_60min: float | None = None
        self.power_curve_improving: bool = False

        # Critical Power
        self.cp: float | None = None
        self.w_prime: float | None = None
        self.cp_trend: str = "unknown"

        # VO2max
        self.vo2max_current: float | None = None
        self.vo2max_trend: str = "unknown"
        self.vo2max_change_pct: float = 0.0

        # Interval quality
        self.avg_interval_adherence: float = 1.0  # 0-1
        self.zone_drift_score: float = 0.0  # 0-1, 0=no drift
        self.consistency_score: float = 1.0  # 0-1 across reps

        # Pace metrics (running)
        self.current_pace_threshold: str | None = None  # min/km
        self.gap_pace_improvement: float = 0.0  # % change

        # Overall performance
        self.performance_direction: str = "stable"  # "improving", "stable", "declining"
        self.confidence: float = 0.5  # 0-1


class PerformanceAnalyzer:
    """Analyzes detailed workout performance for adaptation decisions."""

    def __init__(self):
        """Initialize performance analyzer."""
        self.power_analyzer = PowerCurveAnalyzer()
        self.trends_analyzer = TrendsAnalyzer()

    def analyze_recent_performance(
        self,
        recent_activities: list[Activity],
        historical_activities: list[Activity] | None = None,
        lookback_days: int = 28,
    ) -> PerformanceMetrics:
        """
        Comprehensive performance analysis from recent activities.

        Args:
            recent_activities: Activities from last 2-4 weeks
            historical_activities: Historical data for comparison (optional)
            lookback_days: Days of data to analyze

        Returns:
            PerformanceMetrics with detailed analysis
        """
        metrics = PerformanceMetrics()

        if not recent_activities:
            return metrics

        # Filter to recent period
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent = [a for a in recent_activities if a.start_time >= cutoff_date]

        # Analyze power-based metrics (cycling)
        power_activities = [a for a in recent if hasattr(a, 'average_power') and a.average_power]
        if power_activities:
            self._analyze_power_metrics(metrics, power_activities, historical_activities)

        # Analyze pace-based metrics (running)
        pace_activities = [a for a in recent if hasattr(a, 'average_speed') and a.average_speed]
        if pace_activities:
            self._analyze_pace_metrics(metrics, pace_activities, historical_activities)

        # Analyze VO2max trends (if available)
        self._analyze_vo2max_trends(metrics, recent_activities)

        # Analyze interval quality
        interval_activities = [a for a in recent if self._is_interval_workout(a)]
        if interval_activities:
            self._analyze_interval_quality(metrics, interval_activities)

        # Determine overall performance direction
        self._determine_performance_direction(metrics)

        return metrics

    def _analyze_power_metrics(
        self,
        metrics: PerformanceMetrics,
        recent_activities: list[Activity],
        historical_activities: list[Activity] | None,
    ) -> None:
        """Analyze power-based performance metrics."""
        # Convert activities to format for power analyzer
        activities_data = []
        for activity in recent_activities:
            if hasattr(activity, 'power_stream') and activity.power_stream:
                activities_data.append({
                    "activity_id": activity.activity_id,
                    "date": activity.start_time,
                    "name": activity.name,
                    "type": "Ride",
                    "power_stream": activity.power_stream,
                })

        if not activities_data:
            return

        # Generate current power curve
        try:
            power_curve = self.power_analyzer.generate_power_curve(
                athlete_name="athlete",
                activities_data=activities_data,
                metric_type=PowerMetric.POWER_WATTS,
                sport_type="cycling",
            )

            # Extract key powers
            metrics.power_5s = power_curve.peak_5_sec
            metrics.power_1min = power_curve.peak_1_min
            metrics.power_5min = power_curve.peak_5_min
            metrics.power_20min = power_curve.peak_20_min
            metrics.power_60min = power_curve.peak_60_min

            # Estimate FTP from 20min power
            if power_curve.peak_20_min:
                metrics.current_ftp = power_curve.peak_20_min * 0.95

            # Calculate Critical Power
            cp_model = self.power_analyzer.calculate_critical_power(
                power_curve.best_efforts, PowerMetric.POWER_WATTS
            )
            if cp_model:
                metrics.cp = cp_model.cp
                metrics.w_prime = cp_model.w_prime

            # Compare to historical if available
            if historical_activities:
                self._compare_power_to_historical(metrics, historical_activities)

        except Exception as e:
            # Handle case where power analysis fails
            print(f"Power analysis failed: {e}")

    def _compare_power_to_historical(
        self,
        metrics: PerformanceMetrics,
        historical_activities: list[Activity],
    ) -> None:
        """Compare current power metrics to historical baseline."""
        # Get historical data from 4-8 weeks ago
        start_date = datetime.now() - timedelta(days=56)  # 8 weeks
        end_date = datetime.now() - timedelta(days=28)  # 4 weeks

        historical = [
            a for a in historical_activities
            if start_date <= a.start_time <= end_date
        ]

        if not historical:
            return

        # Generate historical power curve
        hist_data = []
        for activity in historical:
            if hasattr(activity, 'power_stream') and activity.power_stream:
                hist_data.append({
                    "activity_id": activity.activity_id,
                    "date": activity.start_time,
                    "name": activity.name,
                    "type": "Ride",
                    "power_stream": activity.power_stream,
                })

        if not hist_data:
            return

        try:
            hist_curve = self.power_analyzer.generate_power_curve(
                athlete_name="athlete",
                activities_data=hist_data,
                metric_type=PowerMetric.POWER_WATTS,
                sport_type="cycling",
            )

            # Compare FTP
            if metrics.current_ftp and hist_curve.peak_20_min:
                historical_ftp = hist_curve.peak_20_min * 0.95
                metrics.ftp_change_pct = (
                    (metrics.current_ftp - historical_ftp) / historical_ftp * 100
                )

                if metrics.ftp_change_pct > 3:
                    metrics.ftp_trend = "improving"
                    metrics.power_curve_improving = True
                elif metrics.ftp_change_pct < -3:
                    metrics.ftp_trend = "declining"
                else:
                    metrics.ftp_trend = "stable"

        except Exception:
            pass

    def _analyze_pace_metrics(
        self,
        metrics: PerformanceMetrics,
        recent_activities: list[Activity],
        historical_activities: list[Activity] | None,
    ) -> None:
        """Analyze pace-based performance metrics (running)."""
        # Extract threshold pace (from tempo/threshold runs)
        threshold_activities = [
            a for a in recent_activities
            if 'threshold' in a.name.lower() or 'tempo' in a.name.lower()
        ]

        if threshold_activities:
            # Calculate average pace from threshold runs
            threshold_paces = []
            for activity in threshold_activities:
                if hasattr(activity, 'average_speed') and activity.average_speed:
                    # Convert m/s to min/km
                    pace_min_per_km = 1000 / (activity.average_speed * 60)
                    threshold_paces.append(pace_min_per_km)

            if threshold_paces:
                avg_threshold_pace = statistics.mean(threshold_paces)
                minutes = int(avg_threshold_pace)
                seconds = int((avg_threshold_pace - minutes) * 60)
                metrics.current_pace_threshold = f"{minutes}:{seconds:02d}/km"

        # GAP (Grade Adjusted Pace) analysis
        if historical_activities:
            self._analyze_gap_improvement(metrics, recent_activities, historical_activities)

    def _analyze_gap_improvement(
        self,
        metrics: PerformanceMetrics,
        recent_activities: list[Activity],
        historical_activities: list[Activity],
    ) -> None:
        """Analyze Grade Adjusted Pace improvement."""
        # Calculate average GAP for recent activities
        recent_gap_values = []
        for activity in recent_activities:
            gap = self._calculate_gap(activity)
            if gap:
                recent_gap_values.append(gap)

        # Calculate average GAP for historical activities
        historical_gap_values = []
        start_date = datetime.now() - timedelta(days=56)
        end_date = datetime.now() - timedelta(days=28)

        for activity in historical_activities:
            if start_date <= activity.start_time <= end_date:
                gap = self._calculate_gap(activity)
                if gap:
                    historical_gap_values.append(gap)

        # Compare
        if recent_gap_values and historical_gap_values:
            recent_avg = statistics.mean(recent_gap_values)
            historical_avg = statistics.mean(historical_gap_values)

            # Lower GAP is better (faster)
            metrics.gap_pace_improvement = (
                (historical_avg - recent_avg) / historical_avg * 100
            )

    def _calculate_gap(self, activity: Activity) -> float | None:
        """
        Calculate Grade Adjusted Pace for an activity.

        GAP adjusts pace based on elevation gain to normalize for hills.
        Formula: Adjusted time = actual_time × (1 + gain_meters × 0.001)
        """
        if not (hasattr(activity, 'distance') and hasattr(activity, 'duration_seconds')):
            return None

        distance_km = activity.distance / 1000
        duration_hours = activity.duration_seconds / 3600

        if distance_km == 0:
            return None

        # Base pace (min/km)
        base_pace = (duration_hours * 60) / distance_km

        # Adjust for elevation gain if available
        if hasattr(activity, 'elevation_gain') and activity.elevation_gain:
            # Add ~10 seconds per meter of gain per km
            adjustment_factor = 1 + (activity.elevation_gain / distance_km * 0.001)
            gap = base_pace / adjustment_factor
            return gap

        return base_pace

    def _analyze_vo2max_trends(
        self,
        metrics: PerformanceMetrics,
        recent_activities: list[Activity],
    ) -> None:
        """Analyze VO2max trends if available from Garmin."""
        # Extract VO2max values from activities
        vo2max_values = []
        for activity in recent_activities:
            if hasattr(activity, 'vo2max_estimate') and activity.vo2max_estimate:
                vo2max_values.append((activity.start_time.date(), activity.vo2max_estimate))

        if not vo2max_values:
            return

        # Get most recent
        vo2max_values.sort(key=lambda x: x[0], reverse=True)
        metrics.vo2max_current = vo2max_values[0][1]

        # Analyze trend if we have multiple data points
        if len(vo2max_values) >= 3:
            recent_vo2 = statistics.mean([v[1] for v in vo2max_values[:3]])
            older_vo2 = statistics.mean([v[1] for v in vo2max_values[-3:]])

            metrics.vo2max_change_pct = ((recent_vo2 - older_vo2) / older_vo2) * 100

            if metrics.vo2max_change_pct > 2:
                metrics.vo2max_trend = "improving"
            elif metrics.vo2max_change_pct < -2:
                metrics.vo2max_trend = "declining"
            else:
                metrics.vo2max_trend = "stable"

    def _analyze_interval_quality(
        self,
        metrics: PerformanceMetrics,
        interval_activities: list[Activity],
    ) -> None:
        """Analyze quality of interval execution."""
        adherence_scores = []
        drift_scores = []
        consistency_scores = []

        for activity in interval_activities:
            # Analyze interval adherence
            analysis = self._analyze_single_interval_workout(activity)

            if analysis:
                adherence_scores.append(analysis['adherence'])
                drift_scores.append(analysis['drift'])
                consistency_scores.append(analysis['consistency'])

        # Calculate averages
        if adherence_scores:
            metrics.avg_interval_adherence = statistics.mean(adherence_scores)
            metrics.zone_drift_score = statistics.mean(drift_scores)
            metrics.consistency_score = statistics.mean(consistency_scores)

    def _analyze_single_interval_workout(
        self, activity: Activity
    ) -> dict[str, float] | None:
        """
        Analyze a single interval workout for quality metrics.

        Returns:
            Dict with adherence, drift, and consistency scores (0-1)
        """
        if not hasattr(activity, 'hr_stream') or not activity.hr_stream:
            return None

        hr_stream = activity.hr_stream

        # Detect intervals (simplified - look for HR spikes)
        intervals = self._detect_intervals_from_hr(hr_stream)

        if len(intervals) < 2:
            return None

        # Calculate adherence (% of time in target zones)
        adherence = self._calculate_zone_adherence(intervals, activity)

        # Calculate drift (how much zones drifted during workout)
        drift = self._calculate_zone_drift(intervals)

        # Calculate consistency (how similar were the intervals)
        consistency = self._calculate_interval_consistency(intervals)

        return {
            'adherence': adherence,
            'drift': drift,
            'consistency': consistency,
        }

    def _detect_intervals_from_hr(
        self, hr_stream: list[float]
    ) -> list[dict[str, Any]]:
        """
        Detect interval segments from HR stream.

        Returns:
            List of intervals with start, end, avg_hr
        """
        if len(hr_stream) < 60:  # Need at least 1 minute
            return []

        intervals = []
        in_interval = False
        interval_start = 0

        # Calculate rolling average HR
        window_size = 30  # 30 seconds
        avg_hr = statistics.mean(hr_stream[:window_size]) if len(hr_stream) >= window_size else statistics.mean(hr_stream)

        # Threshold for "hard" interval (20% above average)
        hard_threshold = avg_hr * 1.20

        for i in range(len(hr_stream)):
            if hr_stream[i] > hard_threshold:
                if not in_interval:
                    interval_start = i
                    in_interval = True
            else:
                if in_interval:
                    # End of interval
                    if i - interval_start > 60:  # At least 1 minute
                        interval_hr = hr_stream[interval_start:i]
                        intervals.append({
                            'start': interval_start,
                            'end': i,
                            'avg_hr': statistics.mean(interval_hr),
                            'max_hr': max(interval_hr),
                        })
                    in_interval = False

        return intervals

    def _calculate_zone_adherence(
        self, intervals: list[dict], activity: Activity
    ) -> float:
        """Calculate % of interval time in target zones."""
        if not intervals or not hasattr(activity, 'max_hr'):
            return 0.8  # Default moderate adherence

        # Assume target is Z4 (80-90% max HR)
        target_min = activity.max_hr * 0.80 if activity.max_hr else 150
        target_max = activity.max_hr * 0.90 if activity.max_hr else 170

        in_zone_count = 0
        total_count = 0

        hr_stream = activity.hr_stream if hasattr(activity, 'hr_stream') else []

        for interval in intervals:
            segment = hr_stream[interval['start']:interval['end']]
            for hr in segment:
                total_count += 1
                if target_min <= hr <= target_max:
                    in_zone_count += 1

        return in_zone_count / total_count if total_count > 0 else 0.8

    def _calculate_zone_drift(self, intervals: list[dict]) -> float:
        """Calculate how much HR drifted across intervals (0=no drift, 1=high drift)."""
        if len(intervals) < 2:
            return 0.0

        # Compare first and last interval average HRs
        first_hr = intervals[0]['avg_hr']
        last_hr = intervals[-1]['avg_hr']

        drift_pct = abs(last_hr - first_hr) / first_hr

        # Normalize to 0-1 scale (>10% drift = 1.0)
        return min(1.0, drift_pct / 0.10)

    def _calculate_interval_consistency(self, intervals: list[dict]) -> float:
        """Calculate consistency across intervals (1=perfect, 0=very inconsistent)."""
        if len(intervals) < 2:
            return 1.0

        avg_hrs = [interval['avg_hr'] for interval in intervals]

        # Calculate coefficient of variation
        mean_hr = statistics.mean(avg_hrs)
        std_hr = statistics.stdev(avg_hrs) if len(avg_hrs) > 1 else 0

        cv = std_hr / mean_hr if mean_hr > 0 else 0

        # Convert to consistency score (low CV = high consistency)
        # CV < 0.05 = perfect, CV > 0.15 = poor
        consistency = max(0, 1 - (cv / 0.15))

        return consistency

    def _is_interval_workout(self, activity: Activity) -> bool:
        """Determine if activity is an interval workout."""
        name_lower = activity.name.lower()
        interval_keywords = [
            'interval', 'threshold', 'tempo', 'vo2', 'hard',
            'workout', 'speed', 'fartlek', 'hill'
        ]

        return any(keyword in name_lower for keyword in interval_keywords)

    def _determine_performance_direction(self, metrics: PerformanceMetrics) -> None:
        """Determine overall performance direction from all metrics."""
        improvement_indicators = 0
        decline_indicators = 0
        total_indicators = 0

        # Check FTP trend
        if metrics.ftp_trend != "unknown":
            total_indicators += 1
            if metrics.ftp_trend == "improving":
                improvement_indicators += 1
            elif metrics.ftp_trend == "declining":
                decline_indicators += 1

        # Check power curve
        if metrics.power_curve_improving:
            improvement_indicators += 1
            total_indicators += 1

        # Check VO2max trend
        if metrics.vo2max_trend != "unknown":
            total_indicators += 1
            if metrics.vo2max_trend == "improving":
                improvement_indicators += 1
            elif metrics.vo2max_trend == "declining":
                decline_indicators += 1

        # Check interval quality
        if metrics.avg_interval_adherence > 0:
            total_indicators += 1
            if metrics.avg_interval_adherence >= 0.85:
                improvement_indicators += 0.5
            elif metrics.avg_interval_adherence < 0.70:
                decline_indicators += 0.5

        # Determine direction
        if total_indicators == 0:
            metrics.performance_direction = "stable"
            metrics.confidence = 0.3
        else:
            improvement_ratio = improvement_indicators / total_indicators
            decline_ratio = decline_indicators / total_indicators

            if improvement_ratio > 0.6:
                metrics.performance_direction = "improving"
                metrics.confidence = min(0.9, improvement_ratio)
            elif decline_ratio > 0.6:
                metrics.performance_direction = "declining"
                metrics.confidence = min(0.9, decline_ratio)
            else:
                metrics.performance_direction = "stable"
                metrics.confidence = 0.6

    def get_adaptation_recommendation(
        self, metrics: PerformanceMetrics
    ) -> tuple[bool, str]:
        """
        Get adaptation recommendation based on performance metrics.

        Returns:
            Tuple of (should_adapt, reasoning)
        """
        # Strong performance decline
        if metrics.performance_direction == "declining" and metrics.confidence > 0.7:
            if metrics.ftp_trend == "declining" and metrics.ftp_change_pct < -5:
                return (
                    True,
                    f"FTP declined {metrics.ftp_change_pct:.1f}% - athlete needs recovery period"
                )

            if metrics.vo2max_trend == "declining" and metrics.vo2max_change_pct < -3:
                return (
                    True,
                    f"VO2max declined {metrics.vo2max_change_pct:.1f}% - reduce intensity"
                )

        # Poor interval quality
        if metrics.avg_interval_adherence < 0.70:
            return (
                True,
                f"Poor interval execution ({metrics.avg_interval_adherence:.1%}) - athlete struggling with prescribed zones"
            )

        # High zone drift (fatigue during workout)
        if metrics.zone_drift_score > 0.5:
            return (
                True,
                "Significant HR drift during intervals - reduce training load"
            )

        # Performance improving - continue even if readiness moderate
        if metrics.performance_direction == "improving" and metrics.confidence > 0.7:
            return (
                False,
                f"Performance improving (FTP: {metrics.ftp_change_pct:+.1f}%, VO2max: {metrics.vo2max_change_pct:+.1f}%) - continue as planned"
            )

        return (False, "Performance metrics within normal range")
