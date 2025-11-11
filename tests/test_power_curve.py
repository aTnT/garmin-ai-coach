"""
Tests for Power Curve and Critical Power Analyzer.
"""

from datetime import datetime, timedelta

import pytest

from services.ai.power_curve import (
    BestEffort,
    CriticalPower,
    FitnessProfile,
    PowerCurve,
    PowerCurveAnalyzer,
    PowerMetric,
    TrainingZones,
)


class TestPowerModels:
    """Test suite for power curve models."""

    def test_best_effort_creation(self):
        """Test BestEffort model creation."""
        effort = BestEffort(
            duration_seconds=300,
            duration_label="5min",
            value=350.0,
            metric_type=PowerMetric.POWER_WATTS,
            activity_id="12345",
            activity_date=datetime(2024, 1, 15),
        )

        assert effort.duration_seconds == 300
        assert effort.value == 350.0
        assert effort.metric_type == PowerMetric.POWER_WATTS

    def test_best_effort_validation(self):
        """Test BestEffort validation."""
        with pytest.raises(ValueError):
            BestEffort(
                duration_seconds=-10,  # Invalid: negative
                duration_label="invalid",
                value=350.0,
                metric_type=PowerMetric.POWER_WATTS,
            )

        with pytest.raises(ValueError):
            BestEffort(
                duration_seconds=300,
                duration_label="5min",
                value=-50.0,  # Invalid: negative power
                metric_type=PowerMetric.POWER_WATTS,
            )

    def test_critical_power_prediction(self):
        """Test CP model power prediction."""
        cp = CriticalPower(
            cp=300.0,
            w_prime=20000.0,
            metric_type=PowerMetric.POWER_WATTS,
            r_squared=0.95,
            rmse=10.0,
            efforts_used=[],
            calculation_date=datetime.now(),
        )

        # Predict power for 5 minutes (300 seconds)
        predicted = cp.predict_power(300)
        # P(t) = W'/t + CP = 20000/300 + 300 = 66.67 + 300 = 366.67
        assert abs(predicted - 366.67) < 0.1

        # Predict power for 1 hour (3600 seconds)
        predicted_60min = cp.predict_power(3600)
        # P(t) = 20000/3600 + 300 = 5.56 + 300 = 305.56
        assert abs(predicted_60min - 305.56) < 0.1

    def test_critical_power_time_to_exhaustion(self):
        """Test time to exhaustion calculation."""
        cp = CriticalPower(
            cp=300.0,
            w_prime=20000.0,
            metric_type=PowerMetric.POWER_WATTS,
            r_squared=0.95,
            rmse=10.0,
            efforts_used=[],
            calculation_date=datetime.now(),
        )

        # At 400W (100W above CP)
        # t = W' / (P - CP) = 20000 / (400 - 300) = 20000 / 100 = 200 seconds
        time_to_exhaustion = cp.time_to_exhaustion(400)
        assert abs(time_to_exhaustion - 200) < 0.1

        # Below CP = infinite
        time_below_cp = cp.time_to_exhaustion(250)
        assert time_below_cp == float('inf')

    def test_critical_power_w_prime_balance(self):
        """Test W' balance calculation."""
        cp = CriticalPower(
            cp=300.0,
            w_prime=20000.0,
            metric_type=PowerMetric.POWER_WATTS,
            r_squared=0.95,
            rmse=10.0,
            efforts_used=[],
            calculation_date=datetime.now(),
        )

        # 400W for 100 seconds
        # Expended = (400 - 300) * 100 = 10000J
        # Remaining = 20000 - 10000 = 10000J
        remaining = cp.w_prime_balance(400, 100)
        assert abs(remaining - 10000) < 0.1

        # Below CP = no depletion
        remaining_below = cp.w_prime_balance(250, 1000)
        assert remaining_below == 20000.0

    def test_training_zones_creation(self):
        """Test training zones creation from CP."""
        cp = CriticalPower(
            cp=300.0,
            w_prime=20000.0,
            metric_type=PowerMetric.POWER_WATTS,
            r_squared=0.95,
            rmse=10.0,
            efforts_used=[],
            calculation_date=datetime.now(),
        )

        zones = TrainingZones.from_critical_power(cp)

        assert zones.cp == 300.0
        assert zones.recovery_max == 300.0 * 0.55  # 165W
        assert zones.endurance_max == 300.0 * 0.75  # 225W
        assert zones.tempo_max == 300.0 * 0.90  # 270W
        assert zones.threshold_max == 300.0 * 1.05  # 315W
        assert zones.vo2max_max == 300.0 * 1.20  # 360W

    def test_training_zones_get_zone(self):
        """Test zone determination."""
        zones = TrainingZones(
            metric_type=PowerMetric.POWER_WATTS,
            cp=300.0,
            recovery_max=165.0,
            endurance_max=225.0,
            tempo_max=270.0,
            threshold_max=315.0,
            vo2max_max=360.0,
            anaerobic_min=360.0,
        )

        assert zones.get_zone(150) == (1, "Recovery")
        assert zones.get_zone(200) == (2, "Endurance")
        assert zones.get_zone(250) == (3, "Tempo")
        assert zones.get_zone(300) == (4, "Threshold")
        assert zones.get_zone(340) == (5, "VO2max")
        assert zones.get_zone(400) == (6, "Anaerobic")


