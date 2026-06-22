import asyncio

from kitchen_robot.agents.base import Agent
from kitchen_robot.config import Settings
from kitchen_robot.messages import AgentEvent, AgentName, EventType
from kitchen_robot.transports.ble import serialize_stir_command
from kitchen_robot.transports.serial_wire import Esp32SerialClient


class Esp32SerialAgent(Agent):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Esp32SerialClient()

    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        if event.event_type != EventType.STIR_COMMAND:
            return []

        command = serialize_stir_command(event.payload)
        if self.settings.mock:
            print(f"[esp32-serial/mock] {command}")
            return [
                AgentEvent(
                    event_type=EventType.HARDWARE_STATUS,
                    source=AgentName.ESP32_SERIAL,
                    payload={"ok": True, "command": command, "transport": "wired_serial"},
                )
            ]

        result = await asyncio.to_thread(self.client.send_command, command)
        return [
            AgentEvent(
                event_type=EventType.HARDWARE_STATUS,
                source=AgentName.ESP32_SERIAL,
                payload={
                    "ok": result.ok,
                    "message": result.message,
                    "command": command,
                    "port": result.port,
                    "transport": "wired_serial",
                },
            )
        ]
