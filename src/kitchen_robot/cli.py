import argparse
import asyncio

from kitchen_robot.config import Settings
from kitchen_robot.orchestrator import Orchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kitchen Robot Testing 1 runner")
    parser.add_argument("--mock", action="store_true", help="Run without real camera, APIs, voice, or BLE")
    parser.add_argument("--recipe", default="upma", choices=["upma"], help="Recipe to run")
    return parser


async def async_main() -> int:
    args = build_parser().parse_args()
    settings = Settings.from_env(mock=args.mock)
    orchestrator = Orchestrator(settings=settings, recipe_id=args.recipe)
    await orchestrator.run()
    return 0


def main() -> int:
    return asyncio.run(async_main())

