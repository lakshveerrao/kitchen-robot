import asyncio
import base64
import json
from typing import Any

from kitchen_robot.config import Settings


class OpenAiGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _client(self):
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install the 'openai' package to use API-backed agents.") from exc

        return OpenAI(api_key=self.settings.openai_api_key)

    async def inspect_video_window(
        self,
        *,
        recipe_step: dict[str, Any],
        jpeg_frames: list[bytes],
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._inspect_video_window_sync,
            recipe_step,
            jpeg_frames,
        )

    def _inspect_video_window_sync(
        self,
        recipe_step: dict[str, Any],
        jpeg_frames: list[bytes],
    ) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for API-backed vision.")

        frame_items = []
        for frame in jpeg_frames:
            encoded = base64.b64encode(frame).decode("utf-8")
            frame_items.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{encoded}",
                }
            )

        prompt = (
            "You are the Vision Agent for a kitchen robot. These images are sampled "
            "from a short live video window, in order. Evaluate the cooking state for "
            "the current upma recipe step. Return compact JSON only with keys: "
            "goal_met boolean, confidence number 0-1, summary string, safety_notes string, "
            "safety_stop boolean. Set safety_stop true if a hand, face, cloth, cable, "
            "or unsafe object is near the pan or stirrer boundary. "
            f"Current step: {json.dumps(recipe_step)}"
        )

        response = self._client().responses.create(
            model=self.settings.vision_model,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}, *frame_items],
                }
            ],
        )

        return self._parse_json_response(response.output_text)

    async def reason_from_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._reason_from_observation_sync, observation)

    def _reason_from_observation_sync(self, observation: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for API-backed reasoning.")

        prompt = (
            "You are the Main Reasoning Agent for a kitchen robot. You reason only; "
            "you do not control hardware. Given this orchestrator observation, return "
            "compact JSON only with keys: advance_step boolean, say string, confidence number 0-1. "
            f"Observation: {json.dumps(observation)}"
        )

        response = self._client().responses.create(
            model=self.settings.reasoning_model,
            input=prompt,
        )
        return self._parse_json_response(response.output_text)

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return {"advance_step": False, "say": text, "confidence": 0.0}

        if not isinstance(value, dict):
            return {"advance_step": False, "say": str(value), "confidence": 0.0}
        return value
