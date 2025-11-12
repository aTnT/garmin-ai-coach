# Dynamic Training Plans Feature

## Overview

The **Dynamic Training Plans** feature provides adaptive, goal-driven training plan generation and management that automatically adjusts based on recent workout execution and athlete readiness.

## Key Features

### ✅ Goal-Based Plan Generation
- **Race Goals**: Define target races with dates, types, and time objectives
- **Periodization**: Automatic phase creation (Base → Build → Peak → Taper)
- **Time-to-Goal Planning**: Smart scheduling based on weeks until race

### ✅ Dynamic Adaptation
- **Readiness-Based**: Automatically adjusts intensity based on HRV, sleep, training load
- **Performance-Based**: Analyzes FTP trends, power curves, interval quality, VO2max
- **Completion Tracking**: Monitors workout execution and completion rates
- **Auto-Rescheduling**: Moves missed key workouts to optimal dates
- **Load Management**: Prevents overtraining via ACWR monitoring
- **Analytical Insights**: GAP pace, zone adherence, HR drift detection

### ✅ Workout-Level Intelligence
- **Context-Aware Selection**: Chooses workouts based on phase, day, readiness
- **Priority System**: KEY, IMPORTANT, BENEFICIAL, OPTIONAL workouts
- **Structured Workouts**: Full interval prescriptions with zones and coaching cues
- **Alternative Options**: Backup workouts for different scenarios

### ✅ Activity Matching
- **Automatic Tracking**: Links Garmin activities to planned workouts
- **Quality Assessment**: EXCELLENT, GOOD, ADEQUATE, POOR, PARTIAL, SKIPPED
- **Adherence Metrics**: Duration, intensity, and completion percentages

### ✅ Plan Storage & Versioning
- **JSON Persistence**: Human-readable plan files
- **Version History**: Automatic backups on changes
- **Archive System**: Completed plans stored separately

---

## Architecture

```
services/ai/planning/
├── plan_models.py          # Data structures
├── plan_storage.py         # Persistence layer
├── activity_matcher.py     # Planned vs. actual matching
├── adaptation_engine.py    # Dynamic adaptation logic
├── performance_analyzer.py # Performance metrics analysis
├── workout_selector.py     # Context-aware workout selection
└── __init__.py            # Public API
```

### Data Flow

```
Race Goals + Current Fitness
    ↓
Training Plan (16 weeks)
    ├── Base Phase (4 weeks)
    ├── Build Phase (8 weeks)
    ├── Peak Phase (2 weeks)
    └── Taper Phase (2 weeks)
    ↓
Weekly Schedule Generation
    ↓
Daily Workout Selection
    ├── Consider: Phase, Day, Readiness, Recent Workouts
    └── Select: Type, Duration, Priority
    ↓
Workout Generator (Structured intervals)
    ↓
Athlete Executes
    ↓
Activity Matcher (Compare planned vs. actual)
    ↓
Adaptation Engine (Trigger on conditions)
    ├── Low Readiness (<60 for 3+ days) → Reduce intensity
    ├── Missed Workouts (<70% completion) → Simplify plan
    ├── High Load (ACWR > 1.5) → Recovery week
    └── Poor Performance → Rebuild foundation
    ↓
Updated Plan (Rolling adaptation)
```

---

## Usage

### CLI Interface

```bash
# Create a new training plan
pixi run plan-create \
  --athlete "Jane Doe" \
  --race-name "Boston Marathon" \
  --race-date "2025-04-21" \
  --weeks 16

# List all active plans
pixi run plan-list

# Show plan details
pixi run plan-show <plan_id>

# View upcoming workouts
pixi run plan-upcoming <plan_id> --days 7

# Check adaptation needs
pixi run plan-adapt <plan_id>

# Apply adaptation
pixi run plan-adapt <plan_id> --execute

# Export to JSON
pixi run plan export <plan_id> --output plan.json
```

### Programmatic Usage

#### Create a Training Plan

