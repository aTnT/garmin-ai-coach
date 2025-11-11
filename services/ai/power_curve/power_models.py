"""
Power Curve and Critical Power Models

Data structures for power/pace curve analysis and critical power calculations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DurationType(str, Enum):
    """Standard durations for power curve analysis."""

    FIVE_SEC = "5s"
    TEN_SEC = "10s"
    THIRTY_SEC = "30s"
    ONE_MIN = "1min"
    TWO_MIN = "2min"
    FIVE_MIN = "5min"
    TEN_MIN = "10min"
    TWENTY_MIN = "20min"
    THIRTY_MIN = "30min"
    SIXTY_MIN = "60min"
    NINETY_MIN = "90min"
    TWO_HOUR = "2hr"
    THREE_HOUR = "3hr"
    FOUR_HOUR = "4hr"
    FIVE_HOUR = "5hr"


class PowerMetric(str, Enum):
    """Type of power/pace metric."""

    POWER_WATTS = "watts"  # Cycling power
    PACE_MIN_PER_KM = "min/km"  # Running pace
    PACE_MIN_PER_MILE = "min/mi"  # Running pace (imperial)
    SPEED_KPH = "km/h"  # Speed
    SPEED_MPH = "mph"  # Speed (imperial)


class FitnessProfile(str, Enum):
    """Athlete's fitness profile based on power curve shape."""

    SPRINTER = "sprinter"  # Strong in short durations (<1min)
    PURSUER = "pursuer"  # Strong in mid durations (1-5min)
    TIME_TRIALIST = "time_trialist"  # Strong in long durations (20-60min)
    ALL_ROUNDER = "all_rounder"  # Balanced across durations
    ULTRA_ENDURANCE = "ultra_endurance"  # Strong in very long durations (>2hr)


@dataclass
class BestEffort:
    """Represents a best effort for a specific duration."""

    duration_seconds: int
    duration_label: str  # Human-readable (e.g., "5 min")
    value: float  # Power in watts or pace in min/km
    metric_type: PowerMetric
    activity_id: str | None = None
    activity_date: datetime | None = None
    activity_name: str | None = None
    activity_type: str | None = None  # "Run", "Ride", etc.
    normalized: bool = False  # Whether this is normalized power/pace
    average: bool = True  # True for average, False for peak

    def __post_init__(self):
        """Validate best effort data."""
        if self.duration_seconds <= 0:
            raise ValueError("Duration must be positive")
        if self.value <= 0:
            raise ValueError("Value must be positive")


@dataclass
class PowerCurve:
    """Complete power curve across all durations."""

    athlete_name: str
    metric_type: PowerMetric
    sport_type: str  # "cycling", "running", "swimming"
    best_efforts: list[BestEffort]
    data_period_start: datetime
    data_period_end: datetime
    total_activities: int

    # Derived metrics
    peak_5_sec: float | None = None
    peak_1_min: float | None = None
    peak_5_min: float | None = None
    peak_20_min: float | None = None
    peak_60_min: float | None = None

    def __post_init__(self):
        """Extract key power values."""
        duration_map = {
            5: "peak_5_sec",
            60: "peak_1_min",
            300: "peak_5_min",
            1200: "peak_20_min",
            3600: "peak_60_min",
        }

        for effort in self.best_efforts:
            if effort.duration_seconds in duration_map:
                attr_name = duration_map[effort.duration_seconds]
                setattr(self, attr_name, effort.value)


