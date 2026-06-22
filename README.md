# Kitchen Robot - Testing 1

Testing 1 is a laptop-run proof of concept for a voice-first kitchen robot that guides a fixed upma recipe and controls a stirrer through an ESP32-S3.

The product requirements and milestone plan live in:

```text
docs/PRD.md
```

## Scope

- Runtime: macOS laptop
- Camera: external camera, diagonal top view of a kadai
- Voice input: external microphone
- Voice output: Bose speaker through AUX
- Controller: ESP32-S3 DevKit N16R8
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
PYTHONPATH=src .venv/bin/python -m kitchen_robot --mock
```

## ESP32 Firmware

The initial firmware sketch lives in:

```text
firmware/esp32_stirrer_ble/esp32_stirrer_ble.ino
```

ESP32-S3 supports BLE, so Testing 1 uses a BLE UART-style service rather than classic Bluetooth serial.
