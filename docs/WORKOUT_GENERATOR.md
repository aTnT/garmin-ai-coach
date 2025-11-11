# Workout Generator Feature

## Overview

The **Workout Generator** creates structured, sport-specific training sessions adapted to your current readiness score and training zones. Each workout includes detailed intervals, coaching cues, expected adaptations, and automatic modifications based on your physiological state.

## Features

### ✅ Sport-Specific Workouts
- **Running** - Pace, cadence, and HR-based sessions
- **Cycling** - Power and HR-based sessions
- **Swimming** - Stroke-specific programming
- **Strength** - Functional strength for endurance athletes

### ✅ Workout Types
- **Recovery** - Active recovery, Z1-Z2 only
- **Endurance** - Long steady aerobic work
- **Tempo** - Sustained Z3 efforts
- **Threshold** - Lactate threshold intervals
- **VO2max** - High-intensity aerobic intervals
- **Speed** - Anaerobic/neuromuscular work

### ✅ Automatic Readiness Adaptation
Workouts intelligently modify based on your readiness score:
- **Score < 40 (REST)**: Recommends skipping or converting to very easy session
- **Score 40-54 (EASY)**: Converts to recovery session
- **Score 55-69 (MODERATE)**: Reduces volume/intensity by 25-30%
- **Score 70-84 (NORMAL)**: Proceeds as planned with monitoring cues
- **Score >= 85 (PEAK)**: Full execution encouraged

### ✅ Zone-Based Training
Uses your personal HR zones for accurate targeting:
- **Z1 (50-60% max HR)**: Recovery
- **Z2 (60-70% max HR)**: Endurance/aerobic
- **Z3 (70-80% max HR)**: Tempo
- **Z4 (80-90% max HR)**: Threshold
- **Z5 (90-100% max HR)**: VO2max/anaerobic

---

## Usage

### Command Line Interface

#### Generate a Workout

```bash
# Basic usage
pixi run workout-gen --sport running --type threshold --duration 60

# With zones and readiness
pixi run workout-gen --sport cycling --type vo2max --duration 90 \
    --hr-max 185 --lthr 168 --readiness 78

# With terrain and output
pixi run workout-gen --sport running --type endurance --duration 120 \
    --terrain hilly --output-dir ./my-workouts --format markdown
```

#### Get Help

```bash
pixi run workout-help
```

### Programmatic Usage

```python
from services.ai.workouts import WorkoutGenerator, Sport, WorkoutType

# Create generator
generator = WorkoutGenerator()

# Generate workout
workout = generator.generate_workout(
    sport=Sport.RUNNING,
    workout_type=WorkoutType.THRESHOLD,
    duration_minutes=60,
    athlete_zones={
        "hr_max": 190,
        "lthr": 173
    },
    readiness_score=85
)

# Output as markdown
print(workout.to_markdown())

# Save to file
with open("my_workout.md", "w") as f:
    f.write(workout.to_markdown())

# Convert to dict for JSON
import json
with open("my_workout.json", "w") as f:
    json.dump(workout.to_dict(), f, indent=2)
```

---

## Workout Structure

Every generated workout includes:

### 1. **Metadata**
- Workout ID (unique identifier)
- Name and description
- Sport and workout type
- Target duration
- Average and peak intensity zones
- Goal and focus

### 2. **Segments**
Workouts are organized into segments:
- **Warm-up**: Progressive preparation (10-25 min)
- **Main Set**: Core workout focus
- **Cool-down**: Recovery and integration (5-15 min)

### 3. **Intervals**
Each segment contains intervals with:
- Duration and repetitions
- Intensity zone (Z1-Z5)
- Target HR/power/pace ranges
- Rest periods
- Coaching cues

### 4. **Guidance**
- **Expected Adaptations**: What physiological changes to expect
- **Coaching Cues**: Form and execution tips
- **Alternatives if Fatigued**: Modification options
- **Warnings**: Safety considerations

### 5. **Readiness Adaptation**
If readiness score provided:
- Original readiness score
- Specific modifications made
- Rationale for changes

---

## Example Workouts

### Threshold Running Workout

