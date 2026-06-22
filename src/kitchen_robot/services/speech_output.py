import asyncio
import subprocess
import tempfile
from pathlib import Path

from kitchen_robot.config import Settings


class SpeechOutput:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def speak(self, text: str) -> None:
        await asyncio.to_thread(self._speak_sync, text)

    def _speak_sync(self, text: str) -> None:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for API-backed speech output.")

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install the 'openai' package to use API-backed speech output.") from exc

        client = OpenAI(api_key=self.settings.openai_api_key)
        response = client.audio.speech.create(
            model=self.settings.tts_model,
            voice=self.settings.tts_voice,
            input=text,
            instructions=(
                "Speak naturally like a calm kitchen assistant. Match the user's language "
                "style when the text includes Hindi, Hinglish, Telugu, or Telugish."
            ),
        )

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            audio_path = Path(audio_file.name)
            audio_file.write(response.read())

        try:
            subprocess.run(["afplay", str(audio_path)], check=True)
        finally:
            audio_path.unlink(missing_ok=True)