```python
from datetime import date, timedelta
from services.ai.planning import (
    TrainingPlan,
    create_base_phase,
    create_build_phase,
    create_peak_phase,
    create_taper_phase,
)

# Define race goal
race_date = date(2025, 4, 21)
start_date = race_date - timedelta(weeks=16)

# Create phases
phases = [
    create_base_phase(start_date, duration_weeks=4),
    create_build_phase(start_date + timedelta(weeks=4), duration_weeks=8),
    create_peak_phase(start_date + timedelta(weeks=12), duration_weeks=2),
    create_taper_phase(start_date + timedelta(weeks=14), duration_weeks=2),
]

# Create plan
plan = TrainingPlan(
    plan_id="plan-001",
    athlete_id="athlete1",
    athlete_name="Jane Doe",
    created_date=datetime.now(),
    start_date=start_date,
    end_date=race_date,
    last_updated=datetime.now(),
    primary_goal={
        "name": "Boston Marathon",
        "date": race_date.isoformat(),
        "race_type": "Marathon",
        "priority": "A",
        "target_time": "sub 3:00",
    },
    phases=phases,
)
```

#### Save and Load Plans

```python
from services.ai.planning import PlanStorage

storage = PlanStorage("./training_plans")

# Save plan
storage.save_plan(plan)

# Load plan
loaded_plan = storage.load_plan("plan-001")

# Load active plan for athlete
active_plan = storage.load_active_plan("athlete1")

# List all plans
summaries = storage.list_active_plans()
for summary in summaries:
    print(f"{summary.athlete_name}: {summary.primary_goal_name}")
```

#### Generate Weekly Schedule

```python
from services.ai.planning import WorkoutSelector
from services.ai.workouts.workout_models import Sport

selector = WorkoutSelector()

# Get current phase from plan
current_phase = plan.current_phase

# Generate week's workouts
schedule = selector.select_weekly_schedule(
    phase=current_phase,
    week_start_date=date.today(),
    average_readiness=75,
    available_days=["Monday", "Wednesday", "Friday", "Saturday", "Sunday"],
    sport=Sport.RUNNING,
)

# Each day contains:
for day in schedule:
    print(f"{day['date']}: {day['workout_type'].value}")
    print(f"  Duration: {day['duration_minutes']} min")
    print(f"  Priority: {day['priority'].value}")
```

#### Match Activities to Workouts

```python
from services.ai.planning import ActivityMatcher
from services.garmin.client import GarminClient

# Get activities from Garmin
garmin = GarminClient()
activities = garmin.get_activities(days=7)

# Match to planned workouts
matcher = ActivityMatcher()
current_week = plan.current_week

completions = matcher.match_activities_to_week(
    planned_workouts=current_week.planned_workouts,
    activities=activities,
)

# View completion quality
for completion in completions:
    print(f"Workout: {completion.planned_workout_id}")
    print(f"  Quality: {completion.quality_rating.value}")
    print(f"  Completion: {completion.completion_percentage:.1f}%")
    print(f"  Duration Adherence: {completion.duration_adherence:.2f}")
    print(f"  Intensity Adherence: {completion.intensity_adherence:.2f}")
```

#### Check Adaptation Needs (Basic)

```python
from services.ai.planning import AdaptationEngine

engine = AdaptationEngine(sensitivity=1.0)

# Get readiness history (from readiness calculator)
readiness_history = [
    (date.today() - timedelta(days=i), readiness_scores[i])
    for i in range(7)
]

# Check if plan needs adaptation
should_adapt, trigger, details = engine.should_adapt_plan(
    plan=plan,
    readiness_history=readiness_history,
    recent_acwr=1.2,
)

if should_adapt:
    print(f"Adaptation needed: {trigger.value}")
    print(f"Reason: {details}")

    # Apply adaptation
    decision = engine.adapt_upcoming_workouts(
        plan=plan,
        trigger=trigger,
        trigger_details=details,
        readiness_score=65,
        days_ahead=7,
    )

    print(f"Adapted {len(decision.affected_workouts)} workouts")
    print(f"Reasoning: {decision.reasoning}")
```

#### Enhanced Adaptation with Performance Analysis

