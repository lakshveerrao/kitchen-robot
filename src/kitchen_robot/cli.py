import argparse
import asyncio

from kitchen_robot.config import Settings
from kitchen_robot.operator import (
    ble_scan,
    camera_check,
    serial_scan,
    stirrer_command,
    wired_stirrer_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kitchen Robot Testing 1 runner")
    subparsers = parser.add_subparsers(dest="command")
    gui_parser = subparsers.add_parser("gui", help="Run the local browser GUI")
    gui_parser.add_argument("--host", default="127.0.0.1")
    gui_parser.add_argument("--port", type=int, default=8787)

    run_parser = subparsers.add_parser("run", help="Run the orchestrator")
    run_parser.add_argument(
        "--mock",
        action="store_true",
        help="Run without real camera, APIs, voice, or wired motor control",
    )
    run_parser.add_argument("--recipe", default="upma", choices=["upma"], help="Recipe to run")

    camera_parser = subparsers.add_parser("camera-check", help="Capture a short video window")
    camera_parser.add_argument("--camera-index", type=int, default=None)
    camera_parser.add_argument("--seconds", type=float, default=None)

    ble_parser = subparsers.add_parser("ble-scan", help="Scan for BLE devices")
    ble_parser.add_argument("--timeout", type=float, default=5.0)

    stirrer_parser = subparsers.add_parser("stirrer-command", help="Send one command to the ESP32 stirrer")
    stirrer_parser.add_argument(
        "stirrer_command",
        choices=["status", "stop", "emergency_stop", "reverse", "start_profile", "start_delay"],
        nargs="?",
        default="status",
    )
    stirrer_parser.add_argument("--value", default=None, help="Profile name or delay value")

    serial_scan_parser = subparsers.add_parser("serial-scan", help="Find wired ESP32 serial ports")
    serial_scan_parser.set_defaults(_serial_scan=True)

    wired_parser = subparsers.add_parser("wired-command", help="Send one command over USB serial")
    wired_parser.add_argument(
        "wired_command",
        choices=["status", "stop", "emergency_stop", "reverse", "start_profile", "start_delay"],
        nargs="?",
        default="status",
    )
    wired_parser.add_argument("--value", default=None, help="Profile name or delay value")
    wired_parser.add_argument("--port", default=None, help="Serial port override")
    return parser


async def async_main() -> int:
    args = build_parser().parse_args()
    command = args.command or "run"
    settings = Settings.from_env(mock=getattr(args, "mock", False))

    if command == "gui":
        from kitchen_robot.gui import run_gui

        run_gui(args.host, args.port)
        return 0

    if getattr(args, "camera_index", None) is not None:
        settings = settings.with_overrides(camera_index=args.camera_index)
    if getattr(args, "seconds", None) is not None:
        settings = settings.with_overrides(video_window_seconds=args.seconds)

    if command == "camera-check":
        return await camera_check(settings)

    if command == "ble-scan":
        return await ble_scan(settings, timeout=args.timeout)

    if command == "stirrer-command":
        return await stirrer_command(settings, args.stirrer_command, args.value)

    if command == "serial-scan":
        return await serial_scan()

    if command == "wired-command":
        return await wired_stirrer_command(args.wired_command, args.value, port=args.port)

    from kitchen_robot.orchestrator import Orchestrator

    orchestrator = Orchestrator(settings=settings, recipe_id=args.recipe)
    await orchestrator.run()
    return 0


def main() -> int:
    return asyncio.run(async_main())