**Generated with:**
```bash
pixi run workout-gen --sport running --type threshold --duration 60 \
    --hr-max 190 --lthr 173 --readiness 85
```

**Output:**
```markdown
# Running Threshold Development

**Sport:** Running
**Type:** Threshold
**Duration:** 60 minutes
**Average Intensity:** Zone Z3

**Goal:** Improve lactate threshold and sustainable pace

🎯 **Adapted for Your Readiness**
Original readiness score: 85/100
- 🚀 Readiness 85/100 is excellent! Great day for this quality session.
- Full execution possible - embrace the opportunity

## Workout Structure

### Warm-up (20 min)
*Progressive preparation*

**15 min**
- Zone: Z2
- Progressive warm-up
- Target HR: <133 bpm

**1 min (3x)**
- Zone: Z4
- Threshold strides
- Recovery: 1 min
- 💡 *Get legs ready for threshold work*

### Threshold Intervals (32 min)
*4x 8min at threshold*

**8 min (4x)**
- Zone: Z4
- Threshold effort at 164-177 bpm
- Target HR: 164-177 bpm
- Recovery: 2 min
- 💡 *Sustainable hard effort - could hold 20-30 minutes if continuous*

### Cool-down (10 min)

**10 min**
- Zone: Z1
- Easy cool-down
- Target HR: <124 bpm

## Expected Adaptations
- Improved lactate clearance capacity
- Enhanced sustainable race pace
- Increased aerobic power at threshold
- Better mental resilience at high efforts

## Coaching Cues
- First interval should feel 'comfortably hard'
- Hold consistent effort across all intervals
- If HR drifts >5 bpm above target, ease off slightly
- Focus on smooth, efficient form
- Recovery should be active but very easy

## Alternatives if Fatigued
- Reduce to 3x 8min
- Keep 4 intervals but reduce to 6min each
- Lower target HR by 5 bpm

## ⚠️ Important Notes
- High-quality session - requires good readiness
- Skip if feeling unwell or overly fatigued
- Full recovery needed before next hard session (48-72h)
```

### Recovery Workout (Low Readiness Adaptation)

**Generated with readiness score of 45:**
```bash
pixi run workout-gen --sport running --type threshold --duration 60 \
    --hr-max 190 --readiness 45
```

**Result:**
- Automatically **converted to recovery session**
- Reduced to 45 minutes
- All Z1 intensity
- Warning about original plan being too demanding

---

## Workout Types in Detail

### Recovery Workout
**Purpose:** Active recovery without stress
**Duration:** 30-60 minutes
**Intensity:** Z1-Z2 only
**Structure:**
- Continuous easy effort
- No intervals or structure
- Focus on form and relaxation

**Use When:**
- Day after hard session
- Active rest day
- Readiness < 55

### Endurance Workout
**Purpose:** Build aerobic base
**Duration:** 60-180 minutes
**Intensity:** Primarily Z2
**Structure:**
- Short warm-up (10-15 min)
- Long steady effort
- No cool-down needed

**Use When:**
- Building base fitness
- Long run/ride days
- Readiness 70+

### Tempo Workout
**Purpose:** Improve aerobic power
**Duration:** 60-90 minutes
**Intensity:** Sustained Z3
**Structure:**
- 15 min warm-up
- 20-40 min tempo block
- 10 min cool-down

**Use When:**
- Mid-week quality session
- Race-pace endurance
- Readiness 75+

### Threshold Workout
**Purpose:** Improve lactate threshold
**Duration:** 50-70 minutes
**Intensity:** Intervals at Z4
**Structure:**
- 20 min warm-up with strides
- 3-4x 5-8 min at threshold
- 2-3 min recovery between
- 10 min cool-down

**Use When:**
- Key quality session
- 10k-Half Marathon prep
- Readiness 80+

### VO2max Workout
**Purpose:** Increase maximal aerobic capacity
**Duration:** 60-90 minutes
**Intensity:** Hard intervals at Z5
**Structure:**
- 20-25 min warm-up with surges
- 5-6x 3-4 min hard efforts
- 2-3 min easy recovery
- 10 min cool-down

