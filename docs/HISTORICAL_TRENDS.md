# Historical Trends Analysis Feature

## Overview

The **Historical Trends Analysis** feature provides comprehensive multi-year performance tracking and analysis for endurance athletes. It identifies long-term trends, seasonal patterns, year-over-year comparisons, and generates strategic recommendations based on your training trajectory.

## Features

### ✅ Multi-Metric Trend Analysis
- **Performance Metrics** - VO2max, FTP, pace, power
- **Recovery Metrics** - HRV, resting HR, sleep quality
- **Load Metrics** - Weekly training volume, intensity distribution
- **Wellbeing Metrics** - Stress, fatigue, readiness scores

### ✅ Statistical Trend Detection
- **Linear Regression** - Identifies trend direction and strength
- **R-squared Confidence** - Measures reliability of trend analysis
- **Change Percentage** - Quantifies improvement or decline
- **Baseline vs Current** - Tracks progress from starting point

### ✅ Seasonal Pattern Identification
- **Month-by-Month Analysis** - Identifies performance peaks and declines
- **Winter/Summer Patterns** - Detects seasonal variations
- **Peak Performance Windows** - Finds optimal training periods
- **Climate Impact** - Understands environmental effects

### ✅ Year-over-Year Comparisons
- **Annual Progress Tracking** - Compares performance across years
- **Growth Rate Analysis** - Measures year-to-year improvement
- **Consistency Evaluation** - Assesses training stability
- **Long-term Trajectory** - Projects future performance

### ✅ Interactive Visualizations
- **Trend Line Charts** - Visual representation with regression lines
- **Seasonal Bar Charts** - Month-by-month performance comparison
- **Year-over-Year Graphs** - Annual performance evolution
- **Multi-Panel Dashboards** - Comprehensive trajectory view

### ✅ Strategic Recommendations
Automatic generation of actionable insights:
- **Improving Trends**: Maintain current approach, consider progression
- **Declining Trends**: Identify causes, adjust training/recovery
- **Seasonal Strategies**: Optimize training for time of year
- **Load Management**: Balance volume and intensity

---

## Architecture

### Core Components

```
services/ai/trends/
├── trends_models.py      # Data structures and enums
├── trends_analyzer.py    # Trend analysis engine
├── trends_plotter.py     # Visualization generation
└── __init__.py          # Public interface
```

### Data Flow

```
Historical Data (Garmin/CSV)
    ↓
TrendsAnalyzer
    ↓
Statistical Analysis
    ├── Linear Regression
    ├── Seasonal Grouping
    └── Year-over-Year Comparison
    ↓
PerformanceTrajectory
    ↓
TrendsPlotter → Interactive Visualizations
```

---

## Usage

### Programmatic Usage

#### Basic Trend Analysis

```python
from datetime import datetime, timedelta
from services.ai.trends import TrendsAnalyzer, MetricType

# Create analyzer
analyzer = TrendsAnalyzer()

# Prepare data points (from Garmin or other source)
vo2max_data = [
    {"timestamp": datetime(2023, 1, 15), "value": 52.5},
    {"timestamp": datetime(2023, 2, 15), "value": 53.1},
    {"timestamp": datetime(2023, 3, 15), "value": 53.8},
    # ... more data points
]

# Analyze single metric
trend = analyzer.analyze_metric_trend(
    metric_name="VO2max",
    metric_type=MetricType.PERFORMANCE,
    data_points=vo2max_data,
    higher_is_better=True
)

# View results
print(f"Direction: {trend.direction.value}")
print(f"Change: {trend.change_percentage:.1f}%")
print(f"Confidence (R²): {trend.r_squared:.3f}")
print(f"Interpretation: {trend.interpretation}")
print("\nRecommendations:")
for rec in trend.recommendations:
    print(f"  - {rec}")
```

#### Multi-Metric Performance Trajectory

