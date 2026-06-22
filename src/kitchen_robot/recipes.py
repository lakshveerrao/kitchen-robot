from dataclasses import dataclass


@dataclass(frozen=True)
class RecipeStep:
    step_id: str
    instruction: str
    expected_human_action: str | None = None
    stir_mode: str | None = None
    vision_goal: str | None = None
    ask_confirmation_when_uncertain: bool = True


UPMA_RECIPE: list[RecipeStep] = [
    RecipeStep(
        step_id="prepare",
        instruction="Place the kadai on heat and add oil.",
        expected_human_action="Add oil to the kadai.",
        stir_mode=None,
        vision_goal="kadai visible with oil added",
    ),
    RecipeStep(
        step_id="temper",
        instruction="Add mustard seeds, curry leaves, green chili, and onion.",
        expected_human_action="Add tempering ingredients.",
        stir_mode="slow",
        vision_goal="onion starts softening",
    ),
    RecipeStep(
        step_id="roast_suji",
        instruction="Add suji. I will stir while it roasts until light brown.",
        expected_human_action="Add suji.",
        stir_mode="medium",
        vision_goal="suji turns light brown",
    ),
    RecipeStep(
        step_id="add_water",
        instruction="The suji looks ready. Add water slowly while I stir.",
        expected_human_action="Add water slowly.",
        stir_mode="slow",
        vision_goal="water added and mixture bubbling",
    ),
    RecipeStep(
        step_id="cook_thicken",
        instruction="Let it cook while I stir until it thickens.",
        expected_human_action=None,
        stir_mode="slow",
        vision_goal="upma thickened and pulling together",
    ),
    RecipeStep(
        step_id="finish",
        instruction="Upma looks done. Turn off the heat.",
        expected_human_action="Turn off heat.",
        stir_mode=None,
        vision_goal="finished upma consistency",
    ),
]


RECIPES = {"upma": UPMA_RECIPE}

