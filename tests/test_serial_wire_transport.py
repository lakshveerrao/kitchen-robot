import pytest

from kitchen_robot.transports.serial_wire import serialize_serial_stir_command


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"type": "start_profile", "profile": "slow"}, "start 5000"),
        ({"type": "start_delay", "delay_micros": 2500}, "start 2500"),
        ({"type": "status"}, "status"),
        ({"type": "servo", "target": "lift", "position": "down"}, "servo lift down"),
        ({"type": "servo", "target": "home", "position": "home"}, "servo home"),
        ({"type": "servo", "target": "sweep", "position": "sweep"}, "servo sweep"),
    ],
)
def test_serialize_serial_stir_command(payload: dict, expected: str) -> None:
    assert serialize_serial_stir_command(payload) == expected


def test_serialize_serial_stir_command_rejects_unknown_command() -> None:
    with pytest.raises(ValueError):
        serialize_serial_stir_command({"type": "dance"})


def test_serialize_serial_stir_command_rejects_removed_reach_servo() -> None:
    with pytest.raises(ValueError):
        serialize_serial_stir_command({"type": "servo", "target": "reach", "position": "back"})
