from kitchen_robot.agents.base import Agent
from kitchen_robot.messages import AgentEvent, AgentName, EventType


class StirringAgent(Agent):
    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        if event.event_type == EventType.SAFETY_STOP:
            return [
                AgentEvent(
                    event_type=EventType.STIR_COMMAND,
                    source=AgentName.STIRRING,
                    target=AgentName.ESP32_BLE,
                    payload={"type": "emergency_stop"},
                )
            ]

        if event.event_type != EventType.RECIPE_STEP_READY:
            return []

        stir_mode = event.payload.get("stir_mode")
        if stir_mode is None:
            command = {"type": "stop"}
        else:
            command = {"type": "start_profile", "profile": stir_mode}

        return [
            AgentEvent(
                event_type=EventType.STIR_COMMAND,
                source=AgentName.STIRRING,
                target=AgentName.ESP32_BLE,
                payload=command,
            )
        ]
