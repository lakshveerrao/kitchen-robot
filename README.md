# Kitchen Robot - Testing 1

Testing 1 is a laptop-run proof of concept for a voice-first kitchen robot that guides a fixed upma recipe and controls a stirrer through an ESP32-C3.

The product requirements and milestone plan live in:

```text
docs/PRD.md
```

## Scope

- Runtime: macOS laptop
- Camera: external camera, diagonal top view of a kadai
- Voice input: external microphone
- Voice output: Bose speaker through AUX
- Controller: ESP32-C3
- Motor: NEMA 17 stepper via A4988
- Recipe: fixed upma
- Human actions: add ingredients and control heat
- Robot action: stirring only

## Architecture

```text
Sub-agents <-> Orchestrator Agent <-> Main Reasoning Agent
```

The Main Reasoning Agent reasons and advises. It does not directly control hardware. The Orchestrator coordinates sub-agents and action agents.

Initial agents:

- Voice Listen Agent
- Speech Agent
- Vision Agent
- Safety Agent
- Recipe Agent
- Stirring Agent
- ESP32 BLE Agent
- Main Reasoning Agent

## Quick Start

```bash
/Users/pbl/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
PYTHONPATH=src python -m kitchen_robot --mock
```

The first run uses mock mode so the orchestration loop can be tested before camera, voice, APIs, and ESP32 are connected.

## Verification

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
PYTHONPATH=src .venv/bin/python -m kitchen_robot run --mock
```

## Operator Commands

```bash
# Start the local GUI
PYTHONPATH=src .venv/bin/python -m kitchen_robot gui

# Run the mock orchestrator
PYTHONPATH=src .venv/bin/python -m kitchen_robot run --mock

# Check camera capture without calling the AI API
PYTHONPATH=src .venv/bin/python -m kitchen_robot camera-check --camera-index 0 --seconds 2

# Scan for the ESP32 BLE device
PYTHONPATH=src .venv/bin/python -m kitchen_robot ble-scan

# Safe ESP32 command: asks firmware for status, does not move the motor
PYTHONPATH=src .venv/bin/python -m kitchen_robot stirrer-command status

# Emergency stop
PYTHONPATH=src .venv/bin/python -m kitchen_robot stirrer-command emergency_stop
```

If BLE scan times out on macOS, allow Bluetooth access for the terminal/Codex app in System Settings, then retry.

`KitchenStirrer` is a BLE GATT device, not a headphone-style pairing device. It may not appear in the normal macOS/iPhone Bluetooth settings screen. Use the GUI BLE scan or a BLE scanner app such as nRF Connect to verify advertising.

The GUI opens at:

```text
http://127.0.0.1:8787
```

## ESP32 Firmware

The initial firmware sketch lives in:

```text
firmware/esp32_stirrer_ble/esp32_stirrer_ble.ino
```

ESP32-C3 supports BLE, so Testing 1 uses a BLE UART-style service rather than classic Bluetooth serial.

Compile and upload to the ESP32-C3:

```bash
arduino-cli compile --fqbn "esp32:esp32:esp32c3:CDCOnBoot=cdc" firmware/esp32_stirrer_ble
arduino-cli upload -p /dev/cu.usbmodem21101 --fqbn "esp32:esp32:esp32c3:CDCOnBoot=cdc" firmware/esp32_stirrer_ble
```

After upload, the ESP32 prints startup logs at `115200` baud. Look for:

```text
KitchenStirrer booting
KitchenStirrer BLE advertising started
```
