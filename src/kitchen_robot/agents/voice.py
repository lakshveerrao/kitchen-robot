from kitchen_robot.agents.base import Agent
from kitchen_robot.messages import AgentEvent


class VoiceListenAgent(Agent):
    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        # The real implementation will handle wake word, 15 second active listening, and STT.
        return []

