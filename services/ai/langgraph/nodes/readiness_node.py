"""
Readiness Assessment Node

LangGraph node that calculates training readiness from available physiological data.
"""

import logging
from typing import Any

from services.ai.readiness.readiness_calculator import ReadinessCalculator

from ..state.training_analysis_state import TrainingAnalysisState

logger = logging.getLogger(__name__)


def readiness_assessment_node(state: TrainingAnalysisState) -> dict[str, Any]:
    """
    Calculate training readiness from physiological signals.

    Extracts relevant metrics from Garmin data and computes readiness score
    with actionable recommendations.

    Args:
        state: Current workflow state with Garmin data

    Returns:
        Dictionary with readiness_result and readiness_score for state update
    """
    logger.info("=== Readiness Assessment Node ===")

    try:
        garmin_data = state.get("garmin_data", {})

        # Extract physiological markers
        physio_markers = garmin_data.get("physiological_markers", {})
        hrv_data = physio_markers.get("hrv", {})

        # Extract training status
        training_status = garmin_data.get("training_status", {})
        acute_training_load = training_status.get("acute_training_load", {})

        # Extract recent recovery data (most recent entry)
        recovery_indicators = garmin_data.get("recovery_indicators", [])
        latest_recovery = recovery_indicators[-1] if recovery_indicators else {}
        sleep_data = latest_recovery.get("sleep", {})
        stress_data = latest_recovery.get("stress", {})

        # Extract daily stats (current day)
        daily_stats = garmin_data.get("daily_stats", {})

        # Get baseline resting HR from user profile
        user_profile = garmin_data.get("user_profile", {})

        # Calculate average resting HR from recent recovery data as baseline
        rhr_baseline = None
        if recovery_indicators:
            rhr_values = [
                r.get("sleep", {}).get("resting_heart_rate")
                for r in recovery_indicators[-14:]  # Last 2 weeks
                if r.get("sleep", {}).get("resting_heart_rate")
            ]
            if rhr_values:
                rhr_baseline = int(sum(rhr_values) / len(rhr_values))

        # Extract sleep duration
        sleep_duration = sleep_data.get("duration", {})
        sleep_hours = sleep_duration.get("total") if isinstance(sleep_duration, dict) else None

        # Extract sleep quality
        sleep_quality_data = sleep_data.get("quality", {})
        sleep_quality = sleep_quality_data.get("overall_score") if isinstance(sleep_quality_data, dict) else None

        # Current resting HR
        current_rhr = (
            sleep_data.get("resting_heart_rate")
            or daily_stats.get("resting_heart_rate")
            or physio_markers.get("resting_heart_rate")
        )

        # Calculate readiness
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            # HRV data
            hrv_weekly_avg=hrv_data.get("weekly_avg"),
            hrv_last_night=hrv_data.get("last_night_avg"),
            hrv_baseline_balanced_low=hrv_data.get("baseline", {}).get("balanced_low"),
            hrv_baseline_balanced_upper=hrv_data.get("baseline", {}).get("balanced_upper"),
            # Sleep data
            sleep_hours=sleep_hours,
            sleep_quality_score=sleep_quality,
            # Resting HR
            resting_hr=current_rhr,
            resting_hr_baseline=rhr_baseline,
            # Training load
            acwr=acute_training_load.get("acwr"),
            acute_load=acute_training_load.get("acute_load"),
            chronic_load=acute_training_load.get("chronic_load"),
            # Stress
            stress_avg=stress_data.get("avg_level"),
            stress_max=stress_data.get("max_level"),
        )

        # Format as text report
        report = calculator.format_readiness_report(readiness)

        logger.info(
            f"Readiness calculated: Score={readiness.score}, "
            f"Recommendation={readiness.recommendation.value}, "
            f"Confidence={readiness.confidence:.2f}"
        )

        # Log signal details
        for signal in readiness.signals:
            logger.info(f"  {signal.name}: {signal.status.value} - {signal.message}")

        return {
            "readiness_result": report,
            "readiness_score": readiness.score,
            "readiness_recommendation": readiness.recommendation.value,
            "readiness_confidence": readiness.confidence,
        }

    except Exception as e:
        logger.exception("Error calculating readiness assessment")
        return {
            "readiness_result": f"⚠️ Readiness assessment unavailable: {str(e)}",
            "readiness_score": None,
            "readiness_recommendation": "moderate",
            "readiness_confidence": 0.0,
            "errors": [f"readiness_node: {str(e)}"],
        }
