"""
Training Readiness Calculator

Calculates daily training readiness from multiple physiological and training signals.
Provides actionable recommendations for workout modifications.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SignalStatus(Enum):
    """Status indicator for individual readiness signals."""

    OPTIMAL = "optimal"  # Green light
    ACCEPTABLE = "acceptable"  # Yellow - monitor
    CONCERN = "concern"  # Red - caution needed


class ReadinessRecommendation(Enum):
    """Overall training recommendation based on readiness score."""

    REST = "rest"  # Complete rest or very light activity
    EASY = "easy"  # Easy recovery workouts only
    MODERATE = "moderate"  # Moderate training, avoid high intensity
    NORMAL = "normal"  # Proceed with planned training
    PEAK = "peak"  # Excellent readiness, can push hard


@dataclass
class Signal:
    """Individual readiness signal with status and details."""

    name: str
    status: SignalStatus
    value: float | int | str | None
    baseline: float | int | str | None
    deviation: float | None
    message: str
    weight: float  # Contribution weight to overall score


@dataclass
class ReadinessScore:
    """Complete readiness assessment with score, signals, and recommendations."""

    score: int  # 0-100
    recommendation: ReadinessRecommendation
    signals: list[Signal]
    modifications: list[str]
    reasoning: str
    confidence: float  # 0.0-1.0, based on data completeness


class ReadinessCalculator:
    """
    Calculate training readiness from multiple physiological signals.

    Signals analyzed:
    - HRV (Heart Rate Variability) status
    - Sleep quality and duration
    - Resting heart rate deviation
    - Training load (ACWR)
    - Stress levels
    - Recent workout quality
    """

    # Scoring weights for each signal (must sum to 1.0)
    WEIGHTS = {
        "hrv": 0.25,
        "sleep": 0.25,
        "training_load": 0.20,
        "resting_hr": 0.15,
        "stress": 0.10,
        "workout_quality": 0.05,
    }

    # Thresholds for signal assessment
    THRESHOLDS = {
        "sleep": {
            "optimal": 7.5,  # hours
            "acceptable": 6.5,
            "concern": 5.5,
        },
        "acwr": {
            "optimal_low": 0.8,
            "optimal_high": 1.3,
            "concern_high": 1.5,
        },
        "rhr_deviation": {
            "optimal": 3,  # bpm above baseline
            "acceptable": 5,
            "concern": 8,
        },
        "stress": {
            "optimal": 30,
            "acceptable": 50,
            "concern": 70,
        },
    }

    def calculate_readiness(
        self,
        hrv_status: str | None = None,
        hrv_weekly_avg: float | None = None,
        hrv_last_night: float | None = None,
        hrv_baseline_balanced_low: float | None = None,
        hrv_baseline_balanced_upper: float | None = None,
        sleep_hours: float | None = None,
        sleep_quality_score: float | None = None,
        resting_hr: int | None = None,
        resting_hr_baseline: int | None = None,
        acwr: float | None = None,
        acute_load: float | None = None,
        chronic_load: float | None = None,
        stress_avg: int | None = None,
        stress_max: int | None = None,
        recent_training_quality: str | None = None,
    ) -> ReadinessScore:
        """
        Calculate comprehensive training readiness score.

        Args:
            hrv_status: HRV status from Garmin (balanced/unbalanced/low/high)
            hrv_weekly_avg: Weekly average HRV
            hrv_last_night: Last night's HRV reading
            hrv_baseline_balanced_low: Lower bound of balanced HRV range
            hrv_baseline_balanced_upper: Upper bound of balanced HRV range
            sleep_hours: Hours of sleep last night
            sleep_quality_score: Garmin sleep quality score (0-100)
            resting_hr: Current resting heart rate
            resting_hr_baseline: Baseline/average resting heart rate
            acwr: Acute:Chronic Workload Ratio
            acute_load: Current acute training load
            chronic_load: Current chronic training load
            stress_avg: Average daily stress level
            stress_max: Maximum daily stress level
            recent_training_quality: Recent workout quality assessment

        Returns:
            ReadinessScore with overall score, signals, and recommendations
        """
        signals = []
        data_points_available = 0
        total_data_points = 6

        # 1. HRV Signal
        hrv_signal = self._assess_hrv(
            hrv_status,
            hrv_weekly_avg,
            hrv_last_night,
            hrv_baseline_balanced_low,
            hrv_baseline_balanced_upper,
        )
        if hrv_signal:
            signals.append(hrv_signal)
            data_points_available += 1

        # 2. Sleep Signal
        sleep_signal = self._assess_sleep(sleep_hours, sleep_quality_score)
        if sleep_signal:
            signals.append(sleep_signal)
            data_points_available += 1

        # 3. Training Load Signal
        load_signal = self._assess_training_load(acwr, acute_load, chronic_load)
        if load_signal:
            signals.append(load_signal)
            data_points_available += 1

        # 4. Resting HR Signal
        rhr_signal = self._assess_resting_hr(resting_hr, resting_hr_baseline)
        if rhr_signal:
            signals.append(rhr_signal)
            data_points_available += 1

        # 5. Stress Signal
        stress_signal = self._assess_stress(stress_avg, stress_max)
        if stress_signal:
            signals.append(stress_signal)
            data_points_available += 1

        # 6. Workout Quality Signal
        quality_signal = self._assess_workout_quality(recent_training_quality)
        if quality_signal:
            signals.append(quality_signal)
            data_points_available += 1

        # Calculate weighted score (already on 0-100 scale from _signal_to_score)
        total_score = sum(self._signal_to_score(signal) * signal.weight for signal in signals)

        # Normalize based on total weight
        total_weight = sum(signal.weight for signal in signals)
        if total_weight > 0:
            normalized_score = int(total_score / total_weight)
        else:
            normalized_score = 50  # Default if no data

        # Determine recommendation
        recommendation = self._score_to_recommendation(normalized_score)

        # Generate modifications
        modifications = self._generate_modifications(normalized_score, signals)

        # Generate reasoning
        reasoning = self._generate_reasoning(normalized_score, signals)

        # Calculate confidence based on data completeness
        confidence = data_points_available / total_data_points

        logger.info(
            f"Calculated readiness: score={normalized_score}, "
            f"recommendation={recommendation.value}, confidence={confidence:.2f}"
        )

        return ReadinessScore(
            score=normalized_score,
            recommendation=recommendation,
            signals=signals,
            modifications=modifications,
            reasoning=reasoning,
            confidence=confidence,
        )

    def _assess_hrv(
        self,
        status: str | None,
        weekly_avg: float | None,
        last_night: float | None,
        baseline_low: float | None,
        baseline_upper: float | None,
    ) -> Signal | None:
        """Assess HRV signal status."""
        if not any([status, weekly_avg, last_night]):
            return None

        # Parse Garmin HRV status
        if status:
            status_lower = status.lower()
            if status_lower in ["balanced", "normal"]:
                signal_status = SignalStatus.OPTIMAL
                message = "HRV balanced (within normal range)"
            elif status_lower in ["unbalanced", "low"]:
                signal_status = SignalStatus.CONCERN
                message = "HRV unbalanced (below baseline - recovery needed)"
            elif status_lower == "high":
                signal_status = SignalStatus.ACCEPTABLE
                message = "HRV elevated (possible over-recovery or measurement error)"
            else:
                signal_status = SignalStatus.ACCEPTABLE
                message = f"HRV status: {status}"
        elif last_night and baseline_low and baseline_upper:
            # Calculate based on baseline ranges
            if baseline_low <= last_night <= baseline_upper:
                signal_status = SignalStatus.OPTIMAL
                message = f"HRV in balanced range ({last_night:.0f} ms)"
            elif last_night < baseline_low:
                deviation_pct = ((baseline_low - last_night) / baseline_low) * 100
                if deviation_pct > 15:
                    signal_status = SignalStatus.CONCERN
                    message = f"HRV {deviation_pct:.0f}% below baseline ({last_night:.0f} ms)"
                else:
                    signal_status = SignalStatus.ACCEPTABLE
                    message = f"HRV slightly below baseline ({last_night:.0f} ms)"
            else:
                signal_status = SignalStatus.ACCEPTABLE
                message = f"HRV above normal range ({last_night:.0f} ms)"
        else:
            signal_status = SignalStatus.ACCEPTABLE
            message = f"HRV: {last_night or weekly_avg:.0f} ms"

        return Signal(
            name="HRV",
            status=signal_status,
            value=last_night or weekly_avg,
            baseline=(baseline_low + baseline_upper) / 2 if baseline_low and baseline_upper else None,
            deviation=None,
            message=message,
            weight=self.WEIGHTS["hrv"],
        )

    def _assess_sleep(
        self, sleep_hours: float | None, sleep_quality: float | None
    ) -> Signal | None:
        """Assess sleep signal status."""
        if not sleep_hours and not sleep_quality:
            return None

        if sleep_hours:
            if sleep_hours >= self.THRESHOLDS["sleep"]["optimal"]:
                signal_status = SignalStatus.OPTIMAL
                message = f"Excellent sleep duration ({sleep_hours:.1f}h)"
            elif sleep_hours >= self.THRESHOLDS["sleep"]["acceptable"]:
                signal_status = SignalStatus.ACCEPTABLE
                message = f"Adequate sleep ({sleep_hours:.1f}h, target 7.5-8.5h)"
            elif sleep_hours >= self.THRESHOLDS["sleep"]["concern"]:
                signal_status = SignalStatus.ACCEPTABLE
                message = f"Below target sleep ({sleep_hours:.1f}h, increased recovery needed)"
            else:
                signal_status = SignalStatus.CONCERN
                message = f"Insufficient sleep ({sleep_hours:.1f}h, <6h is high risk)"

            # Adjust based on quality score if available
            if sleep_quality:
                if sleep_quality < 60 and signal_status == SignalStatus.OPTIMAL:
                    signal_status = SignalStatus.ACCEPTABLE
                    message += f" but quality low ({sleep_quality:.0f}/100)"
                elif sleep_quality >= 80:
                    message += f" with excellent quality ({sleep_quality:.0f}/100)"
        else:
            # Quality only
            if sleep_quality >= 80:
                signal_status = SignalStatus.OPTIMAL
                message = f"Excellent sleep quality ({sleep_quality:.0f}/100)"
            elif sleep_quality >= 60:
                signal_status = SignalStatus.ACCEPTABLE
                message = f"Adequate sleep quality ({sleep_quality:.0f}/100)"
            else:
                signal_status = SignalStatus.CONCERN
                message = f"Poor sleep quality ({sleep_quality:.0f}/100)"

        return Signal(
            name="Sleep",
            status=signal_status,
            value=sleep_hours,
            baseline=8.0,
            deviation=(sleep_hours - 8.0) if sleep_hours else None,
            message=message,
            weight=self.WEIGHTS["sleep"],
        )

    def _assess_training_load(
        self, acwr: float | None, acute_load: float | None, chronic_load: float | None
    ) -> Signal | None:
        """Assess training load signal status."""
        if not acwr:
            return None

        optimal_low = self.THRESHOLDS["acwr"]["optimal_low"]
        optimal_high = self.THRESHOLDS["acwr"]["optimal_high"]
        concern_high = self.THRESHOLDS["acwr"]["concern_high"]

        if optimal_low <= acwr <= optimal_high:
            signal_status = SignalStatus.OPTIMAL
            message = f"Training load optimal (ACWR: {acwr:.2f}, safe zone)"
        elif acwr < optimal_low:
            signal_status = SignalStatus.ACCEPTABLE
            message = f"Training load low (ACWR: {acwr:.2f}, undertraining risk)"
        elif acwr <= concern_high:
            signal_status = SignalStatus.ACCEPTABLE
            message = f"Training load elevated (ACWR: {acwr:.2f}, monitor fatigue)"
        else:
            signal_status = SignalStatus.CONCERN
            message = f"Training load HIGH (ACWR: {acwr:.2f}, injury risk >2x baseline)"

        # Add context if load values available
        if acute_load and chronic_load:
            message += f" | Acute: {acute_load:.0f}, Chronic: {chronic_load:.0f}"

        return Signal(
            name="Training Load",
            status=signal_status,
            value=acwr,
            baseline=1.0,
            deviation=acwr - 1.0,
            message=message,
            weight=self.WEIGHTS["training_load"],
        )

    def _assess_resting_hr(
        self, resting_hr: int | None, baseline: int | None
    ) -> Signal | None:
        """Assess resting heart rate signal status."""
        if not resting_hr or not baseline:
            return None

        deviation = resting_hr - baseline

        if abs(deviation) <= self.THRESHOLDS["rhr_deviation"]["optimal"]:
            signal_status = SignalStatus.OPTIMAL
            message = f"Resting HR normal ({resting_hr} bpm, baseline: {baseline} bpm)"
        elif abs(deviation) <= self.THRESHOLDS["rhr_deviation"]["acceptable"]:
            if deviation > 0:
                signal_status = SignalStatus.ACCEPTABLE
                message = f"Resting HR elevated (+{deviation} bpm, {resting_hr} vs {baseline} bpm)"
            else:
                signal_status = SignalStatus.OPTIMAL
                message = f"Resting HR excellent ({deviation} bpm, {resting_hr} vs {baseline} bpm)"
        else:
            if deviation > 0:
                signal_status = SignalStatus.CONCERN
                message = f"Resting HR HIGH (+{deviation} bpm above baseline, possible overtraining/illness)"
            else:
                signal_status = SignalStatus.OPTIMAL
                message = f"Resting HR very low ({deviation} bpm, excellent recovery)"

        return Signal(
            name="Resting HR",
            status=signal_status,
            value=resting_hr,
            baseline=baseline,
            deviation=float(deviation),
            message=message,
            weight=self.WEIGHTS["resting_hr"],
        )

    def _assess_stress(self, stress_avg: int | None, stress_max: int | None) -> Signal | None:
        """Assess stress level signal status."""
        if not stress_avg and not stress_max:
            return None

        stress_value = stress_avg or stress_max

        if stress_value <= self.THRESHOLDS["stress"]["optimal"]:
            signal_status = SignalStatus.OPTIMAL
            message = f"Stress levels low (avg: {stress_value})"
        elif stress_value <= self.THRESHOLDS["stress"]["acceptable"]:
            signal_status = SignalStatus.ACCEPTABLE
            message = f"Stress levels moderate (avg: {stress_value}, monitor)"
        elif stress_value <= self.THRESHOLDS["stress"]["concern"]:
            signal_status = SignalStatus.ACCEPTABLE
            message = f"Stress levels elevated (avg: {stress_value}, recovery priority)"
        else:
            signal_status = SignalStatus.CONCERN
            message = f"Stress levels HIGH (avg: {stress_value}, significant recovery needed)"

        if stress_max and stress_max > 80:
            message += f" | Peak: {stress_max}"

        return Signal(
            name="Stress",
            status=signal_status,
            value=stress_value,
            baseline=30,
            deviation=float(stress_value - 30),
            message=message,
            weight=self.WEIGHTS["stress"],
        )

    def _assess_workout_quality(self, quality: str | None) -> Signal | None:
        """Assess recent workout quality signal status."""
        if not quality:
            return None

        quality_lower = quality.lower()

        if "excellent" in quality_lower or "great" in quality_lower:
            signal_status = SignalStatus.OPTIMAL
            message = "Recent workouts: Excellent quality"
        elif "good" in quality_lower or "solid" in quality_lower:
            signal_status = SignalStatus.OPTIMAL
            message = "Recent workouts: Good quality"
        elif "moderate" in quality_lower or "average" in quality_lower:
            signal_status = SignalStatus.ACCEPTABLE
            message = "Recent workouts: Moderate quality"
        elif "poor" in quality_lower or "struggled" in quality_lower:
            signal_status = SignalStatus.CONCERN
            message = "Recent workouts: Poor quality (fatigue indicator)"
        else:
            signal_status = SignalStatus.ACCEPTABLE
            message = f"Recent workouts: {quality}"

        return Signal(
            name="Workout Quality",
            status=signal_status,
            value=quality,
            baseline=None,
            deviation=None,
            message=message,
            weight=self.WEIGHTS["workout_quality"],
        )

    def _signal_to_score(self, signal: Signal) -> float:
        """Convert signal status to numeric score (0-100)."""
        if signal.status == SignalStatus.OPTIMAL:
            return 100.0
        elif signal.status == SignalStatus.ACCEPTABLE:
            return 65.0
        else:  # CONCERN
            return 35.0

    def _score_to_recommendation(self, score: int) -> ReadinessRecommendation:
        """Convert numeric score to training recommendation."""
        if score >= 85:
            return ReadinessRecommendation.PEAK
        elif score >= 70:
            return ReadinessRecommendation.NORMAL
        elif score >= 55:
            return ReadinessRecommendation.MODERATE
        elif score >= 40:
            return ReadinessRecommendation.EASY
        else:
            return ReadinessRecommendation.REST

    def _generate_modifications(self, score: int, signals: list[Signal]) -> list[str]:
        """Generate workout modification recommendations."""
        modifications = []

        # Get concern signals
        concerns = [s for s in signals if s.status == SignalStatus.CONCERN]
        acceptable = [s for s in signals if s.status == SignalStatus.ACCEPTABLE]

        if score < 40:
            modifications.append("🛑 REST DAY RECOMMENDED: Complete rest or very light activity only")
            modifications.append("Consider: Easy walk, gentle yoga, or complete rest")
        elif score < 55:
            modifications.append("📉 EASY DAY: Replace planned workout with recovery session")
            modifications.append("Zone 1-2 only, keep HR below aerobic threshold")
            if any("sleep" in s.name.lower() for s in concerns):
                modifications.append("Prioritize early bedtime tonight (target 8+ hours)")
        elif score < 70:
            modifications.append("⚖️ MODERATE TRAINING: Reduce intensity of planned workout")
            modifications.append("Cut interval volume by 25-30% or reduce intensity by 5-10%")
            modifications.append("Extend recovery periods between intervals")
        elif score < 85:
            modifications.append("✅ PROCEED WITH PLAN: Normal training can continue")
            modifications.append("Monitor how you feel during warm-up, adjust if needed")
        else:
            modifications.append("🚀 PEAK READINESS: Excellent day for key workout or race")
            modifications.append("High-quality session opportunity, full execution possible")

        # Add specific signal-based modifications
        for signal in concerns:
            if "hrv" in signal.name.lower():
                modifications.append("🔴 HRV concern: Prioritize recovery, avoid high intensity")
            elif "sleep" in signal.name.lower():
                modifications.append("🔴 Sleep deficit: Early bedtime + optional afternoon nap")
            elif "load" in signal.name.lower() or "acwr" in signal.message.lower():
                modifications.append("🔴 Training load spike: Reduce volume 25-40% this week")
            elif "hr" in signal.name.lower() and "resting" in signal.name.lower():
                modifications.append("🔴 Elevated RHR: Check for illness/overtraining, consider rest")
            elif "stress" in signal.name.lower():
                modifications.append("🔴 High stress: Add relaxation practices (meditation, breathing)")

        for signal in acceptable:
            if "sleep" in signal.name.lower() and score < 70:
                modifications.append("🟡 Sleep: Target 8+ hours tonight for recovery")
            elif "load" in signal.name.lower() and score < 70:
                modifications.append("🟡 Training load: Monitor weekly volume, avoid spikes")

        return modifications

    def _generate_reasoning(self, score: int, signals: list[Signal]) -> str:
        """Generate natural language reasoning for the readiness score."""
        optimal_count = sum(1 for s in signals if s.status == SignalStatus.OPTIMAL)
        acceptable_count = sum(1 for s in signals if s.status == SignalStatus.ACCEPTABLE)
        concern_count = sum(1 for s in signals if s.status == SignalStatus.CONCERN)

        reasoning_parts = [f"Readiness score of {score}/100 based on {len(signals)} signals:"]

        if optimal_count > 0:
            optimal_names = [s.name for s in signals if s.status == SignalStatus.OPTIMAL]
            reasoning_parts.append(f"✅ Strong indicators: {', '.join(optimal_names)}")

        if acceptable_count > 0:
            acceptable_names = [s.name for s in signals if s.status == SignalStatus.ACCEPTABLE]
            reasoning_parts.append(f"⚠️  Monitor: {', '.join(acceptable_names)}")

        if concern_count > 0:
            concern_names = [s.name for s in signals if s.status == SignalStatus.CONCERN]
            reasoning_parts.append(f"🔴 Concerns: {', '.join(concern_names)}")

        # Add recommendation context
        if score >= 85:
            reasoning_parts.append(
                "All systems show excellent readiness. This is an ideal day for challenging workouts."
            )
        elif score >= 70:
            reasoning_parts.append(
                "Good overall readiness. Proceed with planned training while monitoring response."
            )
        elif score >= 55:
            reasoning_parts.append(
                "Moderate readiness. Consider reducing training intensity to avoid overreaching."
            )
        elif score >= 40:
            reasoning_parts.append(
                "Low readiness detected. Easy recovery training only to facilitate adaptation."
            )
        else:
            reasoning_parts.append(
                "Poor readiness indicates need for rest. Pushing through may increase injury/illness risk."
            )

        return " ".join(reasoning_parts)

    def format_readiness_report(self, readiness: ReadinessScore) -> str:
        """Format readiness score as human-readable text report."""
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append(f"🎯 TRAINING READINESS ASSESSMENT")
        lines.append("=" * 70)
        lines.append("")

        # Score and recommendation
        lines.append(f"Overall Score: {readiness.score}/100 ({readiness.recommendation.value.upper()})")
        lines.append(f"Confidence: {readiness.confidence:.0%} (based on available data)")
        lines.append("")

        # Signals
        lines.append("PHYSIOLOGICAL SIGNALS:")
        lines.append("-" * 70)
        for signal in readiness.signals:
            status_emoji = {
                SignalStatus.OPTIMAL: "✅",
                SignalStatus.ACCEPTABLE: "⚠️ ",
                SignalStatus.CONCERN: "🔴",
            }[signal.status]
            lines.append(f"{status_emoji} {signal.message}")
        lines.append("")

        # Reasoning
        lines.append("ANALYSIS:")
        lines.append("-" * 70)
        lines.append(readiness.reasoning)
        lines.append("")

        # Modifications
        lines.append("TRAINING RECOMMENDATIONS:")
        lines.append("-" * 70)
        for mod in readiness.modifications:
            lines.append(mod)
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)