class TestPowerCurveAnalyzer:
    """Test suite for PowerCurveAnalyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initializes correctly."""
        analyzer = PowerCurveAnalyzer()
        assert len(analyzer.STANDARD_DURATIONS) > 0
        assert 300 in analyzer.STANDARD_DURATIONS  # 5 minutes
        assert 1200 in analyzer.STANDARD_DURATIONS  # 20 minutes

    def test_extract_best_efforts(self):
        """Test extraction of best efforts from activities."""
        analyzer = PowerCurveAnalyzer()

        # Create sample activities with power streams
        activities = [
            {
                "activity_id": "act1",
                "date": datetime(2024, 1, 15),
                "name": "Morning Ride",
                "type": "Ride",
                "power_stream": [250] * 600 + [350] * 300 + [200] * 300,  # 20 minutes
            },
            {
                "activity_id": "act2",
                "date": datetime(2024, 1, 20),
                "name": "Interval Session",
                "type": "Ride",
                "power_stream": [200] * 300 + [400] * 300 + [150] * 600,  # 20 minutes
            },
        ]

        efforts = analyzer.extract_best_efforts(
            activities, PowerMetric.POWER_WATTS, "cycling"
        )

        assert len(efforts) > 0

        # Should have found 5-minute best (350W from act1 or 400W from act2)
        five_min_effort = next((e for e in efforts if e.duration_seconds == 300), None)
        assert five_min_effort is not None
        # Should be from act2 (400W > 350W)
        assert five_min_effort.value == 400.0

    def test_duration_to_label(self):
        """Test duration label conversion."""
        analyzer = PowerCurveAnalyzer()

        assert analyzer._duration_to_label(5) == "5s"
        assert analyzer._duration_to_label(60) == "1min"
        assert analyzer._duration_to_label(300) == "5min"
        assert analyzer._duration_to_label(3600) == "1hr"
        assert analyzer._duration_to_label(5400) == "1h30m"

    def test_generate_power_curve(self):
        """Test power curve generation."""
        analyzer = PowerCurveAnalyzer()

        # Create realistic power data
        activities = self._create_sample_activities()

        power_curve = analyzer.generate_power_curve(
            athlete_name="Test Athlete",
            activities_data=activities,
            metric_type=PowerMetric.POWER_WATTS,
            sport_type="cycling",
        )

        assert power_curve.athlete_name == "Test Athlete"
        assert power_curve.metric_type == PowerMetric.POWER_WATTS
        assert power_curve.sport_type == "cycling"
        assert len(power_curve.best_efforts) > 0
        assert power_curve.total_activities == len(activities)

        # Check that key powers are extracted
        assert power_curve.peak_5_sec is not None or power_curve.peak_1_min is not None

    def test_calculate_critical_power(self):
        """Test critical power calculation."""
        analyzer = PowerCurveAnalyzer()

        # Create realistic efforts for CP calculation
        # Typically: 3min @ 400W, 5min @ 370W, 20min @ 310W
        efforts = [
            BestEffort(
                duration_seconds=180,
                duration_label="3min",
                value=400.0,
                metric_type=PowerMetric.POWER_WATTS,
            ),
            BestEffort(
                duration_seconds=300,
                duration_label="5min",
                value=370.0,
                metric_type=PowerMetric.POWER_WATTS,
            ),
            BestEffort(
                duration_seconds=600,
                duration_label="10min",
                value=340.0,
                metric_type=PowerMetric.POWER_WATTS,
            ),
            BestEffort(
                duration_seconds=1200,
                duration_label="20min",
                value=310.0,
                metric_type=PowerMetric.POWER_WATTS,
            ),
        ]

        cp_model = analyzer.calculate_critical_power(efforts, PowerMetric.POWER_WATTS)

        assert cp_model is not None
        assert cp_model.cp > 0  # CP should be positive
        assert cp_model.w_prime > 0  # W' should be positive
        assert 0 <= cp_model.r_squared <= 1  # R² between 0 and 1
        assert cp_model.ftp_estimate is not None
        # FTP should be close to 20min power * 0.95 or CP
        assert 250 < cp_model.ftp_estimate < 350

    def test_calculate_critical_power_insufficient_data(self):
        """Test CP calculation with insufficient data."""
        analyzer = PowerCurveAnalyzer()

        # Only one effort
        efforts = [
            BestEffort(
                duration_seconds=300,
                duration_label="5min",
                value=370.0,
                metric_type=PowerMetric.POWER_WATTS,
            ),
        ]

        cp_model = analyzer.calculate_critical_power(efforts, PowerMetric.POWER_WATTS)
        assert cp_model is None  # Should return None

    def test_create_fitness_signature(self):
        """Test fitness signature creation."""
        analyzer = PowerCurveAnalyzer()

        # Create power curve with all key powers
        efforts = [
            BestEffort(5, "5s", 1200.0, PowerMetric.POWER_WATTS),
            BestEffort(60, "1min", 600.0, PowerMetric.POWER_WATTS),
            BestEffort(300, "5min", 400.0, PowerMetric.POWER_WATTS),
            BestEffort(1200, "20min", 320.0, PowerMetric.POWER_WATTS),
            BestEffort(3600, "60min", 280.0, PowerMetric.POWER_WATTS),
        ]

        power_curve = PowerCurve(
            athlete_name="Test Athlete",
            metric_type=PowerMetric.POWER_WATTS,
            sport_type="cycling",
            best_efforts=efforts,
            data_period_start=datetime.now() - timedelta(days=90),
            data_period_end=datetime.now(),
            total_activities=50,
        )

        signature = analyzer.create_fitness_signature(power_curve)

        assert signature.cp > 0
        assert signature.w_prime > 0
        assert signature.peak_5_sec == 1200.0
        assert signature.peak_1_min == 600.0
        assert signature.peak_5_min == 400.0
        assert signature.peak_20_min == 320.0
        assert signature.peak_60_min == 280.0
        assert signature.fatigue_resistance is not None
        assert signature.fitness_profile in FitnessProfile

    def test_compare_power_curves(self):
        """Test power curve comparison."""
        analyzer = PowerCurveAnalyzer()

        # Current curve (improved)
        current_efforts = [
            BestEffort(300, "5min", 400.0, PowerMetric.POWER_WATTS),
            BestEffort(1200, "20min", 330.0, PowerMetric.POWER_WATTS),
        ]

        current_curve = PowerCurve(
            athlete_name="Test Athlete",
            metric_type=PowerMetric.POWER_WATTS,
            sport_type="cycling",
            best_efforts=current_efforts,
            data_period_start=datetime.now() - timedelta(days=30),
            data_period_end=datetime.now(),
            total_activities=20,
        )

        # Previous curve
        previous_efforts = [
            BestEffort(300, "5min", 370.0, PowerMetric.POWER_WATTS),
            BestEffort(1200, "20min", 310.0, PowerMetric.POWER_WATTS),
        ]

        previous_curve = PowerCurve(
            athlete_name="Test Athlete",
            metric_type=PowerMetric.POWER_WATTS,
            sport_type="cycling",
            best_efforts=previous_efforts,
            data_period_start=datetime.now() - timedelta(days=120),
            data_period_end=datetime.now() - timedelta(days=90),
            total_activities=20,
        )

        comparison = analyzer.compare_power_curves(
            current_curve, previous_curve, "vs 3 months ago"
        )

        assert comparison.overall_change_percent > 0  # Should show improvement
        assert len(comparison.improving_durations) > 0  # Should have improving durations
        # 5min: (400 - 370) / 370 * 100 = 8.1% improvement
        # 20min: (330 - 310) / 310 * 100 = 6.5% improvement

    def test_identify_limiters(self):
        """Test limiter identification."""
        analyzer = PowerCurveAnalyzer()

        # Create power curve with weak endurance
        efforts = [
            BestEffort(5, "5s", 1200.0, PowerMetric.POWER_WATTS),
            BestEffort(60, "1min", 600.0, PowerMetric.POWER_WATTS),
            BestEffort(300, "5min", 420.0, PowerMetric.POWER_WATTS),
            BestEffort(1200, "20min", 350.0, PowerMetric.POWER_WATTS),
            BestEffort(3600, "60min", 300.0, PowerMetric.POWER_WATTS),  # Poor endurance
        ]

        power_curve = PowerCurve(
            athlete_name="Test Athlete",
            metric_type=PowerMetric.POWER_WATTS,
            sport_type="cycling",
            best_efforts=efforts,
            data_period_start=datetime.now() - timedelta(days=90),
            data_period_end=datetime.now(),
            total_activities=50,
        )

        signature = analyzer.create_fitness_signature(power_curve)
        limiters = analyzer.identify_limiters(power_curve, signature)

        assert "recommendations" in limiters
        assert len(limiters["recommendations"]) > 0

        # Fatigue resistance = 300 / 420 = 0.714 < 0.75 (weak)
        assert limiters["endurance"] == "weak"

    def test_predict_race_performance(self):
        """Test race performance prediction."""
        analyzer = PowerCurveAnalyzer()

        cp_model = CriticalPower(
            cp=300.0,
            w_prime=20000.0,
            metric_type=PowerMetric.POWER_WATTS,
            r_squared=0.95,
            rmse=10.0,
            efforts_used=[],
            calculation_date=datetime.now(),
        )

        # Predict for 40km TT (approximately 60 minutes for pro)
        prediction = analyzer.predict_race_performance(
            cp_model, race_duration_seconds=3600, w_prime_usage_pct=90
        )

        assert prediction["predicted_average_power"] > cp_model.cp
        assert prediction["race_duration_minutes"] == 60
        assert prediction["anaerobic_contribution_pct"] < 10  # Low for 1hr effort
        # P = (20000 * 0.9 / 3600) + 300 = 5 + 300 = 305W
        assert abs(prediction["predicted_average_power"] - 305) < 1

    def _create_sample_activities(self) -> list[dict]:
        """Helper to create sample activity data."""
        activities = []

        # Activity 1: Steady endurance ride
        activities.append({
            "activity_id": "act1",
            "date": datetime(2024, 1, 10),
            "name": "Endurance Ride",
            "type": "Ride",
            "power_stream": [250] * 7200,  # 2 hours at 250W
        })

        # Activity 2: Interval session
        power_stream = []
        # Warm-up
        power_stream.extend([200] * 600)
        # 5x5min intervals at 370W with 3min recovery
        for _ in range(5):
            power_stream.extend([370] * 300)  # 5min
            power_stream.extend([150] * 180)  # 3min recovery
        # Cool-down
        power_stream.extend([180] * 600)

        activities.append({
            "activity_id": "act2",
            "date": datetime(2024, 1, 15),
            "name": "VO2max Intervals",
            "type": "Ride",
            "power_stream": power_stream,
        })

        # Activity 3: 20min test
        test_stream = [200] * 600  # Warm-up
        test_stream.extend([320] * 1200)  # 20min test
        test_stream.extend([180] * 600)  # Cool-down

        activities.append({
            "activity_id": "act3",
            "date": datetime(2024, 1, 20),
            "name": "FTP Test",
            "type": "Ride",
            "power_stream": test_stream,
        })

        return activities


