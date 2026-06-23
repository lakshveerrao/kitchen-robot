from dataclasses import dataclass
from typing import Any


SERVICE_UUID = "8a4f1000-0b38-4f4d-8b5f-6e5d7f0c1000"
RX_UUID = "8a4f1001-0b38-4f4d-8b5f-6e5d7f0c1000"
TX_UUID = "8a4f1002-0b38-4f4d-8b5f-6e5d7f0c1000"


@dataclass
class BleCommandResult:
    ok: bool
    message: str


@dataclass(frozen=True)
class BleDeviceInfo:
    name: str | None
    address: str
    rssi: int | None


def serialize_stir_command(payload: dict) -> str:
    command_type = payload.get("type")

    if command_type == "stop":
        return "stop"

    if command_type == "emergency_stop":
        return "emergency_stop"

    if command_type == "start_profile":
        profile = payload.get("profile", "slow")
        return f"start_profile {profile}"

    if command_type == "start_delay":
        delay_micros = int(payload["delay_micros"])
        return f"start {delay_micros}"

    if command_type == "reverse":
        return "reverse"

    if command_type == "status":
        return "status"

    if command_type == "servo":
        target = str(payload["target"])
        position = str(payload["position"])
        if target == "home":
            return "servo home"
        if target != "lift":
            raise ValueError(f"Unsupported servo target: {target}")
        return f"servo {target} {position}"

    raise ValueError(f"Unsupported stir command: {payload}")


class Esp32BleClient:
    def __init__(self, device_name: str) -> None:
        self.device_name = device_name

    async def scan(self, timeout: float = 5.0) -> list[BleDeviceInfo]:
        try:
            from bleak import BleakScanner
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install the 'bleak' package to use ESP32 BLE control.") from exc

        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
        results: list[BleDeviceInfo] = []
        for device, advertisement in devices.values():
            results.append(
                BleDeviceInfo(
                    name=device.name or advertisement.local_name,
                    address=device.address,
                    rssi=getattr(advertisement, "rssi", None),
                )
            )
        return sorted(results, key=lambda item: (item.name or "", item.address))

    async def send_command(self, command: str) -> BleCommandResult:
        try:
            from bleak import BleakClient, BleakScanner
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install the 'bleak' package to use ESP32 BLE control.") from exc

        device = await BleakScanner.find_device_by_filter(
            lambda discovered, _: discovered.name == self.device_name
        )
        if device is None:
            return BleCommandResult(ok=False, message=f"Device not found: {self.device_name}")

        async with BleakClient(device) as client:
            await client.write_gatt_char(RX_UUID, command.encode("utf-8"), response=False)
            return BleCommandResult(ok=True, message=f"sent: {command}")


def payload_from_cli_command(command: str, value: str | None = None) -> dict[str, Any]:
    if command in {"status", "stop", "emergency_stop", "reverse"}:
        return {"type": command}

    if command == "start_profile":
        return {"type": "start_profile", "profile": value or "slow"}

    if command == "start_delay":
        if value is None:
            raise ValueError("start_delay requires a delay value in microseconds")
        return {"type": "start_delay", "delay_micros": int(value)}

    if command == "servo":
        if value is None:
            raise ValueError("servo requires a value like 'lift up' or 'lift down'")
        parts = value.split(maxsplit=1)
        if len(parts) == 1 and parts[0] == "home":
            return {"type": "servo", "target": "home", "position": "home"}
        if len(parts) != 2:
            raise ValueError("servo requires a value like 'lift up' or 'lift down'")
        if parts[0] != "lift":
            raise ValueError("Testing 1 supports only the lift servo")
        return {"type": "servo", "target": parts[0], "position": parts[1]}

    raise ValueError(f"Unsupported CLI command: {command}")
