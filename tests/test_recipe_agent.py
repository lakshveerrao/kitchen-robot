import pytest

from kitchen_robot.agents.recipe import RecipeAgent
from kitchen_robot.messages import AgentEvent, AgentName, EventType


@pytest.mark.asyncio
async def test_recipe_agent_starts_with_prepare_step() -> None:
    agent = RecipeAgent("upma")
    events = await agent.handle(
        AgentEvent(
            event_type=EventType.SESSION_STARTED,
            source=AgentName.ORCHESTRATOR,
            payload={},
        )
    )

    assert len(events) == 1
    assert events[0].event_type == EventType.RECIPE_STEP_READY
    assert events[0].payload["step_id"] == "prepare"