```python
from services.ai.planning import AdaptationEngine, PerformanceAnalyzer
from services.garmin.client import GarminClient

engine = AdaptationEngine(sensitivity=1.0)
garmin = GarminClient()

# Get readiness history
readiness_history = [
    (date.today() - timedelta(days=i), readiness_scores[i])
    for i in range(7)
]

# Get recent activities with power/HR data
recent_activities = garmin.get_activities(days=28)
historical_activities = garmin.get_activities(days=90)

# Enhanced adaptation check using performance metrics
should_adapt, trigger, details, perf_metrics = engine.should_adapt_plan_enhanced(
    plan=plan,
    readiness_history=readiness_history,
    recent_activities=recent_activities,
    historical_activities=historical_activities,
    recent_acwr=1.2,
)

# View performance insights
if perf_metrics:
    print(f"Performance Direction: {perf_metrics.performance_direction}")
    print(f"Confidence: {perf_metrics.confidence:.1%}")

    if perf_metrics.current_ftp:
        print(f"Current FTP: {perf_metrics.current_ftp:.0f}W")
        print(f"FTP Trend: {perf_metrics.ftp_trend} ({perf_metrics.ftp_change_pct:+.1f}%)")

    print(f"Interval Adherence: {perf_metrics.avg_interval_adherence:.1%}")
    print(f"Zone Drift Score: {perf_metrics.zone_drift_score:.2f}")

if should_adapt:
    print(f"\n⚠️ Adaptation needed: {trigger.value}")
    print(f"Reason: {details}")

    # Apply adaptation
    decision = engine.adapt_upcoming_workouts(
        plan=plan,
        trigger=trigger,
        trigger_details=details,
        readiness_score=65,
        days_ahead=7,
    )

    print(f"Adapted {len(decision.affected_workouts)} workouts")
```

#### Analyze Performance Metrics Directly

```python
from services.ai.planning import PerformanceAnalyzer
from services.garmin.client import GarminClient

analyzer = PerformanceAnalyzer()
garmin = GarminClient()

# Get activities
recent = garmin.get_activities(days=28)
historical = garmin.get_activities(days=90)

# Analyze performance
metrics = analyzer.analyze_recent_performance(
    recent_activities=recent,
    historical_activities=historical,
)

# View detailed metrics
print("Power Metrics:")
print(f"  5s Power: {metrics.power_5s}W")
print(f"  1min Power: {metrics.power_1min}W")
print(f"  5min Power: {metrics.power_5min}W")
print(f"  20min Power: {metrics.power_20min}W")
print(f"  FTP: {metrics.current_ftp}W ({metrics.ftp_trend})")
print(f"  Critical Power: {metrics.cp}W, W': {metrics.w_prime}J")

print("\nVO2max Metrics:")
print(f"  Current: {metrics.vo2max_current}")
print(f"  Trend: {metrics.vo2max_trend} ({metrics.vo2max_change_pct:+.1f}%)")

print("\nInterval Quality:")
print(f"  Adherence: {metrics.avg_interval_adherence:.1%}")
print(f"  Zone Drift: {metrics.zone_drift_score:.2f}")
print(f"  Consistency: {metrics.consistency_score:.2f}")

# Get adaptation recommendation
should_adapt, reasoning = analyzer.get_adaptation_recommendation(metrics)
print(f"\nRecommendation: {'ADAPT' if should_adapt else 'CONTINUE'}")
print(f"Reasoning: {reasoning}")
```

---

## Data Models

### TrainingPlan

Complete training plan for an athlete.

```python
@dataclass
class TrainingPlan:
    plan_id: str
    athlete_id: str
    athlete_name: str
    start_date: date
    end_date: date
    primary_goal: dict  # Race information
    phases: list[TrainingPhase]
    weekly_schedules: list[WeeklySchedule]
    adaptations: list[AdaptationDecision]
    adaptation_enabled: bool = True
    adaptation_sensitivity: float = 1.0  # 0.5-2.0
```

### TrainingPhase

A period in the plan (Base, Build, Peak, Taper).

```python
@dataclass
class TrainingPhase:
    phase_id: str
    phase_type: TrainingPhaseType
    name: str
    start_date: date
    end_date: date
    focus: str
    volume_range: VolumeRange
    intensity_distribution: IntensityDistribution
    key_workout_types: list[WorkoutType]
    goals: list[str]
```

### PlannedWorkout

A workout in the schedule.

```python
@dataclass
class PlannedWorkout:
    workout_id: str
    date: date
    workout: StructuredWorkout
    priority: WorkoutPriority  # KEY, IMPORTANT, BENEFICIAL, OPTIONAL
    rationale: str
    alternative_workouts: list[StructuredWorkout]
    can_reschedule: bool = True
    completed: bool = False
```

### WorkoutCompletion

Records workout execution.

```python
@dataclass
class WorkoutCompletion:
    planned_workout_id: str
    completed_date: datetime
    activity_id: str
    completion_percentage: float  # 0-100
    duration_adherence: float
    intensity_adherence: float
    quality_rating: CompletionQuality
```

### AdaptationDecision

Records plan adaptation.