@dataclass
class CriticalPower:
    """
    Critical Power model (2-parameter).

    CP = Critical Power (watts) - sustainable power for ~30-60 minutes
    W_prime = Anaerobic Work Capacity (joules) - work above CP before exhaustion

    Model: P(t) = W'/t + CP
    Where P(t) is the power sustainable for time t
    """

    cp: float  # Critical Power in watts (or critical pace)
    w_prime: float  # Anaerobic capacity in joules (or distance for pace)
    metric_type: PowerMetric

    # Model fit quality
    r_squared: float  # Goodness of fit (0-1)
    rmse: float  # Root mean squared error

    # Source data
    efforts_used: list[BestEffort]  # Efforts used to calculate CP
    calculation_date: datetime

    # Interpretations
    ftp_estimate: float | None = None  # FTP ≈ 95% of 20min or ~CP
    threshold_heart_rate: int | None = None

    def predict_power(self, duration_seconds: int) -> float:
        """
        Predict sustainable power for a given duration.

        Args:
            duration_seconds: Duration in seconds

        Returns:
            Predicted power/pace
        """
        if duration_seconds <= 0:
            raise ValueError("Duration must be positive")

        # P(t) = W'/t + CP
        return (self.w_prime / duration_seconds) + self.cp

    def time_to_exhaustion(self, power: float) -> float:
        """
        Predict time to exhaustion at a given power.

        Args:
            power: Power level (watts or pace)

        Returns:
            Time in seconds until exhaustion
        """
        if power <= self.cp:
            return float('inf')  # Below CP = theoretically infinite

        # t = W' / (P - CP)
        return self.w_prime / (power - self.cp)

    def w_prime_balance(self, power: float, duration_seconds: int) -> float:
        """
        Calculate remaining W' after effort at given power.

        Args:
            power: Power level (watts or pace)
            duration_seconds: Duration of effort

        Returns:
            Remaining W' in joules
        """
        if power <= self.cp:
            return self.w_prime  # No depletion below CP

        # W' expended = (P - CP) * t
        expended = (power - self.cp) * duration_seconds
        return max(0, self.w_prime - expended)


@dataclass
class TrainingZones:
    """Training zones based on Critical Power model."""

    metric_type: PowerMetric
    cp: float

    # Zone boundaries (as % of CP or absolute values)
    recovery_max: float  # Z1: <55% CP
    endurance_max: float  # Z2: 55-75% CP
    tempo_max: float  # Z3: 75-90% CP
    threshold_max: float  # Z4: 90-105% CP
    vo2max_max: float  # Z5: 105-120% CP
    anaerobic_min: float  # Z6: >120% CP

    # Labels and descriptions
    zone_names: list[str] = field(default_factory=lambda: [
        "Recovery", "Endurance", "Tempo", "Threshold", "VO2max", "Anaerobic"
    ])

    @classmethod
    def from_critical_power(cls, cp_model: CriticalPower) -> "TrainingZones":
        """
        Create training zones from Critical Power model.

        Args:
            cp_model: CriticalPower model

        Returns:
            TrainingZones object
        """
        cp = cp_model.cp

        return cls(
            metric_type=cp_model.metric_type,
            cp=cp,
            recovery_max=cp * 0.55,
            endurance_max=cp * 0.75,
            tempo_max=cp * 0.90,
            threshold_max=cp * 1.05,
            vo2max_max=cp * 1.20,
            anaerobic_min=cp * 1.20,
        )

    def get_zone(self, power: float) -> tuple[int, str]:
        """
        Determine training zone for a given power.

        Args:
            power: Power level

        Returns:
            Tuple of (zone_number, zone_name)
        """
        if power <= self.recovery_max:
            return (1, "Recovery")
        elif power <= self.endurance_max:
            return (2, "Endurance")
        elif power <= self.tempo_max:
            return (3, "Tempo")
        elif power <= self.threshold_max:
            return (4, "Threshold")
        elif power <= self.vo2max_max:
            return (5, "VO2max")
        else:
            return (6, "Anaerobic")


@dataclass
class FitnessSignature:
    """
    Athlete's fitness signature at a point in time.

    Includes CP, W', and power curve characteristics.
    """

    signature_date: datetime
    cp: float
    w_prime: float
    metric_type: PowerMetric

    # Key power values
    peak_5_sec: float | None = None
    peak_1_min: float | None = None
    peak_5_min: float | None = None
    peak_20_min: float | None = None
    peak_60_min: float | None = None

    # Derived metrics
    anaerobic_capacity_score: float | None = None  # W' relative to body weight
    fatigue_resistance: float | None = None  # How well power holds (60min / 5min)

    # Profile classification
    fitness_profile: FitnessProfile | None = None
    profile_scores: dict[FitnessProfile, float] = field(default_factory=dict)

    def classify_profile(self) -> FitnessProfile:
        """
        Classify athlete's fitness profile based on power curve shape.

        Returns:
            FitnessProfile enum
        """
        if not all([self.peak_5_sec, self.peak_1_min, self.peak_5_min,
                    self.peak_20_min, self.peak_60_min]):
            return FitnessProfile.ALL_ROUNDER  # Default if insufficient data

        # Calculate ratios
        sprint_power = self.peak_5_sec / self.peak_60_min  # Sprint relative to endurance
        pursuit_power = self.peak_5_min / self.peak_60_min  # Mid relative to endurance
        endurance_power = self.peak_60_min / self.peak_5_min  # Endurance relative to mid

        # Score each profile
        scores = {
            FitnessProfile.SPRINTER: sprint_power * 0.4,
            FitnessProfile.PURSUER: pursuit_power * 0.4,
            FitnessProfile.TIME_TRIALIST: endurance_power * 0.4,
        }

        # Determine dominant profile
        max_score = max(scores.values())
        if max_score < 0.3:  # No clear dominance
            profile = FitnessProfile.ALL_ROUNDER
        else:
            profile = max(scores, key=scores.get)

        self.fitness_profile = profile
        self.profile_scores = scores

        return profile


