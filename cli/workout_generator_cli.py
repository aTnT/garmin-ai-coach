#!/usr/bin/env python3
"""
Workout Generator CLI

Generate structured workouts adapted to your readiness and zones.
"""

import argparse
import json
import logging
from pathlib import Path

from services.ai.readiness import ReadinessCalculator
from services.ai.workouts import (
    Sport,
    Terrain,
    WorkoutGenerator,
    WorkoutType,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Generate structured training workouts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate threshold run
  python workout_generator_cli.py --sport running --type threshold --duration 60

  # Generate with zones and readiness
  python workout_generator_cli.py --sport cycling --type vo2max --duration 90 \\
      --hr-max 185 --lthr 168 --readiness 78

  # Save to file
  python workout_generator_cli.py --sport running --type endurance --duration 120 \\
      --output-dir ./workouts --format markdown
        """,
    )

    # Required arguments
    parser.add_argument(
        "--sport",
        type=str,
        required=True,
        choices=["running", "cycling", "swimming", "strength"],
        help="Sport type",
    )
    parser.add_argument(
        "--type",
        type=str,
        required=True,
        choices=["recovery", "endurance", "tempo", "threshold", "vo2max", "speed"],
        help="Workout type",
    )
    parser.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Target duration in minutes",
    )

    # Optional zone information
    parser.add_argument("--hr-max", type=int, help="Maximum heart rate (bpm)")
    parser.add_argument("--lthr", type=int, help="Lactate threshold heart rate (bpm)")
    parser.add_argument("--ftp", type=int, help="Functional Threshold Power (watts) for cycling")

    # Readiness
    parser.add_argument(
        "--readiness",
        type=int,
        help="Readiness score (0-100) to adapt workout",
    )

    # Terrain and equipment
    parser.add_argument(
        "--terrain",
        type=str,
        default="flat",
        choices=["flat", "rolling", "hilly", "mountainous", "indoor"],
        help="Terrain type",
    )
    parser.add_argument(
        "--equipment",
        type=str,
        nargs="*",
        help="Available equipment (e.g., power meter, heart rate monitor)",
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./data/workouts"),
        help="Output directory for workout files",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="both",
        choices=["markdown", "json", "both"],
        help="Output format",
    )

    args = parser.parse_args()

    # Build zones dict
    zones = {}
    if args.hr_max:
        zones["hr_max"] = args.hr_max
    if args.lthr:
        zones["lthr"] = args.lthr
    if args.ftp:
        zones["ftp"] = args.ftp

    # Create generator
    generator = WorkoutGenerator()

    # Generate workout
    logger.info(f"Generating {args.sport} {args.type} workout ({args.duration} min)...")

    workout = generator.generate_workout(
        sport=Sport(args.sport),
        workout_type=WorkoutType(args.type),
        duration_minutes=args.duration,
        athlete_zones=zones if zones else None,
        readiness_score=args.readiness,
        terrain=Terrain(args.terrain),
        equipment_available=args.equipment or [],
    )

    # Display to console
    print("\n" + "=" * 80)
    print(workout.to_markdown())
    print("=" * 80)

    # Save to files
    args.output_dir.mkdir(parents=True, exist_ok=True)

    base_filename = f"{workout.sport.value}_{workout.workout_type.value}_{workout.workout_id}"

    if args.format in ["markdown", "both"]:
        md_path = args.output_dir / f"{base_filename}.md"
        md_path.write_text(workout.to_markdown(), encoding="utf-8")
        logger.info(f"✅ Saved markdown: {md_path}")

    if args.format in ["json", "both"]:
        json_path = args.output_dir / f"{base_filename}.json"
        json_path.write_text(json.dumps(workout.to_dict(), indent=2), encoding="utf-8")
        logger.info(f"✅ Saved JSON: {json_path}")

    # Summary
    print(f"\n📁 Workout saved to: {args.output_dir}")
    if args.readiness:
        print(f"🎯 Adapted for readiness score: {args.readiness}/100")
    print(f"⏱️  Total duration: {workout.get_total_duration():.0f} minutes")
    print(f"💪 Peak intensity: Zone {workout.peak_intensity.value.upper()}")


if __name__ == "__main__":
    main()