```python
@dataclass
class AdaptationDecision:
    adaptation_id: str
    timestamp: datetime
    trigger: AdaptationTrigger
    affected_workouts: list[str]
    reasoning: str
    confidence: float
    requires_approval: bool = False
```

### PerformanceMetrics

Performance analysis results from recent workouts.

```python
class PerformanceMetrics:
    # Power metrics
    current_ftp: float | None
    ftp_trend: str  # "improving", "stable", "declining"
    ftp_change_pct: float
    power_5s: float | None
    power_1min: float | None
    power_5min: float | None
    power_20min: float | None
    power_60min: float | None
    cp: float | None  # Critical Power
    w_prime: float | None  # W' (anaerobic capacity)

    # VO2max metrics
    vo2max_current: float | None
    vo2max_trend: str
    vo2max_change_pct: float

    # Interval quality
    avg_interval_adherence: float  # 0-1
    zone_drift_score: float  # 0-1, 0=no drift
    consistency_score: float  # 0-1

    # Pace metrics (running)
    current_pace_threshold: str | None
    gap_pace_improvement: float  # % change

    # Overall assessment
    performance_direction: str  # "improving", "stable", "declining"
    confidence: float  # 0-1
```

---

## Adaptation Logic

### Adaptation Triggers

#### Basic Triggers

1. **LOW_READINESS**: Average readiness < 60 for 3+ days
   - Action: Convert hard sessions to recovery, reduce volume by 30%

2. **MISSED_WORKOUTS**: <70% completion rate
   - Action: Simplify plan, keep only KEY and IMPORTANT workouts

3. **HIGH_TRAINING_LOAD**: ACWR > 1.5
   - Action: Insert recovery days, reduce intensity

4. **ILLNESS_INJURY**: User-reported (requires approval)

5. **RACE_CHANGE**: Goal date/type changed (requires approval)

#### Performance-Based Triggers (Enhanced Mode)

These triggers use detailed workout analytics:

1. **FTP DECLINING > 5%**
   - Trigger: `POOR_PERFORMANCE`
   - Detection: Compare 4-week FTP to 4-8 week baseline
   - Action: Reduce to tempo intensity, add recovery days
   - Reasoning: Overreaching detected, need recovery period

2. **VO2MAX DECLINING > 3%**
   - Trigger: `POOR_PERFORMANCE`
   - Detection: Compare recent VO2max estimates to baseline
   - Action: Reduce training load, maintain aerobic work
   - Reasoning: Accumulated fatigue affecting aerobic capacity

3. **POOR INTERVAL QUALITY < 70%**
   - Trigger: `POOR_PERFORMANCE`
   - Detection: Zone adherence analysis from HR streams
   - Action: Reduce interval intensity or convert to tempo
   - Reasoning: Athlete struggling to execute prescribed zones

4. **HIGH ZONE DRIFT > 50%**
   - Trigger: `HIGH_TRAINING_LOAD`
   - Detection: HR drift within interval sets (>10% drift = 1.0)
   - Action: Reduce training load, add recovery
   - Reasoning: Accumulated fatigue causing HR drift

5. **PERFORMANCE IMPROVING (Override)**
   - Special case: Continue despite moderate readiness
   - Detection: FTP/VO2max improving with high confidence
   - Action: Override LOW_READINESS trigger, continue as planned
   - Reasoning: Positive adaptation occurring, maintain training stimulus

### Adaptation Strategies

**For Low Readiness:**
- Threshold/VO2max → Recovery
- Endurance → Reduce duration by 30%
- Keep recovery as-is

**For High Load:**
- Add recovery day at start of week
- Convert hard sessions to tempo
- Maintain endurance volume

**For Missed Workouts:**
- Reduce session count
- Focus on key sessions only
- Reschedule important workouts

---

## Performance Analysis Details

### How Performance Metrics Are Calculated

#### Power Curve Analysis

The system uses the existing `PowerCurveAnalyzer` to extract peak powers:

- **5s Power**: Neuromuscular power (sprinting)
- **1min Power**: Anaerobic capacity
- **5min Power**: VO2max power
- **20min Power**: FTP estimate (× 0.95)
- **60min Power**: Threshold endurance

**Critical Power (CP) & W':**
- Calculated from power curve using 2-parameter model
- CP = sustainable power indefinitely
- W' = anaerobic work capacity (joules)

