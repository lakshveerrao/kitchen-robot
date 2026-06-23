import pytest

from kitchen_robot.transports.ble import serialize_stir_command


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"type": "stop"}, "stop"),
        ({"type": "emergency_stop"}, "emergency_stop"),
        ({"type": "start_profile", "profile": "slow"}, "start_profile slow"),
        ({"type": "start_delay", "delay_micros": 2500}, "start 2500"),
        ({"type": "reverse"}, "reverse"),
        ({"type": "status"}, "status"),
        ({"type": "servo", "target": "lift", "position": "up"}, "servo lift up"),
        ({"type": "servo", "target": "home", "position": "home"}, "servo home"),
    ],
)
def test_serialize_stir_command(payload: dict, expected: str) -> None:
    assert serialize_stir_command(payload) == expected


def test_serialize_stir_command_rejects_unknown_command() -> None:
    with pytest.raises(ValueError):
        serialize_stir_command({"type": "dance"})


def test_serialize_stir_command_rejects_removed_reach_servo() -> None:
    with pytest.raises(ValueError):
        serialize_stir_command({"type": "servo", "target": "reach", "position": "front"})
