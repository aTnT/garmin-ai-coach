"""
Tests for the Training Readiness Calculator.
"""

import pytest

from services.ai.readiness.readiness_calculator import (
    ReadinessCalculator,
    ReadinessRecommendation,
    Signal,
    SignalStatus,
)


class TestReadinessCalculator:
    """Test suite for ReadinessCalculator."""

    def test_optimal_readiness_all_signals_good(self):
        """Test readiness calculation with all optimal signals."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_weekly_avg=65.0,
            hrv_last_night=67.0,
            hrv_baseline_balanced_low=55.0,
            hrv_baseline_balanced_upper=75.0,
            sleep_hours=8.0,
            sleep_quality_score=85.0,
            resting_hr=52,
            resting_hr_baseline=52,
            acwr=1.1,
            acute_load=250.0,
            chronic_load=227.0,
            stress_avg=25,
            stress_max=45,
        )

        assert readiness.score >= 85, "All optimal signals should give high readiness"
        assert readiness.recommendation == ReadinessRecommendation.PEAK
        assert readiness.confidence > 0.8, "Should have high confidence with complete data"

        # Check all signals are optimal or acceptable
        for signal in readiness.signals:
            assert signal.status in [SignalStatus.OPTIMAL, SignalStatus.ACCEPTABLE]

    def test_low_readiness_multiple_concerns(self):
        """Test readiness calculation with multiple concerning signals."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_weekly_avg=45.0,
            hrv_last_night=40.0,  # Below baseline
            hrv_baseline_balanced_low=55.0,
            hrv_baseline_balanced_upper=75.0,
            sleep_hours=5.0,  # Insufficient
            sleep_quality_score=45.0,  # Poor quality
            resting_hr=62,  # Elevated
            resting_hr_baseline=52,
            acwr=1.7,  # High injury risk
            acute_load=380.0,
            chronic_load=224.0,
            stress_avg=75,  # High stress
            stress_max=92,
        )

        assert readiness.score < 55, "Multiple concerns should give low readiness"
        assert readiness.recommendation in [
            ReadinessRecommendation.REST,
            ReadinessRecommendation.EASY,
        ]

        # Should have multiple concern signals
        concern_count = sum(1 for s in readiness.signals if s.status == SignalStatus.CONCERN)
        assert concern_count >= 3, "Should identify multiple concerning signals"

    def test_moderate_readiness_mixed_signals(self):
        """Test readiness with mix of good and concerning signals."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_weekly_avg=62.0,
            hrv_last_night=60.0,
            hrv_baseline_balanced_low=55.0,
            hrv_baseline_balanced_upper=75.0,
            sleep_hours=6.5,  # Acceptable but not optimal
            sleep_quality_score=72.0,
            resting_hr=55,  # Slightly elevated (but still within optimal threshold)
            resting_hr_baseline=52,
            acwr=1.2,  # Good
            acute_load=280.0,
            chronic_load=233.0,
            stress_avg=42,  # Moderate
        )

        # With mostly optimal signals (HRV, HR, ACWR) and only 2 acceptable (sleep, stress),
        # score should be high (80-90 range)
        assert 80 <= readiness.score <= 95, f"Mostly optimal signals should give high readiness, got {readiness.score}"
        assert readiness.recommendation in [
            ReadinessRecommendation.NORMAL,
            ReadinessRecommendation.PEAK,
        ]

    def test_hrv_signal_assessment_balanced(self):
        """Test HRV signal when in balanced range."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_last_night=65.0,
            hrv_baseline_balanced_low=60.0,
            hrv_baseline_balanced_upper=70.0,
        )

        hrv_signal = next((s for s in readiness.signals if s.name == "HRV"), None)
        assert hrv_signal is not None
        assert hrv_signal.status == SignalStatus.OPTIMAL
        assert "balanced" in hrv_signal.message.lower()

    def test_hrv_signal_assessment_low(self):
        """Test HRV signal when below baseline."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_last_night=45.0,  # Well below baseline
            hrv_baseline_balanced_low=60.0,
            hrv_baseline_balanced_upper=70.0,
        )

        hrv_signal = next((s for s in readiness.signals if s.name == "HRV"), None)
        assert hrv_signal is not None
        assert hrv_signal.status == SignalStatus.CONCERN
        assert "below baseline" in hrv_signal.message.lower()

    def test_sleep_signal_assessment_optimal(self):
        """Test sleep signal with optimal duration."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            sleep_hours=8.0,
            sleep_quality_score=85.0,
        )

        sleep_signal = next((s for s in readiness.signals if s.name == "Sleep"), None)
        assert sleep_signal is not None
        assert sleep_signal.status == SignalStatus.OPTIMAL
        assert "excellent" in sleep_signal.message.lower()

    def test_sleep_signal_assessment_insufficient(self):
        """Test sleep signal with insufficient duration."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            sleep_hours=5.0,
            sleep_quality_score=50.0,
        )

        sleep_signal = next((s for s in readiness.signals if s.name == "Sleep"), None)
        assert sleep_signal is not None
        assert sleep_signal.status == SignalStatus.CONCERN
        assert sleep_signal.value == 5.0

    def test_training_load_optimal_range(self):
        """Test training load in optimal ACWR range."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            acwr=1.0,
            acute_load=250.0,
            chronic_load=250.0,
        )

        load_signal = next((s for s in readiness.signals if "Load" in s.name), None)
        assert load_signal is not None
        assert load_signal.status == SignalStatus.OPTIMAL
        assert "optimal" in load_signal.message.lower()

    def test_training_load_high_injury_risk(self):
        """Test training load with high ACWR (injury risk)."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            acwr=1.8,  # High risk
            acute_load=400.0,
            chronic_load=222.0,
        )

        load_signal = next((s for s in readiness.signals if "Load" in s.name), None)
        assert load_signal is not None
        assert load_signal.status == SignalStatus.CONCERN
        assert "HIGH" in load_signal.message or "injury risk" in load_signal.message.lower()

    def test_resting_hr_normal(self):
        """Test resting HR signal when normal."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            resting_hr=52,
            resting_hr_baseline=52,
        )

        rhr_signal = next((s for s in readiness.signals if "HR" in s.name), None)
        assert rhr_signal is not None
        assert rhr_signal.status == SignalStatus.OPTIMAL
        assert rhr_signal.deviation == 0.0

    def test_resting_hr_elevated(self):
        """Test resting HR signal when significantly elevated."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            resting_hr=62,  # +10 bpm
            resting_hr_baseline=52,
        )

        rhr_signal = next((s for s in readiness.signals if "HR" in s.name), None)
        assert rhr_signal is not None
        assert rhr_signal.status == SignalStatus.CONCERN
        assert rhr_signal.deviation == 10.0
        assert "elevated" in rhr_signal.message.lower() or "HIGH" in rhr_signal.message

    def test_stress_signal_low(self):
        """Test stress signal when low."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            stress_avg=25,
            stress_max=40,
        )

        stress_signal = next((s for s in readiness.signals if s.name == "Stress"), None)
        assert stress_signal is not None
        assert stress_signal.status == SignalStatus.OPTIMAL

    def test_stress_signal_high(self):
        """Test stress signal when high."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            stress_avg=75,
            stress_max=90,
        )

        stress_signal = next((s for s in readiness.signals if s.name == "Stress"), None)
        assert stress_signal is not None
        assert stress_signal.status in [SignalStatus.ACCEPTABLE, SignalStatus.CONCERN]

    def test_partial_data_lower_confidence(self):
        """Test that missing signals result in lower confidence."""
        calculator = ReadinessCalculator()

        # Only provide 2 signals
        readiness = calculator.calculate_readiness(
            sleep_hours=7.5,
            acwr=1.1,
        )

        assert readiness.confidence < 0.5, "Partial data should result in lower confidence"
        assert len(readiness.signals) == 2

    def test_modifications_rest_recommendation(self):
        """Test that REST recommendation includes appropriate modifications."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_last_night=40.0,
            hrv_baseline_balanced_low=65.0,
            hrv_baseline_balanced_upper=75.0,
            sleep_hours=4.5,
            resting_hr=68,
            resting_hr_baseline=52,
            acwr=1.9,
            stress_avg=82,
        )

        assert readiness.recommendation in [
            ReadinessRecommendation.REST,
            ReadinessRecommendation.EASY,
        ]
        assert len(readiness.modifications) > 0

        # Should recommend rest
        has_rest_recommendation = any(
            "REST" in mod.upper() or "rest day" in mod.lower() for mod in readiness.modifications
        )
        assert has_rest_recommendation

    def test_modifications_peak_recommendation(self):
        """Test that PEAK recommendation includes positive encouragement."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_last_night=70.0,
            hrv_baseline_balanced_low=60.0,
            hrv_baseline_balanced_upper=75.0,
            sleep_hours=8.5,
            sleep_quality_score=90.0,
            resting_hr=50,
            resting_hr_baseline=52,
            acwr=1.05,
            stress_avg=20,
        )

        assert readiness.recommendation == ReadinessRecommendation.PEAK
        assert len(readiness.modifications) > 0

        # Should encourage high-quality training
        has_peak_message = any(
            "PEAK" in mod.upper() or "key workout" in mod.lower()
            for mod in readiness.modifications
        )
        assert has_peak_message

    def test_reasoning_generation(self):
        """Test that reasoning is generated with signal summary."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_last_night=65.0,
            hrv_baseline_balanced_low=60.0,
            hrv_baseline_balanced_upper=70.0,
            sleep_hours=7.5,
            acwr=1.2,
        )

        assert len(readiness.reasoning) > 0
        assert str(readiness.score) in readiness.reasoning
        assert "signals" in readiness.reasoning.lower()

    def test_format_readiness_report(self):
        """Test report formatting."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_last_night=65.0,
            hrv_baseline_balanced_low=60.0,
            hrv_baseline_balanced_upper=70.0,
            sleep_hours=7.5,
            acwr=1.1,
        )

        report = calculator.format_readiness_report(readiness)

        assert "TRAINING READINESS ASSESSMENT" in report
        assert f"Overall Score: {readiness.score}/100" in report
        assert "PHYSIOLOGICAL SIGNALS:" in report
        assert "ANALYSIS:" in report
        assert "TRAINING RECOMMENDATIONS:" in report

    def test_no_data_returns_moderate_default(self):
        """Test that no data returns moderate default score."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness()

        assert readiness.score == 50, "No data should default to moderate score"
        assert len(readiness.signals) == 0
        assert readiness.confidence == 0.0

    def test_acwr_undertraining_warning(self):
        """Test ACWR detection of undertraining."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            acwr=0.6,  # Low, undertraining
            acute_load=150.0,
            chronic_load=250.0,
        )

        load_signal = next((s for s in readiness.signals if "Load" in s.name), None)
        assert load_signal is not None
        assert "low" in load_signal.message.lower() or "undertraining" in load_signal.message.lower()


@pytest.mark.integration
class TestReadinessIntegration:
    """Integration tests with realistic Garmin data patterns."""

    def test_post_race_recovery_scenario(self):
        """Test readiness after a race (typical recovery pattern)."""
        calculator = ReadinessCalculator()

        # Day after hard race
        readiness = calculator.calculate_readiness(
            hrv_last_night=48.0,  # Suppressed
            hrv_baseline_balanced_low=60.0,
            hrv_baseline_balanced_upper=70.0,
            sleep_hours=7.0,
            resting_hr=58,  # Elevated
            resting_hr_baseline=52,
            acwr=1.4,  # Spike from race
            stress_avg=55,
        )

        assert readiness.score < 70, "Post-race should show reduced readiness"
        assert readiness.recommendation in [
            ReadinessRecommendation.REST,
            ReadinessRecommendation.EASY,
            ReadinessRecommendation.MODERATE,
        ]

    def test_well_rested_athlete_scenario(self):
        """Test readiness for well-rested, well-trained athlete."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_last_night=68.0,
            hrv_baseline_balanced_low=60.0,
            hrv_baseline_balanced_upper=72.0,
            sleep_hours=8.5,
            sleep_quality_score=88.0,
            resting_hr=50,
            resting_hr_baseline=52,
            acwr=0.95,
            stress_avg=22,
        )

        assert readiness.score >= 80, "Well-rested athlete should have high readiness"
        assert readiness.recommendation in [
            ReadinessRecommendation.PEAK,
            ReadinessRecommendation.NORMAL,
        ]

    def test_overreaching_scenario(self):
        """Test readiness during overreaching (high load, poor recovery)."""
        calculator = ReadinessCalculator()

        readiness = calculator.calculate_readiness(
            hrv_last_night=42.0,  # Very suppressed
            hrv_baseline_balanced_low=58.0,
            hrv_baseline_balanced_upper=68.0,
            sleep_hours=6.0,
            sleep_quality_score=55.0,
            resting_hr=64,  # Very elevated
            resting_hr_baseline=52,
            acwr=1.75,  # High spike
            stress_avg=68,
        )

        assert readiness.score < 50, "Overreaching should show very low readiness"
        assert readiness.recommendation in [
            ReadinessRecommendation.REST,
            ReadinessRecommendation.EASY,
        ]

        # Should have multiple concerning signals
        concern_count = sum(1 for s in readiness.signals if s.status == SignalStatus.CONCERN)
        assert concern_count >= 2
