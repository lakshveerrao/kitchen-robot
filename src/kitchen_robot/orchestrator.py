from collections import deque

from kitchen_robot.agents.esp32_ble import Esp32BleAgent
from kitchen_robot.agents.recipe import RecipeAgent
from kitchen_robot.agents.reasoning import MainReasoningAgent
from kitchen_robot.agents.safety import SafetyAgent
from kitchen_robot.agents.speech import SpeechAgent
from kitchen_robot.agents.stirring import StirringAgent
from kitchen_robot.agents.vision import VisionAgent
from kitchen_robot.agents.voice import VoiceListenAgent
from kitchen_robot.config import Settings
from kitchen_robot.messages import AgentEvent, AgentName, EventType


class Orchestrator:
    def __init__(self, settings: Settings, recipe_id: str) -> None:
        self.settings = settings
        self.agents = {
            AgentName.RECIPE: RecipeAgent(recipe_id),
            AgentName.MAIN_REASONING: MainReasoningAgent(settings),
            AgentName.SPEECH: SpeechAgent(settings),
            AgentName.STIRRING: StirringAgent(),
            AgentName.VISION: VisionAgent(settings),
            AgentName.ESP32_BLE: Esp32BleAgent(settings),
            AgentName.SAFETY: SafetyAgent(),
            AgentName.VOICE_LISTEN: VoiceListenAgent(),
        }

    async def run(self) -> None:
        queue: deque[AgentEvent] = deque(
            [
                AgentEvent(
                    event_type=EventType.SESSION_STARTED,
                    source=AgentName.ORCHESTRATOR,
                    payload={"recipe": "upma", "mode": "mock" if self.settings.mock else "real"},
                )
            ]
        )

        processed = 0
        while queue and processed < 50:
            event = queue.popleft()
            processed += 1
            print(f"[orchestrator] {event.event_type} <- {event.source}")

            if event.target:
                targets = [event.target]
            else:
                targets = list(self.agents.keys())

            for target in targets:
                agent = self.agents[target]
                followups = await agent.handle(event)
                queue.extend(followups)

        print("[orchestrator] session loop ended")

