"""
Training Plan CLI

Command-line interface for managing dynamic training plans.
"""

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import json

from services.ai.planning import (
    PlanStorage,
    TrainingPlan,
    create_base_phase,
    create_build_phase,
    create_peak_phase,
    create_taper_phase,
    WorkoutSelector,
    AdaptationEngine,
    ActivityMatcher,
    PerformanceAnalyzer,
)
from services.ai.workouts.workout_models import Sport
from services.garmin.models import Activity


def create_sample_plan(
    athlete_name: str,
    race_date: date,
    race_name: str,
    weeks_before_race: int = 16,
) -> TrainingPlan:
    """
    Create a sample training plan.

    Args:
        athlete_name: Athlete's name
        race_date: Goal race date
        race_name: Name of goal race
        weeks_before_race: Weeks to train before race

    Returns:
        TrainingPlan object
    """
    import uuid

    plan_id = str(uuid.uuid4())[:8]
    start_date = race_date - timedelta(weeks=weeks_before_race)

    # Create phases
    phases = []

    # Base phase (4 weeks)
    base_start = start_date
    phases.append(create_base_phase(base_start, duration_weeks=4, phase_number=1))

    # Build phase (8 weeks)
    build_start = base_start + timedelta(weeks=4)
    phases.append(create_build_phase(build_start, duration_weeks=8, phase_number=1))

    # Peak phase (2 weeks)
    peak_start = build_start + timedelta(weeks=8)
    phases.append(create_peak_phase(peak_start, duration_weeks=2))

    # Taper phase (2 weeks)
    taper_start = peak_start + timedelta(weeks=2)
    phases.append(create_taper_phase(taper_start, duration_weeks=2))

    # Create plan
    plan = TrainingPlan(
        plan_id=plan_id,
        athlete_id=athlete_name.lower().replace(" ", "_"),
        athlete_name=athlete_name,
        created_date=datetime.now(),
        start_date=start_date,
        end_date=race_date,
        last_updated=datetime.now(),
        primary_goal={
            "name": race_name,
            "date": race_date.isoformat(),
            "race_type": "Marathon",
            "priority": "A",
            "target_time": "sub 3:00",
        },
        phases=phases,
        current_phase_id="base_1",
    )

    return plan


def cmd_create(args):
    """Create a new training plan."""
    # Parse race date
    race_date = datetime.strptime(args.race_date, "%Y-%m-%d").date()

    # Create plan
    plan = create_sample_plan(
        athlete_name=args.athlete,
        race_date=race_date,
        race_name=args.race_name,
        weeks_before_race=args.weeks,
    )

    # Save plan
    storage = PlanStorage(args.storage_dir)
    saved_path = storage.save_plan(plan, backup=False)

    print(f"✓ Created training plan: {plan.plan_id}")
    print(f"  Athlete: {plan.athlete_name}")
    print(f"  Goal: {plan.primary_goal['name']} ({plan.primary_goal['date']})")
    print(f"  Duration: {plan.weeks_remaining} weeks")
    print(f"  Phases: {len(plan.phases)}")
    print(f"  Saved to: {saved_path}")


def cmd_list(args):
    """List all active training plans."""
    storage = PlanStorage(args.storage_dir)
    summaries = storage.list_active_plans()

    if not summaries:
        print("No active training plans found.")
        return

    print(f"\nActive Training Plans ({len(summaries)}):\n")

    for summary in summaries:
        print(f"Plan ID: {summary.plan_id}")
        print(f"  Athlete: {summary.athlete_name}")
        print(f"  Goal: {summary.primary_goal_name} (in {summary.days_to_goal} days)")
        print(f"  Phase: {summary.current_phase_name} (Week {summary.current_week_number}/{summary.weeks_total})")
        print(f"  Completion: {summary.overall_completion_rate:.1f}%")
        print(f"  Status: {summary.current_status.value}")
        print()


def cmd_show(args):
    """Show details of a specific plan."""
    storage = PlanStorage(args.storage_dir)
    plan = storage.load_plan(args.plan_id)

    if not plan:
        print(f"Error: Plan '{args.plan_id}' not found.")
        return

    print(f"\n=== Training Plan: {plan.plan_id} ===\n")
    print(f"Athlete: {plan.athlete_name}")
    print(f"Goal: {plan.primary_goal['name']}")
    print(f"Race Date: {plan.primary_goal['date']} ({plan.days_to_goal} days)")
    print(f"Duration: {plan.start_date} to {plan.end_date}")
    print(f"\nPhases ({len(plan.phases)}):")

    for phase in plan.phases:
        status = "→ ACTIVE" if phase.is_active else ""
        print(f"  • {phase.name}: {phase.start_date} to {phase.end_date} {status}")
        print(f"    Focus: {phase.focus}")
        print(f"    Volume: {phase.volume_range.target_hours_per_week}h/week")

    print(f"\nProgress:")
    print(f"  Completion Rate: {plan.overall_completion_rate:.1f}%")
    print(f"  Adaptations Made: {len(plan.adaptations)}")

    if plan.current_week:
        print(f"\nCurrent Week:")
        print(f"  Week {plan.current_week.week_number}: {plan.current_week.start_date} to {plan.current_week.end_date}")
        print(f"  Planned Workouts: {len(plan.current_week.planned_workouts)}")
        print(f"  Completed: {plan.current_week.completion_rate:.1f}%")