```python
from services.ai.trends import TrendsAnalyzer, MetricType

analyzer = TrendsAnalyzer()

# Prepare multi-metric data
metrics_data = {
    "VO2max": {
        "data_points": vo2max_data,
        "metric_type": MetricType.PERFORMANCE,
        "higher_is_better": True,
    },
    "Resting HR": {
        "data_points": rhr_data,
        "metric_type": MetricType.RECOVERY,
        "higher_is_better": False,
    },
    "HRV": {
        "data_points": hrv_data,
        "metric_type": MetricType.RECOVERY,
        "higher_is_better": True,
    },
    "Training Load": {
        "data_points": load_data,
        "metric_type": MetricType.LOAD,
        "higher_is_better": True,
    },
}

# Generate complete trajectory
trajectory = analyzer.generate_performance_trajectory(
    athlete_name="John Doe",
    metrics_data=metrics_data,
    analysis_period_years=2
)

# Access results
print(f"Athlete: {trajectory.athlete_name}")
print(f"Analysis Period: {trajectory.analysis_period_years} years")
print(f"Overall Direction: {trajectory.overall_direction.value}")
print(f"\nMetric Trends:")
for trend in trajectory.metric_trends:
    print(f"  {trend.metric_name}: {trend.direction.value} ({trend.change_percentage:+.1f}%)")

print(f"\nStrategic Recommendations:")
for rec in trajectory.strategic_recommendations:
    print(f"  - {rec}")
```

#### Creating Visualizations

```python
from services.ai.trends import TrendsPlotter

plotter = TrendsPlotter()

# Single metric trend plot
fig = plotter.plot_metric_trend(trend, title="VO2max Progress")
fig.show()  # Display in browser
fig.write_html("vo2max_trend.html")  # Save to file

# Seasonal patterns
seasonal_fig = plotter.plot_seasonal_patterns(
    trajectory.seasonal_patterns[0],
    metric_name="VO2max"
)
seasonal_fig.show()

# Year-over-year comparison
yoy_fig = plotter.plot_year_over_year_comparison(
    trajectory.year_over_year[0],
    metric_name="VO2max"
)
yoy_fig.show()

# Complete dashboard
dashboard = plotter.create_trends_dashboard(trajectory)
for name, fig in dashboard.items():
    fig.write_html(f"{name}.html")
```

---

## Data Models

### TrendAnalysis

Represents analysis of a single metric over time:

```python
@dataclass
class TrendAnalysis:
    metric_name: str              # Name of metric
    metric_type: MetricType       # PERFORMANCE, RECOVERY, LOAD, WELLBEING
    direction: TrendDirection     # IMPROVING, STABLE, DECLINING
    data_points: list[DataPoint]  # Historical data
    baseline_value: float | None  # Starting value
    current_value: float | None   # Most recent value
    change_percentage: float | None  # % change from baseline
    trend_line_slope: float | None   # Linear regression slope
    r_squared: float | None       # Confidence of trend (0-1)
    interpretation: str           # Human-readable analysis
    recommendations: list[str]    # Actionable suggestions
```

### PerformanceTrajectory

Complete multi-year analysis:

```python
@dataclass
class PerformanceTrajectory:
    athlete_name: str
    analysis_period_years: int
    overall_direction: TrendDirection
    metric_trends: list[TrendAnalysis]
    seasonal_patterns: list[SeasonalPattern]
    year_over_year: list[YearOverYearComparison]
    strategic_recommendations: list[str]
```

### SeasonalPattern

Month-by-month performance pattern:

```python
@dataclass
class SeasonalPattern:
    month: int                    # 1-12
    month_name: str              # "January", etc.
    average_value: float         # Mean for this month
    sample_size: int             # Number of data points
    deviation_from_mean: float   # % difference from annual mean
    peak_or_decline: str         # "PEAK", "DECLINE", "NEUTRAL"
```

### YearOverYearComparison

Annual performance comparison:

```python
@dataclass
class YearOverYearComparison:
    year: int
    average_value: float
    sample_size: int
    change_from_previous: float | None  # % change from prior year
```

---

## Analysis Methods

### Trend Detection Algorithm

The analyzer uses linear regression to identify trends:

1. **Data Preparation**
   - Convert timestamps to numeric values (days from start)
   - Remove outliers (optional)
   - Ensure minimum data points (default: 10)

2. **Linear Regression**
   - Fit line: `y = mx + b`
   - Calculate slope (m) and R-squared
   - R² > 0.7: Strong trend
   - R² 0.4-0.7: Moderate trend
   - R² < 0.4: Weak/noisy trend

3. **Direction Classification**
   - Calculate % change: `(current - baseline) / baseline * 100`
   - **IMPROVING**: Change > +2% (considering if higher is better)
   - **DECLINING**: Change < -2%
   - **STABLE**: Change between -2% and +2%

4. **Interpretation Generation**
   - Combine direction, magnitude, and confidence
   - Generate context-specific message
   - Provide actionable recommendations

### Seasonal Pattern Detection

Identifies consistent monthly variations:

