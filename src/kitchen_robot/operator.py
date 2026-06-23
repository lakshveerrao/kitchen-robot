import asyncio
from multiprocessing import Queue, get_context
from queue import Empty
from typing import Any

from kitchen_robot.config import Settings
from kitchen_robot.transports.serial_wire import (
    Esp32SerialClient,
    detect_esp32_port,
    list_serial_devices,
    serialize_serial_stir_command,
)
from kitchen_robot.transports.ble import payload_from_cli_command, serialize_stir_command


async def camera_check(settings: Settings) -> int:
    from kitchen_robot.services.video import LiveVideoWindow

    video = LiveVideoWindow(settings)
    frames = video.capture_jpeg_window()
    print(
        "camera ok: "
        f"captured {len(frames)} sampled frame(s) from camera index {settings.camera_index}"
    )
    return 0


async def ble_scan(settings: Settings, timeout: float) -> int:
    result = _run_ble_worker(_ble_scan_worker, (settings, timeout), timeout + 5)
    if not result["ok"]:
        print(
            "BLE scan timed out. Check macOS Bluetooth permission for the terminal/Codex app, "
            "then try again."
        )
        if result.get("error"):
            print(result["error"])
        return 3

    devices = result["devices"]
    if not devices:
        print("no BLE devices found")
        return 1

    found_target = False
    for device in devices:
        marker = ""
        if device.name == settings.ble_device_name:
            marker = " <-- target"
            found_target = True
        print(f"{device.name or '(no name)'} | {device.address} | rssi={device.rssi}{marker}")

    return 0 if found_target else 2


async def stirrer_command(settings: Settings, command: str, value: str | None) -> int:
    payload = payload_from_cli_command(command, value)
    serialized = serialize_stir_command(payload)
    print(f"sending to {settings.ble_device_name}: {serialized}")

    result = _run_ble_worker(_ble_command_worker, (settings, serialized), 12)
    if not result["ok"]:
        print(
            "BLE command timed out. Check that KitchenStirrer is advertising and macOS "
            "Bluetooth permission is allowed."
        )
        if result.get("error"):
            print(result["error"])
        return 3

    print(result["message"])
    return 0


async def serial_scan() -> int:
    devices = list_serial_devices()
    if not devices:
        print("no serial devices found")
        return 1

    detected = detect_esp32_port()
    for device in devices:
        marker = " <-- auto" if device.port == detected else ""
        print(f"{device.port} | {device.description} | {device.hwid}{marker}")
    return 0 if detected else 2


async def wired_stirrer_command(command: str, value: str | None, port: str | None = None) -> int:
    payload = payload_from_cli_command(command, value)
    serialized = serialize_serial_stir_command(payload)
    print(f"sending over USB serial: {serialized}")

    timeout = 10 if command in {"stop", "emergency_stop"} else 7
    result = _run_wired_worker(serialized, port, timeout)
    if not result["ok"]:
        print(f"port: {result.get('port') or 'unknown'}")
        print(result.get("error") or "Wired command timed out")
        return 1

    print(f"port: {result.get('port') or 'none'}")
    print(result["message"])
    return 0 if result["command_ok"] else 1


def _run_ble_worker(worker: Any, args: tuple[Any, ...], timeout: float) -> dict[str, Any]:
    context = get_context("spawn")
    queue: Queue = context.Queue()
    process = context.Process(target=worker, args=(*args, queue))
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join(2)
        return {"ok": False, "error": f"operation exceeded {timeout:.1f}s"}

    try:
        return queue.get_nowait()
    except Empty:
        return {"ok": False, "error": "BLE worker exited without a result"}


def _run_wired_worker(command: str, port: str | None, timeout: float) -> dict[str, Any]:
    context = get_context("spawn")
    queue: Queue = context.Queue()
    process = context.Process(target=_wired_command_worker, args=(command, port, queue))
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join(0.5)
        return {
            "ok": False,
            "port": port,
            "error": f"Wired command timed out after {timeout:.1f}s",
        }

    try:
        return queue.get_nowait()
    except Empty:
        return {"ok": False, "port": port, "error": "Wired worker exited without a result"}


def _wired_command_worker(command: str, port: str | None, queue: Queue) -> None:
    try:
        client = Esp32SerialClient(port=port)
        result = client.send_command(command)
        queue.put(
            {
                "ok": True,
                "command_ok": result.ok,
                "port": result.port,
                "message": result.message,
            }
        )
    except Exception as exc:
        queue.put({"ok": False, "port": port, "error": str(exc)})


def _ble_scan_worker(settings: Settings, timeout: float, queue: Queue) -> None:
    async def run() -> None:
        from kitchen_robot.transports.ble import Esp32BleClient

        client = Esp32BleClient(settings.ble_device_name)
        devices = await client.scan(timeout=timeout)
        queue.put({"ok": True, "devices": devices})

    try:
        asyncio.run(run())
    except Exception as exc:
        queue.put({"ok": False, "error": str(exc)})


def _ble_command_worker(settings: Settings, command: str, queue: Queue) -> None:
    async def run() -> None:
        from kitchen_robot.transports.ble import Esp32BleClient

        client = Esp32BleClient(settings.ble_device_name)
        result = await client.send_command(command)
        queue.put({"ok": result.ok, "message": result.message})

    try:
        asyncio.run(run())
    except Exception as exc:
        queue.put({"ok": False, "error": str(exc)})