def cmd_upcoming(args):
    """Show upcoming workouts."""
    storage = PlanStorage(args.storage_dir)
    plan = storage.load_plan(args.plan_id)

    if not plan:
        print(f"Error: Plan '{args.plan_id}' not found.")
        return

    upcoming = plan.upcoming_workouts(days=args.days)

    if not upcoming:
        print("No upcoming workouts found.")
        return

    print(f"\nUpcoming Workouts (next {args.days} days):\n")

    for workout in upcoming:
        priority_symbol = "🔴" if workout.priority.value == "key" else "🟡" if workout.priority.value == "important" else "🟢"
        print(f"{priority_symbol} {workout.date} ({workout.days_until:+d} days)")
        print(f"   {workout.workout.name}")
        print(f"   Type: {workout.workout.workout_type.value.title()}")
        print(f"   Duration: {workout.workout.duration_minutes} min")
        print(f"   Goal: {workout.workout.goal}")
        print()


def cmd_adapt(args):
    """Check if plan needs adaptation."""
    storage = PlanStorage(args.storage_dir)
    plan = storage.load_plan(args.plan_id)

    if not plan:
        print(f"Error: Plan '{args.plan_id}' not found.")
        return

    # Create adaptation engine
    engine = AdaptationEngine(sensitivity=1.0)

    # Check for adaptation need
    # In real scenario, would get readiness history from Garmin
    readiness_history = [
        (date.today() - timedelta(days=i), 65)
        for i in range(7)
    ]

    should_adapt, trigger, details = engine.should_adapt_plan(
        plan, readiness_history, recent_acwr=None
    )

    if should_adapt:
        print(f"\n⚠️  Plan adaptation recommended")
        print(f"Trigger: {trigger.value if trigger else 'unknown'}")
        print(f"Details: {details}")

        if args.execute:
            print("\nAdapting plan...")
            decision = engine.adapt_upcoming_workouts(
                plan, trigger, details, readiness_score=65, days_ahead=7
            )

            print(f"\nAdaptation Applied:")
            print(f"  Affected Workouts: {len(decision.affected_workouts)}")
            print(f"  Reasoning: {decision.reasoning}")
            print(f"  Confidence: {decision.confidence:.2f}")

            # Save updated plan
            storage.save_plan(plan)
            print(f"\n✓ Plan updated and saved.")
        else:
            print("\nRun with --execute to apply adaptation.")
    else:
        print(f"\n✓ Plan on track - no adaptation needed")
        print(f"Details: {details}")


def cmd_export(args):
    """Export plan to JSON."""
    storage = PlanStorage(args.storage_dir)
    plan = storage.load_plan(args.plan_id)

    if not plan:
        print(f"Error: Plan '{args.plan_id}' not found.")
        return

    # Convert to dict
    plan_dict = storage._plan_to_dict(plan)

    # Write to file
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(plan_dict, f, indent=2, default=str)

    print(f"✓ Plan exported to: {output_path}")


def cmd_analyze(args):
    """Analyze recent performance metrics."""
    from services.garmin.client import GarminConnectClient

    print("Performance Analysis")
    print("=" * 50)

    # Note: In real usage, would connect to Garmin
    # For demo purposes, show what would be analyzed
    if args.demo:
        print("\n📊 Demo Mode - Sample Performance Metrics\n")

        # Create demo metrics
        analyzer = PerformanceAnalyzer()
        from services.ai.planning.performance_analyzer import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.current_ftp = 285.0
        metrics.ftp_trend = "improving"
        metrics.ftp_change_pct = 4.2
        metrics.power_5s = 1250.0
        metrics.power_1min = 450.0
        metrics.power_5min = 320.0
        metrics.power_20min = 300.0
        metrics.power_60min = 280.0
        metrics.cp = 285.0
        metrics.w_prime = 20000.0
        metrics.vo2max_current = 52.5
        metrics.vo2max_trend = "stable"
        metrics.vo2max_change_pct = 0.8
        metrics.avg_interval_adherence = 0.85
        metrics.zone_drift_score = 0.25
        metrics.consistency_score = 0.90
        metrics.performance_direction = "improving"
        metrics.confidence = 0.85

        _print_performance_metrics(metrics)

        # Get recommendation
        should_adapt, reasoning = analyzer.get_adaptation_recommendation(metrics)
        print(f"\n{'⚠️  ADAPT RECOMMENDED' if should_adapt else '✅ CONTINUE AS PLANNED'}")
        print(f"Reasoning: {reasoning}")

    else:
        print("\n⚠️  Garmin integration required for live analysis")
        print("Use --demo flag to see sample output")
        print("\nTo use with real data:")
        print("  1. Ensure Garmin credentials are configured")
        print("  2. Run: plan-analyze --athlete <athlete_id> --days 28")