1. **Group by Month**
   - Aggregate all data points by calendar month
   - Calculate monthly averages

2. **Compare to Annual Mean**
   - Compute overall mean across all months
   - Calculate deviation for each month

3. **Classify Patterns**
   - **PEAK**: >10% above mean
   - **DECLINE**: >10% below mean
   - **NEUTRAL**: Within ±10% of mean

4. **Identify Trends**
   - Winter decline (Dec-Feb)
   - Summer peak (Jun-Aug)
   - Transition periods

### Year-over-Year Analysis

Tracks annual progress:

1. **Group by Year**
   - Separate data into calendar years
   - Calculate annual averages

2. **Compare Adjacent Years**
   - Compute % change from previous year
   - Track consistency of improvement

3. **Trend Projection**
   - Identify acceleration/deceleration
   - Predict future trajectory

---

## Interpretation Guide

### Trend Directions

#### IMPROVING
**Performance Metrics** (VO2max, FTP, Pace):
- Indicates successful training adaptations
- Continue current approach with progressive overload
- Monitor for plateaus

**Recovery Metrics** (HRV up, RHR down):
- Excellent recovery and adaptation
- Body handling training stress well
- Can sustain or increase load

**Load Metrics** (increasing volume/intensity):
- Progressive overload achieved
- Monitor fatigue and recovery
- Plan deload weeks

#### DECLINING
**Performance Metrics**:
- ⚠️ Potential overtraining or inadequate recovery
- Review training volume and intensity
- Increase recovery time
- Check nutrition and sleep

**Recovery Metrics** (HRV down, RHR up):
- ⚠️ Accumulated fatigue
- Reduce training load immediately
- Focus on recovery protocols
- Consider medical consultation

**Load Metrics** (decreasing):
- May indicate injury, illness, or lifestyle changes
- Assess if intentional taper or unplanned reduction

#### STABLE
**Any Metric**:
- Maintenance phase or plateau
- May need new training stimulus
- Consider periodization changes
- Could be appropriate for off-season

### R-squared (Confidence) Interpretation

- **R² > 0.8**: Very strong trend, high confidence
- **R² 0.6-0.8**: Strong trend, good confidence
- **R² 0.4-0.6**: Moderate trend, some noise
- **R² 0.2-0.4**: Weak trend, high variability
- **R² < 0.2**: Very noisy, trend unreliable

### Seasonal Pattern Examples

**Classic Endurance Athlete**:
- Winter (Dec-Feb): 5-10% below average (indoor training, weather)
- Spring (Mar-May): Near average (building fitness)
- Summer (Jun-Aug): 5-10% above average (peak season, races)
- Fall (Sep-Nov): Near average (transition)

**Southern Hemisphere**:
- Inverse pattern (winter = Jun-Aug)

**Indoor Cyclist**:
- Minimal seasonal variation
- Slight winter improvement (more indoor training)

---

## Integration with Garmin AI Coach

The trends feature integrates seamlessly with the main coach workflow:

### Data Sources

1. **Garmin Connect API**
   - Automatically fetch historical data
   - Update trends with new activities
   - Access health snapshots (HRV, RHR, stress)

2. **Local Data Storage**
   - Cache historical analysis
   - Reduce API calls
   - Enable offline analysis

3. **Manual CSV Import**
   - Support other platforms (Strava, TrainingPeaks)
   - Custom metrics
   - Historical data migration

### Workflow Integration

```python
# In main coach workflow
from services.ai.trends import TrendsAnalyzer

# During analysis, include historical context
trends_analyzer = TrendsAnalyzer()
trajectory = trends_analyzer.generate_performance_trajectory(
    athlete_name=user.name,
    metrics_data=garmin_data,
    analysis_period_years=2
)

# Use trends to inform recommendations
if trajectory.overall_direction == TrendDirection.DECLINING:
    # Prioritize recovery recommendations
    ...
elif trajectory.overall_direction == TrendDirection.IMPROVING:
    # Consider progressive overload
    ...
```

---

## Best Practices

### For Athletes

1. **Data Quality**
   - Ensure consistent data recording
   - Use same devices/methods over time
   - Aim for at least 1-2 years of data
   - More data = more reliable trends

2. **Interpretation Context**
   - Consider life changes (injury, illness, job change)
   - Account for intentional training cycles
   - Don't panic over short-term fluctuations
   - Focus on 6-12 month trends

3. **Action on Insights**
   - Use recommendations to adjust training
   - Address declining recovery metrics promptly
   - Leverage seasonal patterns for race planning
   - Track interventions to see what works