@pytest.mark.integration
class TestPowerCurveIntegration:
    """Integration tests for power curve analysis."""

    def test_full_analysis_pipeline(self):
        """Test complete analysis from activities to insights."""
        analyzer = PowerCurveAnalyzer()

        # Create realistic activity history
        activities = self._create_realistic_activities()

        # Generate power curve
        power_curve = analyzer.generate_power_curve(
            athlete_name="John Doe",
            activities_data=activities,
            metric_type=PowerMetric.POWER_WATTS,
            sport_type="cycling",
        )

        # Calculate critical power
        cp_model = analyzer.calculate_critical_power(
            power_curve.best_efforts, PowerMetric.POWER_WATTS
        )

        assert cp_model is not None
        assert cp_model.cp > 200  # Reasonable CP for trained cyclist
        assert cp_model.w_prime > 10000  # Reasonable W'

        # Generate training zones
        zones = analyzer.generate_training_zones(cp_model)
        assert zones.recovery_max < zones.endurance_max < zones.tempo_max

        # Create fitness signature
        signature = analyzer.create_fitness_signature(power_curve, cp_model)
        assert signature.fitness_profile is not None

        # Identify limiters
        limiters = analyzer.identify_limiters(power_curve, signature)
        assert len(limiters["recommendations"]) > 0

        # Predict race performance
        prediction = analyzer.predict_race_performance(cp_model, 3600)  # 1 hour
        assert 280 < prediction["predicted_average_power"] < 350

    def _create_realistic_activities(self) -> list[dict]:
        """Create realistic 3-month activity history."""
        import random
        random.seed(42)

        activities = []
        base_date = datetime.now() - timedelta(days=90)

        for week in range(12):  # 12 weeks
            week_start = base_date + timedelta(weeks=week)

            # 3-4 rides per week
            num_rides = random.choice([3, 4])

            for ride in range(num_rides):
                ride_date = week_start + timedelta(days=ride * 2)
                ride_type = random.choice(["endurance", "tempo", "intervals", "recovery"])

                if ride_type == "endurance":
                    # 2-3 hour steady ride
                    duration = random.randint(7200, 10800)
                    power = random.randint(220, 260)
                    power_stream = [power + random.randint(-10, 10) for _ in range(duration)]

                elif ride_type == "tempo":
                    # 90 min with tempo blocks
                    power_stream = []
                    power_stream.extend([200] * 600)  # Warm-up
                    power_stream.extend([280] * 1800)  # 30min tempo
                    power_stream.extend([220] * 300)  # Recovery
                    power_stream.extend([280] * 1800)  # 30min tempo
                    power_stream.extend([180] * 600)  # Cool-down

                elif ride_type == "intervals":
                    # VO2max or threshold intervals
                    power_stream = []
                    power_stream.extend([200] * 600)  # Warm-up

                    # 4x5min at 360W
                    for _ in range(4):
                        power_stream.extend([360] * 300)
                        power_stream.extend([150] * 180)

                    power_stream.extend([180] * 600)  # Cool-down

                else:  # recovery
                    # 1 hour easy
                    power_stream = [180 + random.randint(-10, 10) for _ in range(3600)]

                activities.append({
                    "activity_id": f"act_{week}_{ride}",
                    "date": ride_date,
                    "name": f"{ride_type.title()} Ride",
                    "type": "Ride",
                    "power_stream": power_stream,
                })

        return activities
