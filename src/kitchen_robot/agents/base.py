from abc import ABC, abstractmethod

from kitchen_robot.messages import AgentEvent


class Agent(ABC):
    @abstractmethod
    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        """Handle an event and return zero or more follow-up events."""

