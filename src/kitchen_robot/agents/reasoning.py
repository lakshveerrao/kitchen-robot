from kitchen_robot.agents.base import Agent
from kitchen_robot.config import Settings
from kitchen_robot.messages import AgentEvent, AgentName, EventType
from kitchen_robot.services.openai_gateway import OpenAiGateway


class MainReasoningAgent(Agent):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.openai = OpenAiGateway(settings)

    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        if event.event_type != EventType.VISION_OBSERVATION:
            return []

        if self.settings.mock:
            goal_met = event.payload.get("goal_met", False)
            return [
                AgentEvent(
                    event_type=EventType.REASONING_ADVICE,
                    source=AgentName.MAIN_REASONING,
                    payload={
                        "advance_step": goal_met,
                        "say": "The current cooking stage looks ready. Please continue to the next step."
                        if goal_met
                        else "I am still watching this stage.",
                        "confidence": event.payload.get("confidence", 0.5),
                    },
                )
            ]

        advice = await self.openai.reason_from_observation(event.payload)
        return [
            AgentEvent(
                event_type=EventType.REASONING_ADVICE,
                source=AgentName.MAIN_REASONING,
                payload={
                    "advance_step": bool(advice.get("advance_step", False)),
                    "say": advice.get("say", ""),
                    "confidence": float(advice.get("confidence", 0.0)),
                },
            )
        ]
