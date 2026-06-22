from kitchen_robot.agents.base import Agent
from kitchen_robot.config import Settings
from kitchen_robot.messages import AgentEvent, AgentName, EventType
from kitchen_robot.transports.ble import Esp32BleClient, serialize_stir_command


class Esp32BleAgent(Agent):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Esp32BleClient(settings.ble_device_name)

    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        if event.event_type != EventType.STIR_COMMAND:
            return []

        command = serialize_stir_command(event.payload)
        if self.settings.mock:
            print(f"[esp32/mock] {command}")
            return [
                AgentEvent(
                    event_type=EventType.HARDWARE_STATUS,
                    source=AgentName.ESP32_BLE,
                    payload={"ok": True, "command": command},
                )
            ]

        result = await self.client.send_command(command)
        return [
            AgentEvent(
                event_type=EventType.HARDWARE_STATUS,
                source=AgentName.ESP32_BLE,
                payload={"ok": result.ok, "message": result.message, "command": command},
            )
        ]