**FTP Trend Detection:**
- Compare recent 4-week FTP to 4-8 week baseline
- >3% increase = "improving"
- <-3% decrease = "declining"
- Otherwise = "stable"

#### VO2max Trend Analysis

From Garmin's VO2max estimates:
- Extract VO2max values from recent activities
- Compare average of 3 most recent to 3 oldest
- >2% = improving, <-2% = declining

#### Interval Quality Analysis

**Interval Detection:**
- Analyzes HR stream to find "hard" segments
- Threshold: HR > 20% above baseline
- Minimum duration: 60 seconds

**Zone Adherence (0-1):**
- Calculates % of interval time in target zone (Z4: 80-90% max HR)
- 1.0 = perfect adherence
- 0.7 = 70% in zone
- <0.7 triggers adaptation

**Zone Drift (0-1):**
- Compares HR in first vs last interval
- Measures cardiovascular drift due to fatigue
- 0.0 = no drift
- >0.5 = significant drift (>10% HR increase)

**Consistency (0-1):**
- Coefficient of variation across intervals
- 1.0 = perfect consistency
- Lower = more variable execution

#### Grade Adjusted Pace (GAP)

For running activities:
```
GAP = base_pace / (1 + elevation_gain_per_km × 0.001)
```

Normalizes pace for hills:
- 100m gain per km = ~10 sec/km adjustment
- Allows fair comparison of hilly vs flat runs
- Used for pace trend analysis

#### Performance Direction

Weighted combination of indicators:
- FTP trend (if available)
- Power curve improvement
- VO2max trend
- Interval quality

**Confidence Score:**
- Based on number of available metrics
- More data sources = higher confidence
- Requires >70% confidence to trigger adaptation

---

## Periodization Guide

### Phase Types

**BASE (4-8 weeks)**
- Focus: Aerobic foundation, volume building
- Intensity: 80% Z1-Z2, 20% Z3-Z4
- Key Workouts: Long endurance (2-4 hours), Tempo (1 hour)
- Volume: 6-10 hours/week

**BUILD (6-10 weeks)**
- Focus: Lactate threshold, race-specific fitness
- Intensity: 60% Z1-Z2, 25% Z3, 15% Z4-Z5
- Key Workouts: Threshold intervals, VO2max, Long runs
- Volume: 10-15 hours/week

**PEAK (2-3 weeks)**
- Focus: Race-specific intensity, sharpening
- Intensity: 50% Z1-Z2, 20% Z3, 30% Z4-Z5
- Key Workouts: Race pace, VO2max, Speed work
- Volume: 8-12 hours/week

**TAPER (1-2 weeks)**
- Focus: Recovery while maintaining sharpness
- Intensity: 60% Z1, 20% Z2-Z3, 20% Z4-Z5 (short)
- Key Workouts: Short openers, Easy runs
- Volume: 4-6 hours/week (50% reduction)

### Weekly Structure Examples

**Base Week:**
- Monday: Rest or easy 45min
- Tuesday: Easy 60min
- Wednesday: Tempo 60min
- Thursday: Easy 45min
- Friday: Rest
- Saturday: Long run 120-180min
- Sunday: Cross-training or easy 45min

**Build Week:**
- Monday: Rest
- Tuesday: Threshold intervals 60min
- Wednesday: Easy 60min
- Thursday: VO2max intervals 45min
- Friday: Easy 45min
- Saturday: Tempo run 75min
- Sunday: Long run 120-150min

---

## Best Practices

### For Athletes

1. **Set Realistic Goals**
   - Choose races 12-20 weeks out
   - Base training on current fitness
   - Allow time for adaptation

2. **Track Readiness**
   - Log sleep, stress, HRV daily
   - Be honest about how you feel
   - Trust the adaptation system

3. **Prioritize Key Workouts**
   - Never skip KEY workouts
   - Reschedule if necessary
   - OPTIONAL workouts can be dropped

4. **Review Adaptations**
   - Understand why plan changed
   - Provide feedback
   - Override if needed

### For Coaches

1. **Customize Phases**
   - Adjust phase duration to athlete
   - Modify intensity distributions
   - Set appropriate volume ranges

2. **Monitor Adaptation Frequency**
   - sensitivity < 1.0 for conservative
   - sensitivity > 1.0 for aggressive
   - Review adaptation history

3. **Use Approval System**
   - Major changes require approval
   - Illness/injury always needs coach input
   - Review automated adaptations weekly