**Use When:**
- Peak fitness development
- 5k-10k race prep
- Readiness 85+
- 72h+ since last hard session

### Speed Workout
**Purpose:** Neuromuscular power and speed
**Duration:** 50-70 minutes
**Intensity:** Very fast, near-max efforts
**Structure:**
- 25 min progressive warm-up
- 8-12x 30-90 sec very fast
- 3-4 min full recovery
- 10 min cool-down

**Use When:**
- Race sharpening
- Pre-competition phase
- Readiness 85+
- Fresh legs (no recent hard sessions)

---

## Integration with Readiness

The workout generator seamlessly integrates with the readiness assessment system:

### Automatic Adaptation

```python
from services.ai.readiness import ReadinessCalculator
from services.ai.workouts import WorkoutGenerator, Sport, WorkoutType

# Calculate readiness
calc = ReadinessCalculator()
readiness = calc.calculate_readiness(
    hrv_last_night=65.0,
    hrv_baseline_balanced_low=60.0,
    hrv_baseline_balanced_upper=70.0,
    sleep_hours=7.5,
    resting_hr=52,
    resting_hr_baseline=52,
    acwr=1.1
)

# Generate adapted workout
generator = WorkoutGenerator()
workout = generator.generate_workout(
    sport=Sport.RUNNING,
    workout_type=WorkoutType.THRESHOLD,
    duration_minutes=60,
    readiness_score=readiness.score
)

print(f"Original plan: {WorkoutType.THRESHOLD.value}")
print(f"Adapted plan: {workout.workout_type.value}")
print(f"Modifications: {workout.readiness_modifications}")
```

### Adaptation Logic

| Readiness Score | Recommendation | Workout Modification |
|----------------|---------------|---------------------|
| 0-39 (REST) | Skip session | Warning added, suggest complete rest |
| 40-54 (EASY) | Convert to recovery | → Recovery session, Z1-Z2 only, reduced duration |
| 55-69 (MODERATE) | Reduce intensity | -25-30% volume, +30% recovery time, lower zones |
| 70-84 (NORMAL) | Proceed carefully | No changes, add monitoring cues |
| 85-100 (PEAK) | Full execution | Encouragement added, optimal day for quality |

---

## Best Practices

### For Athletes

1. **Use Readiness Integration**
   - Always provide readiness score when generating workouts
   - Trust the adaptation recommendations
   - Better to underdo than overdo

2. **Zone Accuracy**
   - Update HR max regularly (field test or lab test)
   - Know your LTHR (20-30 min time trial)
   - Use recent race data for calibration

3. **Progressive Loading**
   - Start with recovery/endurance workouts
   - Add one quality session per week
   - Build to 2-3 quality sessions over months

4. **Listen to Your Body**
   - Workout generator provides template
   - Adjust during warm-up based on feel
   - Stop if form degrades or pain occurs

5. **Recovery Protocol**
   - 48-72h between threshold+ workouts
   - Easy day after hard day
   - Deload every 3-4 weeks (reduce volume 30-50%)

### For Coaches

1. **Customize Templates**
   - Modify duration based on athlete level
   - Adjust volume for experience (beginners: lower)
   - Consider weekly training load

2. **Periodization**
   - Base phase: Primarily endurance/recovery
   - Build phase: Add tempo/threshold
   - Peak phase: Add VO2max/speed
   - Taper: Reduce volume, maintain intensity

3. **Individual Differences**
   - Some athletes respond better to more/less volume
   - Recovery needs vary significantly
   - Adjust based on performance trends

4. **Monitor Trends**
   - Track readiness scores over time
   - Correlate with workout completion quality
   - Adjust plans if chronic low readiness

---

## CLI Options Reference

### Required Arguments

| Option | Description | Example |
|--------|-------------|---------|
| `--sport` | Sport type | `running`, `cycling`, `swimming`, `strength` |
| `--type` | Workout type | `recovery`, `endurance`, `tempo`, `threshold`, `vo2max`, `speed` |
| `--duration` | Duration in minutes | `60`, `90`, `120` |

### Optional Zone Arguments

