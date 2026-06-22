from kitchen_robot.transports.ble import payload_from_cli_command


def test_payload_from_cli_status() -> None:
    assert payload_from_cli_command("status") == {"type": "status"}


def test_payload_from_cli_start_profile_defaults_to_slow() -> None:
    assert payload_from_cli_command("start_profile") == {
        "type": "start_profile",
        "profile": "slow",
    }


def test_payload_from_cli_start_delay_uses_value() -> None:
    assert payload_from_cli_command("start_delay", "2500") == {
        "type": "start_delay",
        "delay_micros": 2500,
    }
