# Kitchen Robot Testing 1 PRD

## 1. Product Summary

Kitchen Robot Testing 1 is a laptop-run proof of concept for a voice-first cooking assistant. It guides a human through a fixed upma recipe, observes the kadai using live video, and controls a stirrer through an ESP32-S3.

Testing 1 is not the final product. It proves the core loop:

```text
Listen -> Observe -> Reason -> Guide -> Stir -> Check safety -> Continue
```

## 2. Primary Goal

Build a working prototype that can:

1. Run on a macOS laptop.
2. Guide a fixed upma recipe.
3. Use an external camera for live video observation.
4. Use an external mic for voice input.
5. Speak through a Bose AUX speaker.
6. Send Bluetooth commands to an ESP32-S3.
7. Control a NEMA 17 stepper motor through an A4988 driver.
8. Stop stirring immediately when safety requires it.

## 3. Non-Goals For Testing 1

Testing 1 will not:

- Run on Android phone as the main computer.
- Control stove heat.
- Add ingredients automatically.
- Support multiple recipes.
- Build a polished mobile app.
- Build the full admin capability editor.
- Fully solve all multilingual voice polish.
- Fully automate cooking without human supervision.

## 4. Users

### Primary User

The builder/tester cooking upma beside the laptop and kadai.

### Human Role

The human:

- Adds ingredients.
- Controls heat.
- Places and removes utensils.
- Confirms uncertain steps.
- Can stop the robot at any time.

### Robot Role

The robot:

- Gives spoken instructions.
- Watches the kadai.
- Reasons about recipe stage.
- Stirs when safe.
- Stops when unsafe.

## 5. Hardware Requirements

### Laptop Side

- macOS laptop
- External camera
- External microphone
- Bose speaker through AUX
- Internet connection for API calls

### Robot Side

- ESP32-S3 DevKit N16R8
- NEMA 17 stepper motor
- A4988 stepper driver
- 12V 2500mAh LiPo battery
- Existing test mount

## 6. Software Architecture

The architecture uses sub-agents, an orchestrator, and a reasoning agent.

```text
Sub-agents <-> Orchestrator Agent <-> Main Reasoning Agent
```

### Rule

The Main Reasoning Agent does not directly control hardware. It only reasons and advises.

The Orchestrator coordinates the system.

Sub-agents do the actual work.

## 7. Agents

### Orchestrator Agent

Responsibilities:

- Owns the session loop.
- Routes messages between agents.
- Tracks current recipe step.
- Sends observations to the Main Reasoning Agent.
- Sends tasks to sub-agents.
- Keeps action ordering clear.

### Main Reasoning Agent

Responsibilities:

- Understands cooking context.
- Interprets summarized observations.
- Decides whether a step likely advanced.
- Produces advice in structured form.

Does not:

- Send BLE commands.
- Speak directly.
- Read camera directly.
- Control the motor directly.

### Recipe Agent

Responsibilities:

- Stores fixed upma recipe.
- Provides current step.
- Advances when the Orchestrator accepts step completion.

### Vision Agent

Responsibilities:

- Uses live camera feed.
- Observes short video windows.
- Sends compact observations to the Orchestrator.
- Checks recipe goals such as light browning, water added, thickening.

### Safety Agent

Responsibilities:

- Watches for unsafe conditions.
- Stops stirring when a hand comes near pan boundaries.
- Supports emergency stop.

### Voice Listen Agent

Responsibilities:

- Listens for wake word: `Hey Robot`.
- Opens active listening mode for 15 seconds.
- Sends transcribed user speech to the Orchestrator.

### Speech Agent

Responsibilities:

- Speaks robot instructions.
- Uses human-like API TTS.
- Replies in the user's latest language style where possible.

### Stirring Agent

Responsibilities:

- Converts recipe needs into stir commands.
- Chooses high-level commands like slow/medium/stop.
- Sends emergency stop when safety requires it.

### ESP32 BLE Agent

Responsibilities:

- Connects to ESP32 over BLE.
- Sends serialized motor commands.
- Receives status where available.

## 8. Voice Requirements

