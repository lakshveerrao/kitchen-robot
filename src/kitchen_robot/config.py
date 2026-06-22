from dataclasses import dataclass
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None


@dataclass(frozen=True)
class Settings:
    mock: bool
    openai_api_key: str | None
    reasoning_model: str | None
    vision_model: str | None
    stt_model: str | None
    tts_model: str | None
    tts_voice: str
    wake_word: str
    active_listen_seconds: int
    ble_device_name: str
    camera_index: int
    video_window_seconds: float
    video_sample_every_n_frames: int

    @classmethod
    def from_env(cls, mock: bool = False) -> "Settings":
        load_dotenv()
        return cls(
            mock=mock,
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            reasoning_model=os.getenv("KITCHEN_ROBOT_REASONING_MODEL", "gpt-5.5"),
            vision_model=os.getenv("KITCHEN_ROBOT_VISION_MODEL", "gpt-5.5"),
            stt_model=os.getenv("KITCHEN_ROBOT_STT_MODEL", "gpt-4o-transcribe"),
            tts_model=os.getenv("KITCHEN_ROBOT_TTS_MODEL", "gpt-4o-mini-tts"),
            tts_voice=os.getenv("KITCHEN_ROBOT_TTS_VOICE", "marin"),
            wake_word=os.getenv("KITCHEN_ROBOT_WAKE_WORD", "hey robot").lower(),
            active_listen_seconds=int(os.getenv("KITCHEN_ROBOT_ACTIVE_LISTEN_SECONDS", "15")),
            ble_device_name=os.getenv("KITCHEN_ROBOT_BLE_DEVICE_NAME", "KitchenStirrer"),
            camera_index=int(os.getenv("KITCHEN_ROBOT_CAMERA_INDEX", "0")),
            video_window_seconds=float(os.getenv("KITCHEN_ROBOT_VIDEO_WINDOW_SECONDS", "2.0")),
            video_sample_every_n_frames=int(
                os.getenv("KITCHEN_ROBOT_VIDEO_SAMPLE_EVERY_N_FRAMES", "10")
            ),
        )
