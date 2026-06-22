from kitchen_robot.agents.base import Agent
from kitchen_robot.config import Settings
from kitchen_robot.messages import AgentEvent, EventType
from kitchen_robot.services.speech_output import SpeechOutput


class SpeechAgent(Agent):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.output = SpeechOutput(settings)

    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        if event.event_type not in {EventType.RECIPE_STEP_READY, EventType.SPEECH_REQUEST}:
            return []

        text = event.payload.get("instruction") or event.payload.get("text")
        if not text:
            return []

        if self.settings.mock:
            print(f"[speech/mock] {text}")
            return []

        await self.output.speak(text)
        return []
