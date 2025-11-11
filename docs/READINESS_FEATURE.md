# Training Readiness Assessment Feature

## Overview

The **Training Readiness Assessment** feature provides athletes with a daily readiness score (0-100) that indicates whether they should rest, train easy, or push hard. This feature analyzes multiple physiological signals to prevent overtraining, optimize recovery, and reduce injury risk.

## What It Does

The readiness calculator integrates seamlessly into your analysis workflow and produces:

1. **Readiness Score (0-100)** - Overall training readiness
2. **Recommendation** - REST, EASY, MODERATE, NORMAL, or PEAK
3. **Signal Analysis** - Breakdown of each physiological indicator
4. **Workout Modifications** - Specific adjustments to your training plan
5. **Confidence Score** - Based on data completeness

## Signals Analyzed

The system evaluates 6 key signals:

### 1. Heart Rate Variability (HRV) - 25% weight
- **Optimal**: Within baseline balanced range
- **Concern**: <15% below baseline (recovery needed)
- **Interpretation**: HRV reflects nervous system recovery status

### 2. Sleep Duration & Quality - 25% weight
- **Optimal**: 7.5+ hours with quality >80/100
- **Concern**: <6 hours or quality <60/100
- **Interpretation**: Sleep is the primary recovery mechanism

### 3. Training Load (ACWR) - 20% weight
- **Optimal**: 0.8-1.3 (safe zone)
- **Concern**: >1.5 (injury risk increases 2x)
- **Interpretation**: Balance between acute and chronic training stress

### 4. Resting Heart Rate - 15% weight
- **Optimal**: Within ±3 bpm of baseline
- **Concern**: >8 bpm above baseline (overtraining/illness)
- **Interpretation**: Elevated RHR indicates systemic stress

### 5. Stress Levels - 10% weight
- **Optimal**: <30 (low stress)
- **Concern**: >70 (high stress impacts recovery)
- **Interpretation**: Life stress compounds training stress

### 6. Workout Quality - 5% weight
- **Optimal**: Recent workouts felt strong
- **Concern**: Consistent struggle indicates fatigue
- **Interpretation**: Subjective feel validates objective data

## Recommendations

### 🚀 PEAK (Score: 85-100)
**Recommendation**: Excellent day for key workouts or races
- All systems showing optimal readiness
- High-quality session opportunity
- Can execute full training intensity

### ✅ NORMAL (Score: 70-84)
**Recommendation**: Proceed with planned training
- Good overall readiness
- Execute workouts as scheduled
- Monitor response during warm-up

### ⚖️ MODERATE (Score: 55-69)
**Recommendation**: Reduce intensity or volume
- Mixed signals suggest caution
- Cut interval volume by 25-30%
- Or reduce intensity by 5-10%
- Extend recovery periods

### 📉 EASY (Score: 40-54)
**Recommendation**: Easy recovery only
- Replace workouts with Zone 1-2
- Keep HR below aerobic threshold
- Prioritize sleep tonight

### 🛑 REST (Score: 0-39)
**Recommendation**: Complete rest or light activity
- Multiple concerning signals
- High injury/illness risk if pushing
- Consider: walk, yoga, or complete rest

## Example Output

```
======================================================================
🎯 TRAINING READINESS ASSESSMENT
======================================================================

Overall Score: 68/100 (MODERATE)
Confidence: 83% (based on available data)

PHYSIOLOGICAL SIGNALS:
----------------------------------------------------------------------
✅ HRV in balanced range (62 ms)
⚠️  Sleep: 6.2h (below target, increased recovery needed)
✅ Training load optimal (ACWR: 1.12, safe zone)
🔴 Resting HR elevated (+8 bpm above baseline, possible overtraining)
⚠️  Stress levels moderate (avg: 52, monitor)

ANALYSIS:
----------------------------------------------------------------------
Readiness score of 68/100 based on 5 signals:
✅ Strong indicators: HRV, Training Load
⚠️  Monitor: Sleep, Stress
🔴 Concerns: Resting HR

Good overall readiness with one concern. Consider reducing training
intensity to avoid overreaching.

TRAINING RECOMMENDATIONS:
----------------------------------------------------------------------
⚖️ MODERATE TRAINING: Reduce intensity of planned workout
Cut interval volume by 25-30% or reduce intensity by 5-10%
Extend recovery periods between intervals
🔴 Elevated RHR: Check for illness/overtraining, consider rest
🟡 Sleep: Target 8+ hours tonight for recovery

======================================================================
```

## Integration

### In Analysis Workflow

The readiness node runs after the expert nodes and before synthesis:

```
Summarizers (parallel) → Experts (parallel) → Readiness → Synthesis → Formatter
```

This ensures:
1. All physiological data is collected
2. Readiness is calculated before synthesis
3. Synthesis agent can incorporate readiness into recommendations

### In Output Files

Readiness assessment is saved to:
- `data/readiness_report.md` - Standalone readiness report
- `data/analysis.html` - Integrated into main analysis (via synthesis)

### In State

The readiness node updates the workflow state with:
```python
{
    "readiness_result": str,  # Formatted report
    "readiness_score": int,   # 0-100
    "readiness_recommendation": str,  # "rest", "easy", etc.
    "readiness_confidence": float,  # 0.0-1.0
}
```

## Usage