def _print_performance_metrics(metrics):
    """Print formatted performance metrics."""
    print("Power Metrics:")
    print(f"  FTP: {metrics.current_ftp:.0f}W ({metrics.ftp_trend}, {metrics.ftp_change_pct:+.1f}%)")
    if metrics.power_5s:
        print(f"  5s Power: {metrics.power_5s:.0f}W")
    if metrics.power_1min:
        print(f"  1min Power: {metrics.power_1min:.0f}W")
    if metrics.power_5min:
        print(f"  5min Power: {metrics.power_5min:.0f}W")
    if metrics.power_20min:
        print(f"  20min Power: {metrics.power_20min:.0f}W")
    if metrics.cp:
        print(f"  Critical Power: {metrics.cp:.0f}W, W': {metrics.w_prime:.0f}J")

    print("\nVO2max Metrics:")
    if metrics.vo2max_current:
        print(f"  Current: {metrics.vo2max_current:.1f}")
        print(f"  Trend: {metrics.vo2max_trend} ({metrics.vo2max_change_pct:+.1f}%)")

    print("\nInterval Quality:")
    print(f"  Zone Adherence: {metrics.avg_interval_adherence:.1%}")
    print(f"  Zone Drift: {metrics.zone_drift_score:.2f}")
    print(f"  Consistency: {metrics.consistency_score:.2f}")

    print(f"\nPerformance Direction: {metrics.performance_direction.upper()}")
    print(f"Confidence: {metrics.confidence:.1%}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Training Plan Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "--storage-dir",
        default="./training_plans",
        help="Directory for plan storage (default: ./training_plans)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new training plan")
    create_parser.add_argument("--athlete", required=True, help="Athlete name")
    create_parser.add_argument(
        "--race-name", required=True, help="Goal race name"
    )
    create_parser.add_argument(
        "--race-date", required=True, help="Race date (YYYY-MM-DD)"
    )
    create_parser.add_argument(
        "--weeks", type=int, default=16, help="Weeks before race (default: 16)"
    )
    create_parser.set_defaults(func=cmd_create)

    # List command
    list_parser = subparsers.add_parser("list", help="List active training plans")
    list_parser.set_defaults(func=cmd_list)

    # Show command
    show_parser = subparsers.add_parser("show", help="Show plan details")
    show_parser.add_argument("plan_id", help="Plan ID")
    show_parser.set_defaults(func=cmd_show)

    # Upcoming command
    upcoming_parser = subparsers.add_parser("upcoming", help="Show upcoming workouts")
    upcoming_parser.add_argument("plan_id", help="Plan ID")
    upcoming_parser.add_argument(
        "--days", type=int, default=7, help="Number of days ahead (default: 7)"
    )
    upcoming_parser.set_defaults(func=cmd_upcoming)

    # Adapt command
    adapt_parser = subparsers.add_parser(
        "adapt", help="Check/apply plan adaptations"
    )
    adapt_parser.add_argument("plan_id", help="Plan ID")
    adapt_parser.add_argument(
        "--execute", action="store_true", help="Execute adaptation (not just check)"
    )
    adapt_parser.set_defaults(func=cmd_adapt)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export plan to JSON")
    export_parser.add_argument("plan_id", help="Plan ID")
    export_parser.add_argument(
        "--output", default="plan.json", help="Output file (default: plan.json)"
    )
    export_parser.set_defaults(func=cmd_export)

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze performance metrics"
    )
    analyze_parser.add_argument(
        "--demo", action="store_true", help="Show demo output with sample data"
    )
    analyze_parser.add_argument(
        "--athlete", help="Athlete ID (for live data)"
    )
    analyze_parser.add_argument(
        "--days", type=int, default=28, help="Days of history to analyze (default: 28)"
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    # Parse and execute
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
