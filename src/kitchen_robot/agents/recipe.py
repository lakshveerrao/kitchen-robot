from kitchen_robot.agents.base import Agent
from kitchen_robot.messages import AgentEvent, AgentName, EventType
from kitchen_robot.recipes import RECIPES, RecipeStep


class RecipeAgent(Agent):
    def __init__(self, recipe_id: str) -> None:
        self.recipe_id = recipe_id
        self.steps = RECIPES[recipe_id]
        self.current_index = 0

    @property
    def current_step(self) -> RecipeStep:
        return self.steps[self.current_index]

    async def handle(self, event: AgentEvent) -> list[AgentEvent]:
        if event.event_type == EventType.SESSION_STARTED:
            return [self._step_event()]

        if event.event_type == EventType.REASONING_ADVICE and event.payload.get("advance_step"):
            self.current_index = min(self.current_index + 1, len(self.steps) - 1)
            return [self._step_event()]

        return []

    def _step_event(self) -> AgentEvent:
        step = self.current_step
        return AgentEvent(
            event_type=EventType.RECIPE_STEP_READY,
            source=AgentName.RECIPE,
            payload={
                "step_id": step.step_id,
                "instruction": step.instruction,
                "expected_human_action": step.expected_human_action,
                "stir_mode": step.stir_mode,
                "vision_goal": step.vision_goal,
                "ask_confirmation_when_uncertain": step.ask_confirmation_when_uncertain,
            },
        )