@dataclass
class PowerCurveComparison:
    """Comparison between two power curves (e.g., current vs historical)."""

    metric_type: PowerMetric
    current_curve: PowerCurve
    comparison_curve: PowerCurve
    comparison_label: str  # e.g., "vs 6 months ago", "vs last year"

    # Changes by duration
    duration_changes: dict[int, float] = field(default_factory=dict)  # duration_sec -> % change

    # Overall assessment
    overall_change_percent: float | None = None
    improving_durations: list[str] = field(default_factory=list)
    declining_durations: list[str] = field(default_factory=list)
    stable_durations: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate changes between curves."""
        # Match efforts by duration
        current_efforts = {e.duration_seconds: e.value for e in self.current_curve.best_efforts}
        comparison_efforts = {e.duration_seconds: e.value for e in self.comparison_curve.best_efforts}

        # Calculate changes
        changes = []
        for duration, current_value in current_efforts.items():
            if duration in comparison_efforts:
                comparison_value = comparison_efforts[duration]

                # For power: higher is better
                # For pace: lower is better (need to invert)
                if self.metric_type in [PowerMetric.PACE_MIN_PER_KM, PowerMetric.PACE_MIN_PER_MILE]:
                    # Pace: improvement = decrease
                    change_pct = ((comparison_value - current_value) / comparison_value) * 100
                else:
                    # Power: improvement = increase
                    change_pct = ((current_value - comparison_value) / comparison_value) * 100

                self.duration_changes[duration] = change_pct
                changes.append(change_pct)

                # Classify change
                duration_label = self._duration_to_label(duration)
                if change_pct > 2:
                    self.improving_durations.append(duration_label)
                elif change_pct < -2:
                    self.declining_durations.append(duration_label)
                else:
                    self.stable_durations.append(duration_label)

        # Overall change (average across all durations)
        if changes:
            self.overall_change_percent = sum(changes) / len(changes)

    def _duration_to_label(self, duration_seconds: int) -> str:
        """Convert duration in seconds to human-readable label."""
        if duration_seconds < 60:
            return f"{duration_seconds}s"
        elif duration_seconds < 3600:
            minutes = duration_seconds // 60
            return f"{minutes}min"
        else:
            hours = duration_seconds // 3600
            return f"{hours}hr"


@dataclass
class CriticalPowerHistory:
    """Historical tracking of Critical Power over time."""

    athlete_name: str
    metric_type: PowerMetric
    cp_measurements: list[tuple[datetime, float]]  # (date, CP value)
    w_prime_measurements: list[tuple[datetime, float]]  # (date, W' value)

    # Trends
    cp_trend_direction: str | None = None  # "improving", "stable", "declining"
    cp_change_percent: float | None = None
    w_prime_trend_direction: str | None = None
    w_prime_change_percent: float | None = None

    def __post_init__(self):
        """Calculate trends."""
        if len(self.cp_measurements) >= 2:
            first_cp = self.cp_measurements[0][1]
            last_cp = self.cp_measurements[-1][1]
            self.cp_change_percent = ((last_cp - first_cp) / first_cp) * 100

            if self.cp_change_percent > 2:
                self.cp_trend_direction = "improving"
            elif self.cp_change_percent < -2:
                self.cp_trend_direction = "declining"
            else:
                self.cp_trend_direction = "stable"

        if len(self.w_prime_measurements) >= 2:
            first_w = self.w_prime_measurements[0][1]
            last_w = self.w_prime_measurements[-1][1]
            self.w_prime_change_percent = ((last_w - first_w) / first_w) * 100

            if self.w_prime_change_percent > 2:
                self.w_prime_trend_direction = "improving"
            elif self.w_prime_change_percent < -2:
                self.w_prime_trend_direction = "declining"
            else:
                self.w_prime_trend_direction = "stable"
