from kitchen_robot.agents.base import Agent
from kitchen_robot.messages import AgentEvent


class SafetyAgent(Agent):
    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        # The real implementation will monitor live video for hands near pan boundaries.
        return []