4. **Regular Analysis**
   - Review trends monthly or quarterly
   - Update analysis after major training blocks
   - Compare predictions to actual outcomes
   - Adjust based on new data

### For Coaches

1. **Athlete Communication**
   - Share visualizations with athletes
   - Explain R-squared confidence levels
   - Discuss strategic recommendations together
   - Set realistic expectations based on trends

2. **Training Periodization**
   - Align training phases with seasonal patterns
   - Use trends to validate program effectiveness
   - Adjust based on trajectory analysis
   - Plan recovery blocks when trends decline

3. **Individualization**
   - Each athlete has unique patterns
   - Compare trends across similar athletes
   - Identify responders vs non-responders
   - Customize based on trend data

4. **Long-term Planning**
   - Use year-over-year data for goal setting
   - Project realistic race performance
   - Identify optimal competition windows
   - Plan multi-year development

---

## Example Analysis Output

### Improving VO2max Trend

```
Metric: VO2max
Direction: IMPROVING
Baseline: 52.3 ml/kg/min (Jan 2023)
Current: 56.8 ml/kg/min (Dec 2024)
Change: +8.6%
Trend Confidence (R²): 0.847

Interpretation:
Strong positive trend in VO2max over the past 2 years. The high R-squared
value (0.847) indicates consistent improvement with minimal volatility.
This represents excellent aerobic adaptation to training.

Recommendations:
- Continue current training approach - it's working well
- Consider progressive overload to maintain improvement rate
- Monitor for plateau - may need new stimulus in 3-6 months
- Excellent foundation for race-specific training
```

### Seasonal Pattern Example

```
VO2max Seasonal Patterns (2022-2024):

January:   54.2 ml/kg/min  (-3.2% from mean)  ❄️  DECLINE
February:  54.8 ml/kg/min  (-2.1% from mean)  ❄️  DECLINE
March:     55.6 ml/kg/min  (-0.7% from mean)  🌱  NEUTRAL
April:     56.1 ml/kg/min  (+0.2% from mean)  🌱  NEUTRAL
May:       56.8 ml/kg/min  (+1.4% from mean)  🌱  NEUTRAL
June:      58.2 ml/kg/min  (+3.9% from mean)  ☀️  PEAK
July:      58.9 ml/kg/min  (+5.2% from mean)  ☀️  PEAK
August:    58.4 ml/kg/min  (+4.3% from mean)  ☀️  PEAK
September: 56.9 ml/kg/min  (+1.6% from mean)  🍂  NEUTRAL
October:   56.2 ml/kg/min  (+0.4% from mean)  🍂  NEUTRAL
November:  55.4 ml/kg/min  (-1.1% from mean)  🍂  NEUTRAL
December:  54.6 ml/kg/min  (-2.5% from mean)  ❄️  DECLINE

Annual Mean: 56.0 ml/kg/min

Pattern Insights:
- Clear summer peak (June-August): +4-5% above annual average
- Winter decline (December-February): -2-3% below average
- Optimal race windows: June, July, August
- Consider winter base building, summer racing focus
```

---

## Scientific Basis

### Statistical Methods

1. **Linear Regression**
   - Ordinary Least Squares (OLS) regression
   - Measures linear relationship between time and metric
   - Standard method for trend analysis in sports science

2. **Coefficient of Determination (R²)**
   - Measures proportion of variance explained by trend line
   - Values 0-1, higher = better fit
   - Standard goodness-of-fit metric

3. **Seasonal Decomposition**
   - Time series analysis technique
   - Separates trend, seasonal, and residual components
   - Used in epidemiology and sports science

### Research Support

**Training Adaptations**:
- Bouchard et al. (2011): Individual variation in training response
- Variability in VO2max improvements: 0-100% range
- Trends help identify responders vs non-responders

**Seasonal Performance**:
- Ely et al. (2007): Marathon performance declines 1.7% per 5°C increase
- Temperature and humidity affect performance
- Seasonal patterns reflect environmental factors

**Long-term Development**:
- Foster (1998): Training periodization improves performance
- Multi-year tracking essential for elite athletes
- Historical trends predict future potential

**Monitoring and Feedback**:
- Halson (2014): Monitoring training load and recovery
- Trend analysis helps prevent overtraining
- Data-driven decisions improve outcomes

---

## Future Enhancements

### Planned Features

1. **Advanced Statistical Methods**
   - ARIMA time series forecasting
   - Change point detection
   - Anomaly detection algorithms