### Automatic (Default)

Readiness is calculated automatically for every analysis run:

```bash
pixi run coach-cli --config my_training_config.yaml
```

### Programmatic

```python
from services.ai.readiness import ReadinessCalculator

calculator = ReadinessCalculator()

readiness = calculator.calculate_readiness(
    hrv_last_night=65.0,
    hrv_baseline_balanced_low=60.0,
    hrv_baseline_balanced_upper=70.0,
    sleep_hours=7.5,
    sleep_quality_score=80.0,
    resting_hr=52,
    resting_hr_baseline=52,
    acwr=1.1,
    acute_load=250.0,
    chronic_load=227.0,
    stress_avg=28,
    stress_max=45,
)

print(f"Score: {readiness.score}")
print(f"Recommendation: {readiness.recommendation.value}")

# Format as report
report = calculator.format_readiness_report(readiness)
print(report)
```

## Scientific Basis

### ACWR (Acute:Chronic Workload Ratio)
- **Research**: Gabbett (2016) showed ACWR >1.5 increases injury risk 2-4x
- **Optimal Range**: 0.8-1.3 maintains fitness while minimizing injury risk
- **Source**: British Journal of Sports Medicine

### HRV (Heart Rate Variability)
- **Research**: Plews et al. (2013) - HRV-guided training prevents overtraining
- **Metric**: 7-day rolling average, deviation from baseline
- **Source**: Scandinavian Journal of Medicine & Science in Sports

### Sleep Duration
- **Research**: Milewski et al. (2014) - <8h sleep increases injury risk 1.7x
- **Target**: 7.5-8.5 hours for endurance athletes
- **Source**: Journal of Pediatric Orthopaedics

### Resting Heart Rate
- **Research**: +5-10 bpm elevation indicates overreaching/illness
- **Mechanism**: Sympathetic nervous system overactivation
- **Source**: Exercise & Sport Sciences Reviews

## Data Requirements

### Minimum Required
- At least **2 signals** for calculation
- Confidence score reflects data completeness

### Optimal Data
All 6 signals available:
- HRV data (last night + baseline)
- Sleep duration/quality
- Resting HR (current + baseline)
- Training load (ACWR)
- Stress levels
- Recent workout quality (optional)

### Data Sources
- **Garmin Data**: HRV, sleep, RHR, stress, training load
- **User Input**: Workout quality (future enhancement)
- **Calculated**: ACWR from training status history

## Limitations

1. **Individual Variability**: Baselines differ between athletes
2. **Context Missing**: Doesn't account for life stressors outside Garmin data
3. **Lag Time**: Physiological responses can lag 24-48h
4. **Data Quality**: Requires consistent Garmin device usage
5. **Subjective Factors**: Doesn't capture motivation, mental fatigue

## Best Practices

### For Athletes

1. **Consistency**: Wear Garmin device 24/7 for accurate baselines
2. **Context**: Consider the recommendation but also how you feel
3. **Trends**: Look at patterns over days, not single scores
4. **Override**: You know your body - use readiness as a guide, not a rule
5. **Recovery**: When in doubt, err on the side of rest

### For Coaches

1. **Communication**: Discuss readiness scores with athletes
2. **Flexibility**: Build recovery days into plans based on readiness
3. **Education**: Teach athletes to interpret their signals
4. **Context**: Consider readiness alongside training phase, competition schedule
5. **Individual**: Different athletes respond differently to training stress

## Future Enhancements

### Planned Improvements

1. **Menstrual Cycle Integration** (female athletes)
   - Adjust recommendations based on cycle phase
   - Account for hormonal influences on recovery

2. **Historical Pattern Learning**
   - Machine learning from athlete's past responses
   - Personalized thresholds and recommendations

3. **Subjective Input Integration**
   - Muscle soreness ratings
   - Mood and motivation scores
   - Sleep quality perception

4. **Long-term Trend Analysis**
   - Readiness trends over weeks/months
   - Correlation with performance outcomes
   - Injury prediction modeling

5. **Real-time Notifications**
   - Alert when readiness drops below threshold
   - Proactive rest day recommendations

6. **Comparative Analysis**
   - Compare readiness to training plan demands
   - Auto-adjust workout intensity recommendations

## References

1. Gabbett, T. J. (2016). "The training-injury prevention paradox." British Journal of Sports Medicine, 50(5), 273-280.

2. Plews, D. J., et al. (2013). "Training adaptation and heart rate variability in elite endurance athletes." Scandinavian Journal of Medicine & Science in Sports, 23(6), e353-e362.

3. Milewski, M. D., et al. (2014). "Chronic lack of sleep is associated with increased sports injuries." Journal of Pediatric Orthopaedics, 34(2), 129-133.

4. Buchheit, M. (2014). "Monitoring training status with HR measures." Sports Medicine, 44(Suppl 1), 73-81.

5. Halson, S. L. (2014). "Monitoring training load to understand fatigue." Sports Medicine, 44(Suppl 2), 139-147.

## Support

For questions, issues, or feature requests related to the readiness assessment:

- **GitHub Issues**: https://github.com/leonzzz435/garmin-ai-coach/issues
- **Documentation**: https://github.com/leonzzz435/garmin-ai-coach#readme
- **Examples**: See `tests/test_readiness_calculator.py` for usage examples
