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
- Arm servo: 1x SG90 micro servo
- Recipe: fixed upma
- Human actions: add ingredients and control heat
- Robot actions: stirring and lift up/down

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
- ESP32 Wired Serial Agent
- Main Reasoning Agent

## Quick Start

```bash
/Users/pbl/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
PYTHONPATH=src python -m kitchen_robot run --mock
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

# Find the wired ESP32-C3 serial port
PYTHONPATH=src .venv/bin/python -m kitchen_robot serial-scan

# Safe wired command: asks firmware for status, does not move the motor
PYTHONPATH=src .venv/bin/python -m kitchen_robot wired-command status

# Emergency stop
PYTHONPATH=src .venv/bin/python -m kitchen_robot wired-command emergency_stop

# Move the SG90 lift servo
PYTHONPATH=src .venv/bin/python -m kitchen_robot wired-command servo --value "lift up"
PYTHONPATH=src .venv/bin/python -m kitchen_robot wired-command servo --value "lift down"
PYTHONPATH=src .venv/bin/python -m kitchen_robot wired-command servo --value "home"
PYTHONPATH=src .venv/bin/python -m kitchen_robot wired-command servo --value "sweep"
```

Wired USB serial is the primary Testing 1 motor-control path. Bluetooth is not required.

The GUI opens at:

```text
http://127.0.0.1:8787
```

## ESP32 Firmware

The initial firmware sketch lives in:

```text
firmware/esp32_stirrer_ble/esp32_stirrer_ble.ino
```

Testing 1 uses USB serial as the primary control path. BLE support remains in the firmware as a secondary/debug path.

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

The firmware accepts these USB serial commands at `115200` baud:

```text
status
stop
emergency_stop
start_profile slow
start_profile medium
start_profile fast
reverse
start 2500
servo lift up
servo lift down
servo home
servo sweep
```

Default SG90 wiring in the firmware:

```text
Lift servo signal: GPIO7
Backup lift signal: GPIO10
Servo power: external 5V supply
Servo ground: shared with ESP32-C3 ground
```

The firmware mirrors the same lift servo signal on `GPIO7` and `GPIO10` for Testing 1 debugging. Use one signal wire only. Do not power the SG90 servo from the ESP32-C3 3.3V pin. Use a separate 5V servo supply and connect grounds together.

## API Key

Do not paste API keys into chat. Put the key in a local `.env` file:

```bash
cp .env.example .env
```

Then edit `.env` and set:

```text
OPENAI_API_KEY=your_key_here
```