2. **Machine Learning Integration**
   - Predict future performance trajectory
   - Identify complex patterns
   - Personalized recommendation engine

3. **Comparative Analytics**
   - Compare to age-group norms
   - Peer comparison (anonymized)
   - Elite athlete benchmarks

4. **Automated Alerts**
   - Email/notification when trends change
   - Early warning for declining performance
   - Celebration of milestones

5. **Export and Sharing**
   - PDF reports for coaches
   - Integration with TrainingPeaks/Strava
   - Social sharing of achievements

6. **Multi-Sport Analysis**
   - Sport-specific trends (run vs bike vs swim)
   - Cross-training impact analysis
   - Brick workout trends

---

## Troubleshooting

### Common Issues

**"Insufficient data for reliable analysis"**
- Need at least 10 data points
- Collect more historical data
- Wait for additional activities

**Low R-squared / Noisy trends**
- Inconsistent measurement methods
- High day-to-day variability (normal for some metrics)
- Consider smoothing or longer time windows

**Unexpected seasonal patterns**
- May reflect travel/vacation
- Indoor vs outdoor training differences
- Life circumstances (work schedule changes)

**Declining trends despite good training**
- Check for overtraining symptoms
- Review sleep and nutrition
- Consider stress factors
- May need deload or recovery block

---

## API Reference

### TrendsAnalyzer

```python
class TrendsAnalyzer:
    """Main analysis engine for historical trends."""

    def analyze_metric_trend(
        self,
        metric_name: str,
        metric_type: MetricType,
        data_points: list[dict],
        higher_is_better: bool = True,
    ) -> TrendAnalysis:
        """Analyze trend for a single metric."""

    def identify_seasonal_patterns(
        self,
        data_points: list[dict],
        metric_name: str,
    ) -> list[SeasonalPattern]:
        """Identify month-by-month performance patterns."""

    def compare_years(
        self,
        data_points: list[dict],
        year: int,
        metric_name: str,
    ) -> YearOverYearComparison:
        """Compare performance to previous year."""

    def generate_performance_trajectory(
        self,
        athlete_name: str,
        metrics_data: dict[str, dict],
        analysis_period_years: int,
    ) -> PerformanceTrajectory:
        """Generate complete multi-metric trajectory."""
```

### TrendsPlotter

```python
class TrendsPlotter:
    """Creates interactive visualizations."""

    def plot_metric_trend(
        self,
        trend: TrendAnalysis,
        title: str | None = None,
        show_trendline: bool = True,
    ) -> go.Figure:
        """Create trend line chart."""

    def plot_seasonal_patterns(
        self,
        seasonal_patterns: list[SeasonalPattern],
        metric_name: str,
    ) -> go.Figure:
        """Create seasonal bar chart."""

    def plot_year_over_year_comparison(
        self,
        comparisons: list[YearOverYearComparison],
        metric_name: str,
    ) -> go.Figure:
        """Create year-over-year comparison."""

    def plot_performance_trajectory(
        self,
        trajectory: PerformanceTrajectory,
    ) -> go.Figure:
        """Create multi-panel dashboard."""

    def create_trends_dashboard(
        self,
        trajectory: PerformanceTrajectory,
    ) -> dict[str, go.Figure]:
        """Generate complete dashboard."""
```

---

## References

1. Bouchard, C., et al. (2011). "Genomic predictors of the maximal O2 uptake response to standardized exercise training programs." *Journal of Applied Physiology*, 110(5), 1160-1170.

2. Ely, M. R., et al. (2007). "Impact of weather on marathon-running performance." *Medicine & Science in Sports & Exercise*, 39(3), 487-493.

3. Foster, C. (1998). "Monitoring training in athletes with reference to overtraining syndrome." *Medicine & Science in Sports & Exercise*, 30(7), 1164-1168.

4. Halson, S. L. (2014). "Monitoring training load to understand fatigue in athletes." *Sports Medicine*, 44(Suppl 2), 139-147.

5. Seiler, S., & Tonnessen, E. (2009). "Intervals, thresholds, and long slow distance: the role of intensity and duration in endurance training." *Sportscience*, 13, 32-53.

---

## Support

For questions or issues:
- **GitHub Issues**: https://github.com/leonzzz435/garmin-ai-coach/issues
- **Documentation**: https://github.com/leonzzz435/garmin-ai-coach#readme
- **Examples**: See `tests/test_trends_analyzer.py` for usage examples
