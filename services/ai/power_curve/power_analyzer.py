"""
Power Curve and Critical Power Analyzer

Analyzes power/pace data to generate power curves and calculate Critical Power.
"""

from datetime import datetime, timedelta
from typing import Any

import numpy as np
from numpy.polynomial import Polynomial

from .power_models import (
    BestEffort,
    CriticalPower,
    CriticalPowerHistory,
    FitnessProfile,
    FitnessSignature,
    PowerCurve,
    PowerCurveComparison,
    PowerMetric,
    TrainingZones,
)


class PowerCurveAnalyzer:
    """Analyzes power/pace data to generate curves and calculate Critical Power."""

    # Standard durations to analyze (in seconds)
    STANDARD_DURATIONS = [
        5, 10, 30,  # Sprint
        60, 120, 300,  # Short
        600, 1200, 1800,  # Mid
        3600, 5400, 7200,  # Long
        10800, 14400, 18000  # Very long
    ]

    # Durations to use for CP calculation (typically 3-20 min efforts)
    CP_CALCULATION_DURATIONS = [180, 300, 600, 1200]  # 3, 5, 10, 20 min

    def __init__(self):
        """Initialize the power curve analyzer."""
        pass

    def extract_best_efforts(
        self,
        activities_data: list[dict[str, Any]],
        metric_type: PowerMetric,
        sport_type: str = "cycling",
    ) -> list[BestEffort]:
        """
        Extract best efforts across all standard durations from activities.

        Args:
            activities_data: List of activity dictionaries with power/pace streams
            metric_type: Type of metric (power or pace)
            sport_type: Type of sport

        Returns:
            List of BestEffort objects
        """
        # Track best for each duration
        best_by_duration: dict[int, BestEffort] = {}

        for activity in activities_data:
            activity_id = activity.get("activity_id", "unknown")
            activity_date = activity.get("date")
            activity_name = activity.get("name", "")
            activity_type = activity.get("type", sport_type)

            # Get power or pace stream
            power_stream = activity.get("power_stream") or activity.get("pace_stream")
            if not power_stream or len(power_stream) < 10:
                continue  # Need at least 10 seconds of data

            # For each standard duration, find best effort in this activity
            for duration in self.STANDARD_DURATIONS:
                if duration > len(power_stream):
                    continue  # Duration longer than activity

                # Find best average power for this duration
                best_avg = self._find_best_average(power_stream, duration, metric_type)

                if best_avg is None:
                    continue

                # Check if this is a personal best for this duration
                if duration not in best_by_duration or self._is_better(
                    best_avg, best_by_duration[duration].value, metric_type
                ):
                    best_by_duration[duration] = BestEffort(
                        duration_seconds=duration,
                        duration_label=self._duration_to_label(duration),
                        value=best_avg,
                        metric_type=metric_type,
                        activity_id=activity_id,
                        activity_date=activity_date,
                        activity_name=activity_name,
                        activity_type=activity_type,
                        normalized=False,
                        average=True,
                    )

        return list(best_by_duration.values())

    def _find_best_average(
        self, stream: list[float], duration: int, metric_type: PowerMetric
    ) -> float | None:
        """
        Find the best average value for a given duration in a data stream.

        Args:
            stream: Power or pace data stream
            duration: Duration in seconds
            metric_type: Type of metric

        Returns:
            Best average value or None
        """
        if len(stream) < duration:
            return None

        # Use sliding window to find best average
        window_sums = []
        for i in range(len(stream) - duration + 1):
            window = stream[i : i + duration]
            # Filter out zeros and invalid values
            valid_values = [v for v in window if v > 0]
            if len(valid_values) >= duration * 0.8:  # At least 80% valid data
                window_sums.append(sum(valid_values) / len(valid_values))

        if not window_sums:
            return None

        # For power: best = max
        # For pace: best = min (faster)
        if metric_type in [PowerMetric.PACE_MIN_PER_KM, PowerMetric.PACE_MIN_PER_MILE]:
            return min(window_sums)
        else:
            return max(window_sums)

    def _is_better(
        self, new_value: float, old_value: float, metric_type: PowerMetric
    ) -> bool:
        """Check if new value is better than old value."""
        if metric_type in [PowerMetric.PACE_MIN_PER_KM, PowerMetric.PACE_MIN_PER_MILE]:
            return new_value < old_value  # Lower pace is better
        else:
            return new_value > old_value  # Higher power is better

    def _duration_to_label(self, duration_seconds: int) -> str:
        """Convert duration in seconds to human-readable label."""
        if duration_seconds < 60:
            return f"{duration_seconds}s"
        elif duration_seconds < 3600:
            minutes = duration_seconds // 60
            return f"{minutes}min"
        else:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h{minutes}m"
            return f"{hours}hr"

    def generate_power_curve(
        self,
        athlete_name: str,
        activities_data: list[dict[str, Any]],
        metric_type: PowerMetric,
        sport_type: str = "cycling",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> PowerCurve:
        """
        Generate a complete power curve from activity data.

        Args:
            athlete_name: Athlete's name
            activities_data: List of activities with power/pace data
            metric_type: Type of metric
            sport_type: Type of sport
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            PowerCurve object
        """
        # Extract best efforts
        best_efforts = self.extract_best_efforts(activities_data, metric_type, sport_type)

        # Sort by duration
        best_efforts.sort(key=lambda e: e.duration_seconds)

        # Determine date range
        if start_date is None and best_efforts:
            dates = [e.activity_date for e in best_efforts if e.activity_date]
            start_date = min(dates) if dates else datetime.now()

        if end_date is None:
            end_date = datetime.now()

        # Create power curve
        power_curve = PowerCurve(
            athlete_name=athlete_name,
            metric_type=metric_type,
            sport_type=sport_type,
            best_efforts=best_efforts,
            data_period_start=start_date,
            data_period_end=end_date,
            total_activities=len(activities_data),
        )

        return power_curve

    def calculate_critical_power(
        self,
        best_efforts: list[BestEffort],
        metric_type: PowerMetric,
    ) -> CriticalPower | None:
        """
        Calculate Critical Power using 2-parameter model.

        Model: P(t) = W'/t + CP
        Where:
        - P(t) = sustainable power for duration t
        - CP = Critical Power (asymptotic power)
        - W' = Anaerobic work capacity

        Args:
            best_efforts: List of best efforts (need at least 2, preferably 3-5)
            metric_type: Type of metric

        Returns:
            CriticalPower object or None if insufficient data
        """
        # Filter to appropriate durations for CP calculation (3-20 min typically)
        cp_efforts = [
            e for e in best_efforts
            if e.duration_seconds >= 180 and e.duration_seconds <= 1200
        ]

        if len(cp_efforts) < 2:
            # Try to use wider range if not enough data
            cp_efforts = [
                e for e in best_efforts
                if e.duration_seconds >= 60 and e.duration_seconds <= 3600
            ]

        if len(cp_efforts) < 2:
            return None  # Need at least 2 points

        # Prepare data for linear regression
        # Transform: P = W'/t + CP
        # Rearrange: P*t = W' + CP*t
        # Let: y = P*t (work), x = t (time)
        # Then: y = W' + CP*x (linear regression)

        times = np.array([e.duration_seconds for e in cp_efforts])
        powers = np.array([e.value for e in cp_efforts])

        # Method 1: Linear regression of work vs time
        work = powers * times  # Work = Power * Time

        # Fit: work = intercept + slope * time
        # Where: intercept = W', slope = CP
        coeffs = np.polyfit(times, work, 1)
        cp = coeffs[0]  # Slope
        w_prime = coeffs[1]  # Intercept

        # Calculate R-squared and RMSE
        predicted_work = np.polyval(coeffs, times)
        predicted_powers = predicted_work / times

        ss_res = np.sum((work - predicted_work) ** 2)
        ss_tot = np.sum((work - np.mean(work)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        rmse = np.sqrt(np.mean((powers - predicted_powers) ** 2))

        # Estimate FTP (typically ~95% of 20min power or ~CP)
        twenty_min_efforts = [e for e in cp_efforts if 1000 <= e.duration_seconds <= 1400]
        if twenty_min_efforts:
            ftp_estimate = max(e.value for e in twenty_min_efforts) * 0.95
        else:
            ftp_estimate = cp  # Use CP as estimate

        critical_power = CriticalPower(
            cp=float(cp),
            w_prime=float(w_prime),
            metric_type=metric_type,
            r_squared=float(r_squared),
            rmse=float(rmse),
            efforts_used=cp_efforts,
            calculation_date=datetime.now(),
            ftp_estimate=float(ftp_estimate),
        )

        return critical_power

    def generate_training_zones(
        self, cp_model: CriticalPower
    ) -> TrainingZones:
        """
        Generate training zones from Critical Power model.

        Args:
            cp_model: CriticalPower model

        Returns:
            TrainingZones object
        """
        return TrainingZones.from_critical_power(cp_model)

    def create_fitness_signature(
        self,
        power_curve: PowerCurve,
        cp_model: CriticalPower | None = None,
    ) -> FitnessSignature:
        """
        Create a fitness signature from power curve and CP model.

        Args:
            power_curve: PowerCurve object
            cp_model: Optional CriticalPower model

        Returns:
            FitnessSignature object
        """
        # If no CP model provided, calculate it
        if cp_model is None:
            cp_model = self.calculate_critical_power(
                power_curve.best_efforts, power_curve.metric_type
            )

        if cp_model is None:
            # Fallback values
            cp = 0.0
            w_prime = 0.0
        else:
            cp = cp_model.cp
            w_prime = cp_model.w_prime

        signature = FitnessSignature(
            signature_date=datetime.now(),
            cp=cp,
            w_prime=w_prime,
            metric_type=power_curve.metric_type,
            peak_5_sec=power_curve.peak_5_sec,
            peak_1_min=power_curve.peak_1_min,
            peak_5_min=power_curve.peak_5_min,
            peak_20_min=power_curve.peak_20_min,
            peak_60_min=power_curve.peak_60_min,
        )

        # Calculate fatigue resistance
        if power_curve.peak_5_min and power_curve.peak_60_min:
            signature.fatigue_resistance = power_curve.peak_60_min / power_curve.peak_5_min

        # Classify fitness profile
        signature.classify_profile()

        return signature

    def compare_power_curves(
        self,
        current_curve: PowerCurve,
        comparison_curve: PowerCurve,
        comparison_label: str = "previous",
    ) -> PowerCurveComparison:
        """
        Compare two power curves.

        Args:
            current_curve: Current power curve
            comparison_curve: Historical power curve to compare against
            comparison_label: Label for comparison (e.g., "vs 6 months ago")

        Returns:
            PowerCurveComparison object
        """
        comparison = PowerCurveComparison(
            metric_type=current_curve.metric_type,
            current_curve=current_curve,
            comparison_curve=comparison_curve,
            comparison_label=comparison_label,
        )

        return comparison

    def track_critical_power_history(
        self,
        cp_models: list[tuple[datetime, CriticalPower]],
        athlete_name: str,
    ) -> CriticalPowerHistory:
        """
        Track Critical Power evolution over time.

        Args:
            cp_models: List of (date, CriticalPower) tuples
            athlete_name: Athlete's name

        Returns:
            CriticalPowerHistory object
        """
        if not cp_models:
            raise ValueError("Need at least one CP measurement")

        # Sort by date
        cp_models_sorted = sorted(cp_models, key=lambda x: x[0])

        metric_type = cp_models_sorted[0][1].metric_type

        cp_measurements = [(date, cp.cp) for date, cp in cp_models_sorted]
        w_prime_measurements = [(date, cp.w_prime) for date, cp in cp_models_sorted]

        history = CriticalPowerHistory(
            athlete_name=athlete_name,
            metric_type=metric_type,
            cp_measurements=cp_measurements,
            w_prime_measurements=w_prime_measurements,
        )

        return history

    def identify_limiters(
        self, power_curve: PowerCurve, fitness_signature: FitnessSignature
    ) -> dict[str, Any]:
        """
        Identify performance limiters based on power curve analysis.

        Args:
            power_curve: PowerCurve object
            fitness_signature: FitnessSignature object

        Returns:
            Dictionary with limiter analysis
        """
        limiters = {
            "sprint_power": None,
            "anaerobic_capacity": None,
            "vo2max": None,
            "threshold": None,
            "endurance": None,
            "recommendations": [],
        }

        # Analyze sprint power (5-30s)
        if power_curve.peak_5_sec and power_curve.peak_1_min:
            sprint_ratio = power_curve.peak_5_sec / power_curve.peak_1_min
            if sprint_ratio < 1.3:  # Weak sprint
                limiters["sprint_power"] = "weak"
                limiters["recommendations"].append(
                    "Consider adding sprint intervals (10-30s max efforts) to improve neuromuscular power"
                )

        # Analyze anaerobic capacity (W')
        if fitness_signature.w_prime:
            # Typical W' ranges: 15,000-25,000 J for trained cyclists
            if fitness_signature.w_prime < 15000:
                limiters["anaerobic_capacity"] = "weak"
                limiters["recommendations"].append(
                    "Low anaerobic capacity (W'). Add 3-5min VO2max intervals to improve"
                )

        # Analyze VO2max (5min power)
        if power_curve.peak_5_min and fitness_signature.cp:
            vo2max_ratio = power_curve.peak_5_min / fitness_signature.cp
            if vo2max_ratio < 1.15:  # Low VO2max relative to threshold
                limiters["vo2max"] = "weak"
                limiters["recommendations"].append(
                    "VO2max appears limited. Add high-intensity intervals (3-8min at 105-120% FTP)"
                )

        # Analyze threshold (CP/FTP)
        # Threshold is represented by CP itself

        # Analyze endurance (fatigue resistance)
        if fitness_signature.fatigue_resistance:
            if fitness_signature.fatigue_resistance < 0.75:  # Poor endurance
                limiters["endurance"] = "weak"
                limiters["recommendations"].append(
                    "Poor fatigue resistance. Build aerobic base with longer, steady rides (2-4+ hours)"
                )

        # Overall recommendations based on profile
        if fitness_signature.fitness_profile == FitnessProfile.SPRINTER:
            limiters["recommendations"].append(
                "Sprinter profile: Strong in short efforts. Consider building endurance for longer events"
            )
        elif fitness_signature.fitness_profile == FitnessProfile.TIME_TRIALIST:
            limiters["recommendations"].append(
                "Time trialist profile: Strong endurance. Consider adding high-intensity work for races with surges"
            )

        return limiters

    def predict_race_performance(
        self,
        cp_model: CriticalPower,
        race_duration_seconds: int,
        w_prime_usage_pct: float = 100.0,
    ) -> dict[str, float]:
        """
        Predict sustainable power for a race duration.

        Args:
            cp_model: CriticalPower model
            race_duration_seconds: Race duration in seconds
            w_prime_usage_pct: Percentage of W' to use (default 100%)

        Returns:
            Dictionary with predicted power, speed, etc.
        """
        # Adjust W' based on usage percentage
        effective_w_prime = cp_model.w_prime * (w_prime_usage_pct / 100.0)

        # Predicted average power: P = (W'/t) + CP
        predicted_power = (effective_w_prime / race_duration_seconds) + cp_model.cp

        # Calculate work done
        total_work = predicted_power * race_duration_seconds

        # Power distribution
        power_from_cp = cp_model.cp * race_duration_seconds
        power_from_w_prime = effective_w_prime

        return {
            "predicted_average_power": predicted_power,
            "race_duration_seconds": race_duration_seconds,
            "race_duration_minutes": race_duration_seconds / 60,
            "total_work_kj": total_work / 1000,
            "power_from_aerobic_kj": power_from_cp / 1000,
            "power_from_anaerobic_kj": power_from_w_prime / 1000,
            "anaerobic_contribution_pct": (power_from_w_prime / total_work) * 100,
            "w_prime_usage_pct": w_prime_usage_pct,
        }
