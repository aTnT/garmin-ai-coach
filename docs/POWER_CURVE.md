# Power Curve & Critical Power Analysis Feature

## Overview

The **Power Curve & Critical Power Analysis** feature provides comprehensive power/pace analysis for endurance athletes. It generates power curves, calculates Critical Power (CP) and anaerobic capacity (W'), creates training zones, identifies performance limiters, and predicts race performance.

## Features

### ✅ Power Curve Generation
- **Best Efforts Extraction** - Automatically finds personal bests across all durations
- **Standard Durations** - 5s, 30s, 1min, 5min, 20min, 60min, 2hr, etc.
- **Multi-Sport Support** - Cycling (watts), running (pace), swimming
- **Historical Tracking** - Compare curves over time

### ✅ Critical Power Calculation
- **2-Parameter CP Model** - CP (sustainable power) and W' (anaerobic capacity)
- **Linear Regression** - Statistical fit with R-squared confidence
- **FTP Estimation** - Functional Threshold Power from CP or 20min test
- **Race Prediction** - Estimate sustainable power for any duration

### ✅ Fitness Signature
- **Profile Classification** - Sprinter, Pursuer, Time Trialist, All-Rounder
- **Strength Analysis** - Identify sprint, VO2max, threshold, endurance capabilities
- **Fatigue Resistance** - How well power holds over long durations
- **Limiter Identification** - Pinpoint weaknesses to target in training

### ✅ Training Zones
- **CP-Based Zones** - More physiologically accurate than FTP-based
- **6-Zone Model** - Recovery, Endurance, Tempo, Threshold, VO2max, Anaerobic
- **Auto-Calculation** - Zones derived from Critical Power model

### ✅ Interactive Visualizations
- **Power Curve Charts** - Log-scale duration vs power
- **CP Model Overlay** - Compare actual vs predicted
- **Training Zone Visualization** - Color-coded power ranges
- **Fitness Radar Charts** - Multi-dimensional performance view
- **Historical Comparison** - Track improvements over time

---

## Scientific Basis

### Critical Power Model

The **2-parameter Critical Power model** describes the relationship between power and time to exhaustion:

```
P(t) = W'/t + CP

Where:
- P(t) = sustainable power for duration t
- CP = Critical Power (asymptotic sustainable power)
- W' = Anaerobic Work Capacity (joules)
```

**Key Concepts:**

1. **Critical Power (CP)**:
   - Maximal power sustainable for ~30-60 minutes
   - Represents aerobic capacity threshold
   - Similar to FTP but more physiologically grounded
   - Typically 300-350W for trained male cyclists

2. **W' (W-prime / Anaerobic Capacity)**:
   - Fixed amount of work available above CP
   - Depletes during efforts above CP
   - Recovers during efforts below CP
   - Typically 15,000-25,000 J for trained cyclists

3. **Time to Exhaustion**:
   ```
   t = W' / (P - CP)
   ```
   At power P above CP, time until exhaustion is W' divided by the power above CP.

4. **W' Balance**:
   ```
   W'_remaining = W' - (P - CP) × t
   ```
   After time t at power P, remaining anaerobic capacity.

### Research Support

- **Monod & Scherrer (1965)**: Original CP model development
- **Jones et al. (2010)**: "The 'Critical Power' Concept" comprehensive review
- **Skiba et al. (2012)**: W' balance modeling
- **Karsten et al. (2015)**: CP validity for pacing strategies

---

## Architecture

### Core Components

```
services/ai/power_curve/
├── power_models.py      # Data structures (CP, PowerCurve, FitnessSignature, etc.)
├── power_analyzer.py    # Analysis engine and CP calculations
├── power_plotter.py     # Interactive visualizations
└── __init__.py         # Public interface
```

### Data Flow

```
Activity Data (power streams)
    ↓
PowerCurveAnalyzer
    ↓
Extract Best Efforts (5s, 1min, 5min, 20min, etc.)
    ↓
PowerCurve
    ↓
Calculate Critical Power (linear regression)
    ↓
CriticalPower Model (CP + W')
    ↓
├─→ TrainingZones (6 zones based on CP)
├─→ FitnessSignature (profile classification)
├─→ Limiter Analysis (identify weaknesses)
└─→ Race Predictions (estimate performance)
    ↓
PowerCurvePlotter → Visualizations
```

---

## Usage

### Basic Power Curve Analysis

```python
from datetime import datetime
from services.ai.power_curve import PowerCurveAnalyzer, PowerMetric

# Create analyzer
analyzer = PowerCurveAnalyzer()

# Prepare activity data with power streams
activities = [
    {
        "activity_id": "12345",
        "date": datetime(2024, 1, 15),
        "name": "Morning Ride",
        "type": "Ride",
        "power_stream": [250, 255, 248, ...],  # Second-by-second power data
    },
    # ... more activities
]

# Generate power curve
power_curve = analyzer.generate_power_curve(
    athlete_name="John Doe",
    activities_data=activities,
    metric_type=PowerMetric.POWER_WATTS,
    sport_type="cycling"
)

# View best efforts
for effort in power_curve.best_efforts:
    print(f"{effort.duration_label}: {effort.value:.1f}W")

# Key powers
print(f"5s Peak: {power_curve.peak_5_sec:.1f}W")
print(f"1min Peak: {power_curve.peak_1_min:.1f}W")
print(f"5min Peak: {power_curve.peak_5_min:.1f}W")
print(f"20min Peak: {power_curve.peak_20_min:.1f}W")
print(f"60min Peak: {power_curve.peak_60_min:.1f}W")
```

### Calculate Critical Power

```python
# Calculate CP from best efforts
cp_model = analyzer.calculate_critical_power(
    power_curve.best_efforts,
    PowerMetric.POWER_WATTS
)

print(f"Critical Power: {cp_model.cp:.1f}W")
print(f"W' (Anaerobic Capacity): {cp_model.w_prime:.0f}J")
print(f"FTP Estimate: {cp_model.ftp_estimate:.1f}W")
print(f"Model Confidence (R²): {cp_model.r_squared:.3f}")

# Predict power for any duration
predicted_30min = cp_model.predict_power(1800)  # 30 minutes
print(f"Predicted 30min Power: {predicted_30min:.1f}W")

# Time to exhaustion at 400W
tte = cp_model.time_to_exhaustion(400)
print(f"Time to exhaustion at 400W: {tte/60:.1f} minutes")
```

### Generate Training Zones

```python
# Create training zones from CP
zones = analyzer.generate_training_zones(cp_model)

print(f"Zone 1 (Recovery): 0 - {zones.recovery_max:.0f}W")
print(f"Zone 2 (Endurance): {zones.recovery_max:.0f} - {zones.endurance_max:.0f}W")
print(f"Zone 3 (Tempo): {zones.endurance_max:.0f} - {zones.tempo_max:.0f}W")
print(f"Zone 4 (Threshold): {zones.tempo_max:.0f} - {zones.threshold_max:.0f}W")
print(f"Zone 5 (VO2max): {zones.threshold_max:.0f} - {zones.vo2max_max:.0f}W")
print(f"Zone 6 (Anaerobic): {zones.vo2max_max:.0f}W+")

# Determine zone for a workout
zone_num, zone_name = zones.get_zone(285)
print(f"285W is in Zone {zone_num}: {zone_name}")
```

### Create Fitness Signature

```python
# Generate fitness signature
signature = analyzer.create_fitness_signature(power_curve, cp_model)

print(f"Fitness Profile: {signature.fitness_profile.value}")
print(f"Fatigue Resistance: {signature.fatigue_resistance:.2f}")

# Profile classification
if signature.fitness_profile == FitnessProfile.SPRINTER:
    print("Strong in short efforts, focus on building endurance")
elif signature.fitness_profile == FitnessProfile.TIME_TRIALIST:
    print("Strong endurance, consider adding high-intensity work")
```

### Identify Limiters

```python
# Identify performance limiters
limiters = analyzer.identify_limiters(power_curve, signature)

print("Performance Limiters:")
for category, status in limiters.items():
    if status and status != "strong" and category != "recommendations":
        print(f"  {category}: {status}")

print("\nRecommendations:")
for rec in limiters["recommendations"]:
    print(f"  - {rec}")
```

### Predict Race Performance

```python
# Predict power for 40km TT (~60 minutes)
prediction = analyzer.predict_race_performance(
    cp_model,
    race_duration_seconds=3600,
    w_prime_usage_pct=90  # Use 90% of W'
)

print(f"Predicted Average Power: {prediction['predicted_average_power']:.1f}W")
print(f"Total Work: {prediction['total_work_kj']:.1f} kJ")
print(f"Aerobic Contribution: {100 - prediction['anaerobic_contribution_pct']:.1f}%")
print(f"Anaerobic Contribution: {prediction['anaerobic_contribution_pct']:.1f}%")
```

### Create Visualizations

```python
from services.ai.power_curve import PowerCurvePlotter

plotter = PowerCurvePlotter()

# Power curve with CP model overlay
fig = plotter.plot_power_curve(power_curve, show_model=True, cp_model=cp_model)
fig.show()
fig.write_html("power_curve.html")

# Training zones
zones_fig = plotter.plot_training_zones(zones)
zones_fig.show()

# Fitness signature radar chart
signature_fig = plotter.plot_fitness_signature(signature)
signature_fig.show()

# Complete dashboard
dashboard = plotter.create_power_dashboard(
    power_curve, cp_model, zones, signature, limiters
)
for name, fig in dashboard.items():
    fig.write_html(f"{name}.html")
```

---

## Training Zone Guide

### CP-Based Zones (6-Zone Model)

| Zone | Name | % of CP | Duration | Purpose | Feel |
|------|------|---------|----------|---------|------|
| 1 | Recovery | <55% | Any | Active recovery, adaptation | Very easy, conversational |
| 2 | Endurance | 55-75% | 2-6+ hrs | Aerobic base, fat adaptation | Easy, comfortable |
| 3 | Tempo | 75-90% | 20-90 min | Aerobic development | Moderately hard |
| 4 | Threshold | 90-105% | 8-30 min | Lactate threshold, FTP | Hard, sustainable |
| 5 | VO2max | 105-120% | 3-8 min | Maximal aerobic power | Very hard |
| 6 | Anaerobic | >120% | 30s-3 min | Anaerobic capacity | Maximal |

### Training Applications

**Zone 1 (Recovery):**
- After hard workouts
- Active recovery days
- Warm-up/cool-down
- Very high volume possible

**Zone 2 (Endurance):**
- Base building phase
- Long rides (>2 hours)
- Fat adaptation
- Mitochondrial development

**Zone 3 (Tempo):**
- "Sweetspot" training (88-92% CP)
- Muscular endurance
- Time-efficient aerobic work
- Pre-competition phase

**Zone 4 (Threshold):**
- FTP/CP development
- Lactate clearance
- 2×20min, 3×15min, 4×10min intervals
- Race-specific for 40km TT, marathon

**Zone 5 (VO2max):**
- Maximal aerobic capacity
- Cardiac output
- 4-6 × 5min intervals
- Important for 5km run, 4km pursuit

**Zone 6 (Anaerobic):**
- Neuromuscular power
- W' development
- Sprint intervals, hill repeats
- Closing efforts in races

---

## Fitness Profiles

### Profile Classifications

**Sprinter:**
- High 5s / 60min ratio (>4.0)
- Strong neuromuscular power
- High peak power, lower sustained
- *Training focus:* Build aerobic base and endurance

**Pursuer:**
- High 5min / 60min ratio (>1.35)
- Strong VO2max
- Excel at 3-8 minute efforts
- *Training focus:* Improve threshold and long efforts

**Time Trialist:**
- High 60min / 5min ratio (>0.75)
- Excellent fatigue resistance
- Strong sustained power
- *Training focus:* Add high-intensity intervals

**All-Rounder:**
- Balanced across all durations
- No clear strength/weakness
- Versatile for various events
- *Training focus:* Event-specific development

**Ultra-Endurance:**
- Strong at very long durations (>2hrs)
- Excellent fat utilization
- May lack high-end power
- *Training focus:* High-intensity work

---

## Practical Examples

### Example 1: Trained Cyclist Profile

```
Athlete: Sarah Johnson
CP: 285W
W': 18,500J
FTP: 280W (from 20min test)

Best Efforts:
- 5s:    1050W
- 1min:   520W
- 5min:   360W
- 20min:  295W
- 60min:  280W

Profile: Time Trialist
Fatigue Resistance: 0.78 (excellent)

Limiters:
- Sprint power: Weak (5s/60min = 3.75)
- VO2max: Moderate (5min only 1.29× CP)

Recommendations:
- Add sprint intervals (10-30s) 1× per week
- Include 4-6 × 5min VO2max intervals
- Continue strength in threshold and endurance
```

### Example 2: Improving Power Curve

```
Comparison: Current vs 6 Months Ago

Duration | Previous | Current | Change
---------|----------|---------|--------
5s       | 980W     | 1020W   | +4.1%
1min     | 480W     | 510W    | +6.3%
5min     | 330W     | 355W    | +7.6%
20min    | 275W     | 295W    | +7.3%
60min    | 255W     | 275W    | +7.8%

Overall: +6.6% improvement
Improving Durations: All
Profile shift: All-Rounder → Time Trialist

CP Change: 260W → 280W (+7.7%)
W' Change: 16,000J → 18,000J (+12.5%)
```

### Example 3: Race Pacing

```
Event: 40km Time Trial
Target Time: 60 minutes
CP: 290W
W': 20,000J

Pacing Strategy (90% W' usage):
- Predicted Avg Power: 295W
- Total Work: 17.7 kJ
- Aerobic: 17.4 kJ (98%)
- Anaerobic: 0.3 kJ (2%)

Recommendation:
- Start at 300W for first 5min (deplete 3000J)
- Settle to 293-297W (slight variability OK)
- Final 5min: 300-305W (use remaining W')
- Avoid surges above 320W (rapid W' depletion)
```

---

## Integration with Garmin AI Coach

### Automatic Analysis

```python
# In main coach workflow
from services.ai.power_curve import PowerCurveAnalyzer, PowerMetric

# Fetch power data from Garmin
activities = garmin_client.get_activities_with_streams(days=90)

# Generate power curve
analyzer = PowerCurveAnalyzer()
power_curve = analyzer.generate_power_curve(
    athlete_name=user.name,
    activities_data=activities,
    metric_type=PowerMetric.POWER_WATTS,
    sport_type="cycling"
)

# Calculate CP
cp_model = analyzer.calculate_critical_power(
    power_curve.best_efforts,
    PowerMetric.POWER_WATTS
)

# Use CP for training recommendations
if cp_model:
    zones = analyzer.generate_training_zones(cp_model)
    # Incorporate zones into workout prescriptions
```

---

## Best Practices

### For Athletes

1. **Data Quality**
   - Use power meter or smart trainer consistently
   - Calibrate regularly
   - Ensure good GPS for pace data
   - Need 8-12 weeks of varied training for accurate CP

2. **Testing Protocol**
   - Perform 3-5 maximal efforts at different durations
   - Ideal: 3min, 5min, 12min, 20min tests
   - Fresh condition (well-rested)
   - Consistent conditions (indoor preferred)

3. **CP Updates**
   - Recalculate monthly or after training block
   - Track trends over time
   - Expect CP to increase 5-15W per year with training
   - W' more variable, influenced by high-intensity work

4. **Using CP for Training**
   - Base zones on CP, not FTP
   - Threshold work at 95-105% CP
   - VO2max at 110-120% CP
   - Monitor W' depletion in intervals

### For Coaches

1. **Interpreting CP Model**
   - R² > 0.95: Excellent fit, high confidence
   - R² 0.90-0.95: Good fit
   - R² < 0.90: Consider more/better efforts

2. **Programming**
   - Use power curve to identify limiters
   - Prescribe zone work based on CP
   - Monitor W' for interval design
   - Track CP/W' trends for periodization

3. **Race Strategy**
   - Use CP model for pacing plans
   - Calculate W' expenditure for surges
   - Optimize start strategy
   - Plan for final efforts

---

## API Reference

### PowerCurveAnalyzer

```python
class PowerCurveAnalyzer:
    def generate_power_curve(
        self,
        athlete_name: str,
        activities_data: list[dict],
        metric_type: PowerMetric,
        sport_type: str = "cycling",
    ) -> PowerCurve:
        """Generate complete power curve from activities."""

    def calculate_critical_power(
        self,
        best_efforts: list[BestEffort],
        metric_type: PowerMetric,
    ) -> CriticalPower | None:
        """Calculate CP using 2-parameter model."""

    def generate_training_zones(
        self, cp_model: CriticalPower
    ) -> TrainingZones:
        """Generate 6 training zones from CP."""

    def create_fitness_signature(
        self,
        power_curve: PowerCurve,
        cp_model: CriticalPower | None = None,
    ) -> FitnessSignature:
        """Create fitness signature with profile classification."""

    def identify_limiters(
        self, power_curve: PowerCurve, fitness_signature: FitnessSignature
    ) -> dict[str, Any]:
        """Identify performance limiters."""

    def predict_race_performance(
        self,
        cp_model: CriticalPower,
        race_duration_seconds: int,
        w_prime_usage_pct: float = 100.0,
    ) -> dict[str, float]:
        """Predict sustainable power for race."""
```

---

## References

1. Monod, H., & Scherrer, J. (1965). "The work capacity of a synergic muscular group." *Ergonomics*, 8(3), 329-338.

2. Jones, A. M., et al. (2010). "The 'Critical Power' Concept: Applications to Sports Performance." *International Journal of Sports Physiology and Performance*, 5(3), 298-304.

3. Skiba, P. F., et al. (2012). "Modeling the expenditure and reconstitution of work capacity above critical power." *Medicine & Science in Sports & Exercise*, 44(8), 1526-1532.

4. Karsten, B., et al. (2015). "The effects of intensity on the accuracy of the critical power model." *International Journal of Sports Physiology and Performance*, 10(5), 547-552.

5. Coggan, A. R., & Allen, H. (2010). *Training and Racing with a Power Meter* (2nd ed.). VeloPress.

---

## Support

For questions or issues:
- **GitHub Issues**: https://github.com/leonzzz435/garmin-ai-coach/issues
- **Documentation**: https://github.com/leonzzz435/garmin-ai-coach#readme
- **Examples**: See `tests/test_power_curve.py` for usage examples