4. **Integrate with LangGraph**
   - Use season planner for strategic framework
   - Weekly planner for tactical details
   - Workout generator for execution

---

## Future Enhancements

### Planned Features

1. **LangGraph Integration**
   - Connect to existing season/weekly planners
   - Use AI for adaptation reasoning
   - Automatic planning context updates

2. **Continuous Planning**
   - Rolling 14-day window
   - Daily plan refresh
   - Seamless phase transitions

3. **Race Prediction**
   - Estimate finish time from training
   - Pacing strategy generation
   - Confidence intervals

4. **Multi-Sport Support**
   - Triathlon training plans
   - Brick workout integration
   - Sport-specific periodization

5. **Social Features**
   - Share plans with coach
   - Group training coordination
   - Comparative analytics

6. **Advanced Analytics**
   - Training load charts
   - Fitness/fatigue modeling (CTL/ATL/TSB)
   - Performance prediction

---

## API Reference

### PlanStorage

```python
class PlanStorage:
    def __init__(self, storage_dir: str | Path)
    def save_plan(self, plan: TrainingPlan, backup: bool = True) -> Path
    def load_plan(self, plan_id: str) -> TrainingPlan | None
    def load_active_plan(self, athlete_id: str) -> TrainingPlan | None
    def list_active_plans(self) -> list[PlanSummary]
    def archive_plan(self, plan_id: str) -> bool
```

### ActivityMatcher

```python
class ActivityMatcher:
    def __init__(self, matching_window_hours: int = 36)
    def match_activity_to_workout(
        self, planned_workout: PlannedWorkout, activities: list[Activity]
    ) -> WorkoutCompletion | None
    def match_activities_to_week(
        self, planned_workouts: list[PlannedWorkout], activities: list[Activity]
    ) -> list[WorkoutCompletion]
```

### AdaptationEngine

```python
class AdaptationEngine:
    def __init__(self, sensitivity: float = 1.0)

    def should_adapt_plan(
        self, plan: TrainingPlan, readiness_history: list[tuple[date, int]],
        recent_acwr: float | None
    ) -> tuple[bool, AdaptationTrigger | None, str]

    def should_adapt_plan_enhanced(
        self, plan: TrainingPlan, readiness_history: list[tuple[date, int]],
        recent_activities: list[Activity], historical_activities: list[Activity] | None,
        recent_acwr: float | None
    ) -> tuple[bool, AdaptationTrigger | None, str, PerformanceMetrics | None]

    def adapt_upcoming_workouts(
        self, plan: TrainingPlan, trigger: AdaptationTrigger, trigger_details: str,
        readiness_score: int | None, days_ahead: int = 7
    ) -> AdaptationDecision
```

### PerformanceAnalyzer

```python
class PerformanceAnalyzer:
    def __init__(self)

    def analyze_recent_performance(
        self, recent_activities: list[Activity],
        historical_activities: list[Activity] | None = None,
        lookback_days: int = 28
    ) -> PerformanceMetrics

    def get_adaptation_recommendation(
        self, metrics: PerformanceMetrics
    ) -> tuple[bool, str]
```

### WorkoutSelector

```python
class WorkoutSelector:
    def select_workout_for_day(
        self, day_of_week: str, phase: TrainingPhase, readiness_score: int,
        days_since_last_hard: int, days_to_race: int | None = None
    ) -> tuple[WorkoutType, int, WorkoutPriority]
    def select_weekly_schedule(
        self, phase: TrainingPhase, week_start_date: date, average_readiness: int,
        available_days: list[str] | None = None, sport: Sport = Sport.RUNNING
    ) -> list[dict[str, Any]]
```

---

## Troubleshooting

**"Plan not adapting when expected"**
- Check `adaptation_enabled` is True
- Review `adaptation_sensitivity` setting
- Verify readiness history has sufficient data

**"Too many adaptations"**
- Reduce sensitivity (try 0.7 or 0.8)
- Check if completion tracking is accurate
- Review adaptation triggers

**"Workouts don't match current fitness"**
- Update phase manually if needed
- Provide recent test results
- Adjust volume ranges in phase

**"Can't find saved plan"**
- Check storage directory path
- Verify plan_id is correct
- Look in archive directory

---

## Support

- **GitHub Issues**: https://github.com/leonzzz435/garmin-ai-coach/issues
- **Examples**: See `tests/test_training_plan.py`
- **CLI Help**: `pixi run plan --help`
