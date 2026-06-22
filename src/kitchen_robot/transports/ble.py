from dataclasses import dataclass


SERVICE_UUID = "8a4f1000-0b38-4f4d-8b5f-6e5d7f0c1000"
RX_UUID = "8a4f1001-0b38-4f4d-8b5f-6e5d7f0c1000"
TX_UUID = "8a4f1002-0b38-4f4d-8b5f-6e5d7f0c1000"


@dataclass
class BleCommandResult:
    ok: bool
    message: str


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

    raise ValueError(f"Unsupported stir command: {payload}")


class Esp32BleClient:
    def __init__(self, device_name: str) -> None:
        self.device_name = device_name

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

