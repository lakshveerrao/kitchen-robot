import asyncio

from kitchen_robot.agents.base import Agent
from kitchen_robot.config import Settings
from kitchen_robot.messages import AgentEvent, AgentName, EventType
from kitchen_robot.services.openai_gateway import OpenAiGateway
from kitchen_robot.services.video import LiveVideoWindow


class VisionAgent(Agent):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.video = LiveVideoWindow(settings)
        self.openai = OpenAiGateway(settings)

    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        if event.event_type != EventType.RECIPE_STEP_READY:
            return []

        vision_goal = event.payload.get("vision_goal")
        if not vision_goal:
            return []

        if self.settings.mock:
            await asyncio.sleep(0.1)
            return [
                AgentEvent(
                    event_type=EventType.VISION_OBSERVATION,
                    source=AgentName.VISION,
                    payload={
                        "goal": vision_goal,
                        "goal_met": event.payload["step_id"] in {"prepare", "finish"},
                        "confidence": 0.75,
                        "summary": f"Mock observation for goal: {vision_goal}",
                    },
                )
            ]

        frames = self.video.capture_jpeg_window()
        observation = await self.openai.inspect_video_window(
            recipe_step=event.payload,
            jpeg_frames=frames,
        )
        return [
            AgentEvent(
                event_type=EventType.VISION_OBSERVATION,
                source=AgentName.VISION,
                payload={
                    "goal": vision_goal,
                    "goal_met": bool(observation.get("goal_met", False)),
                    "confidence": float(observation.get("confidence", 0.0)),
                    "summary": observation.get("summary", ""),
                    "safety_notes": observation.get("safety_notes", ""),
                },
            )
        ]
