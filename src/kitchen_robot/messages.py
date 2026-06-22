from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class AgentName(str, Enum):
    ORCHESTRATOR = "orchestrator"
    MAIN_REASONING = "main_reasoning"
    RECIPE = "recipe"
    VISION = "vision"
    SAFETY = "safety"
    VOICE_LISTEN = "voice_listen"
    SPEECH = "speech"
    STIRRING = "stirring"
    ESP32_BLE = "esp32_ble"
    ESP32_SERIAL = "esp32_serial"


class EventType(str, Enum):
    SESSION_STARTED = "session_started"
    USER_UTTERANCE = "user_utterance"
    RECIPE_STEP_READY = "recipe_step_ready"
    VISION_OBSERVATION = "vision_observation"
    SAFETY_STOP = "safety_stop"
    REASONING_ADVICE = "reasoning_advice"
    SPEECH_REQUEST = "speech_request"
    STIR_COMMAND = "stir_command"
    HARDWARE_STATUS = "hardware_status"
    SESSION_ENDED = "session_ended"


@dataclass(frozen=True)
class AgentEvent:
    event_type: EventType
    source: AgentName
    payload: dict[str, Any]
    target: AgentName | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