| Option | Description | Example |
|--------|-------------|---------|
| `--hr-max` | Maximum heart rate (bpm) | `190` |
| `--lthr` | Lactate threshold HR (bpm) | `173` |
| `--ftp` | Functional Threshold Power (watts) | `250` |

### Readiness & Environment

| Option | Description | Example |
|--------|-------------|---------|
| `--readiness` | Current readiness score (0-100) | `75` |
| `--terrain` | Terrain type | `flat`, `rolling`, `hilly`, `mountainous`, `indoor` |
| `--equipment` | Available equipment | `power meter` `heart rate monitor` |

### Output Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output-dir` | Output directory | `./data/workouts` |
| `--format` | Output format | `both` (`markdown`, `json`, `both`) |

---

## Future Enhancements

### Planned Features

1. **Race-Specific Workouts**
   - Generate workouts based on target race distance
   - Progression through training phases
   - Taper protocols

2. **Multi-Week Programs**
   - Generate entire training blocks
   - Automatic periodization
   - Progressive overload management

3. **Brick Workouts**
   - Bike-to-run transitions
   - Multi-sport session design
   - Transition-specific guidance

4. **Advanced Zone Models**
   - Power-based cycling (FTP zones)
   - Pace-based running (threshold pace zones)
   - Swimming CSS (Critical Swim Speed)

5. **Workout Library**
   - Save favorite workouts
   - Tag and search workouts
   - Share workouts with coach/athletes

6. **Integration with Calendar**
   - Export to Garmin/Strava/TrainingPeaks
   - Sync with calendar apps
   - Automatic reminders

---

## Scientific Basis

### Intensity Zone Model

The 5-zone model is based on physiological thresholds:

1. **Zone 1-2 (Aerobic)**: Fat oxidation, mitochondrial development
   - Research: Seiler & Kjerland (2006) - 80/20 training distribution

2. **Zone 3 (Tempo)**: Mixed fuel utilization, aerobic power
   - Research: Esteve-Lanao et al. (2005) - Tempo improves lactate threshold

3. **Zone 4 (Threshold)**: Maximal lactate steady state
   - Research: Billat et al. (2003) - Threshold training improves performance

4. **Zone 5 (VO2max)**: Maximal aerobic capacity development
   - Research: Helgerud et al. (2007) - VO2max intervals improve economy

### Readiness Adaptation

Workout modification based on readiness prevents overtraining:

- **ACWR guidance**: Gabbett (2016) - Injury risk with high acute:chronic ratios
- **HRV-guided training**: Kiviniemi et al. (2007) - HRV-guided training improves performance
- **Fatigue management**: Halson & Jeukendrup (2004) - Monitoring and managing fatigue

### Interval Design

Interval structures based on physiological research:

- **Threshold intervals**: 4-5x 5-10 min (Billat et al., 1999)
- **VO2max intervals**: 4-6x 3-5 min (Helgerud et al., 2007)
- **Speed work**: Short, fast with full recovery (Ross & Leveritt, 2001)

---

## References

1. Seiler, S., & Kjerland, G. Ø. (2006). "Quantifying training intensity distribution in elite endurance athletes." *Scandinavian Journal of Medicine & Science in Sports*, 16(1), 49-56.

2. Billat, V. L., et al. (2003). "Effect of training in humans on off- and on-transient oxygen uptake kinetics after severe exhausting intensity runs." *European Journal of Applied Physiology*, 87(6), 496-505.

3. Helgerud, J., et al. (2007). "Aerobic high-intensity intervals improve VO2max more than moderate training." *Medicine & Science in Sports & Exercise*, 39(4), 665-671.

4. Gabbett, T. J. (2016). "The training-injury prevention paradox." *British Journal of Sports Medicine*, 50(5), 273-280.

5. Kiviniemi, A. M., et al. (2007). "Endurance training guided individually by daily heart rate variability measurements." *European Journal of Applied Physiology*, 101(6), 743-751.

---

## Support

For questions or issues:
- **GitHub Issues**: https://github.com/leonzzz435/garmin-ai-coach/issues
- **Documentation**: https://github.com/leonzzz435/garmin-ai-coach#readme
- **Examples**: See `tests/test_workout_generator.py` for usage examples