### Wake Word

Wake word: `Hey Robot`

### Listening Window

After wake word, robot listens normally for 15 seconds.

### Languages

Testing 1 should be designed for:

- English
- Hindi
- Hinglish
- Telugu
- Telugish

The robot should reply in the user's most recent language style where possible.

## 9. Vision Requirements

### Input

The camera feed is live video, not a single photo interaction.

### Cost Control

The system should not send every frame to the AI API. It should:

- Keep live video active locally.
- Analyze short video windows.
- Sample frames from those windows.
- Send compact visual context to the model.

This preserves live observation while avoiding unnecessary token/API cost.

## 10. Stirring Requirements

The system must support:

- `stop`
- `emergency_stop`
- `start_profile slow`
- `start_profile medium`
- `start_profile fast`
- low-level delay-based start
- `reverse`
- `status`

Default Testing 1 behavior:

- Auto-stir for normal recipe steps.
- Ask confirmation when uncertain.
- Stop immediately for safety.

## 11. Safety Requirements

The robot must stop stirring when:

- A hand comes near pan boundaries.
- Emergency stop is triggered.
- ESP32/BLE status is unsafe or unknown.
- Vision confidence is too low for an automatic action.

Motor current and A4988 current limit must be tested carefully before cooking with load.

## 12. Testing 1 Recipe

Recipe: fixed upma.

High-level steps:

1. Prepare kadai and oil.
2. Add tempering ingredients.
3. Add and roast suji until light brown.
4. Add water slowly.
5. Cook and stir until thickened.
6. Finish and turn off heat.

## 13. Milestones

### M1: Project Skeleton

Deliverables:

- Python package.
- README.
- Config file.
- Agent message types.
- Mock orchestrator loop.

Acceptance:

- Mock app starts and routes events.

### M2: Recipe And Agent Flow

Deliverables:

- Fixed upma recipe.
- Recipe Agent.
- Main Reasoning Agent interface.
- Speech/Stirring/Vision placeholders.

Acceptance:

- Mock flow speaks recipe steps and creates stir commands.

### M3: ESP32 Firmware And BLE Commands

Deliverables:

- ESP32-S3 firmware sketch.
- BLE service.
- Motor command parser.
- Laptop BLE sender.

Acceptance:

- Laptop can send `stop`, `start_profile slow`, and `emergency_stop`.

### M4: Live Video Observation

Deliverables:

- External camera capture.
- Short live video window sampler.
- Vision model adapter.

Acceptance:

- System can inspect camera view and return structured observation.

### M5: Speech Output

Deliverables:

- TTS API integration.
- macOS audio playback.

Acceptance:

- Robot speaks a recipe instruction through selected audio output.

### M6: Voice Input

Deliverables:

- Wake-word flow.
- 15 second active listening.
- STT API integration.

Acceptance:

- User can wake robot and say a simple command.

### M7: Safety Stop

Deliverables:

- Hand-near-pan detection strategy.
- Safety Agent event.
- Emergency stop path to ESP32.

Acceptance:

- Safety event immediately sends `emergency_stop`.

### M8: First Dry Run

Deliverables:

- Run without heat or food.
- Camera, voice, BLE, and motor tested together.

Acceptance:

- Robot can speak, observe, and start/stop motor safely.

### M9: First Cooking Test

Deliverables:

- Guided upma test with human supervision.

Acceptance:

- Robot guides steps, stirs at expected stages, and stops safely.

## 14. Current Status

Completed:

- M1 Project Skeleton
- M2 Recipe And Agent Flow
- Project virtual environment setup
- Dependency install
- Pytest, lint, and mock app verification
- Part of M3 ESP32 Firmware And BLE Commands
- Part of M4 Live Video Observation
- Part of M5 Speech Output

Not yet complete:

- ESP32 flashing
- Real BLE board test
- Real camera test
- Real TTS audio test
- Wake-word and STT
- Safety vision implementation
- Dry run
- Cooking test

## 15. Build Rule

After every major step, summarize:

1. What was done.
2. Why it was done.
3. What changed.
4. Simple explanation for an 8-year-old.
