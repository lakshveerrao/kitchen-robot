import argparse
import asyncio
import base64
import contextlib
import io
import json
from multiprocessing import Queue, get_context
import os
from pathlib import Path
from queue import Empty
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

from kitchen_robot.config import Settings
from kitchen_robot.operator import (
    ble_scan,
    serial_scan,
    stirrer_command,
    wired_stirrer_command,
)


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kitchen Robot Testing 1</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #667085;
      --line: #d7dde5;
      --accent: #0f766e;
      --danger: #b42318;
      --warn: #b54708;
      --ok: #027a48;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }

    header {
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }

    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
    }

    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }

    .wide { grid-column: 1 / -1; }

    h2 {
      margin: 0 0 12px;
      font-size: 15px;
      font-weight: 700;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    button {
      min-height: 42px;
      border: 1px solid var(--line);
      background: #ffffff;
      border-radius: 6px;
      color: var(--text);
      font-size: 14px;
      font-weight: 650;
      cursor: pointer;
    }

    button:hover { border-color: var(--accent); }
    button.primary { background: var(--accent); color: white; border-color: var(--accent); }
    button.danger { background: var(--danger); color: white; border-color: var(--danger); }
    button.warn { background: #fff7ed; color: var(--warn); border-color: #fed7aa; }
    button:disabled { opacity: 0.55; cursor: wait; }

    label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
    }

    input, select {
      width: 100%;
      min-height: 38px;
      border-radius: 6px;
      border: 1px solid var(--line);
      padding: 0 10px;
      font-size: 14px;
      background: white;
      color: var(--text);
    }

    .field-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 12px;
    }

    .status {
      display: inline-flex;
      align-items: center;
      min-height: 30px;
      padding: 0 10px;
      border-radius: 999px;
      background: #eef4ff;
      color: #3538cd;
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
    }

    .status.ok { background: #ecfdf3; color: var(--ok); }
    .status.error { background: #fef3f2; color: var(--danger); }
    .status.busy { background: #fffaeb; color: var(--warn); }

    .steps {
      margin: 0;
      padding-left: 22px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.65;
    }

    .steps strong {
      color: var(--text);
    }

    .camera-box {
      display: grid;
      gap: 10px;
    }

    video {
      width: 100%;
      aspect-ratio: 16 / 9;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #101828;
      object-fit: cover;
    }

    .hint {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .agent-strip {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      margin-top: 12px;
    }

    .agent-pill {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      font-size: 12px;
      color: var(--muted);
      background: #ffffff;
    }

    .agent-pill strong {
      display: block;
      color: var(--text);
      font-size: 12px;
      margin-bottom: 2px;
    }

    .session-status {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
    }

    pre {
      margin: 0;
      min-height: 280px;
      max-height: 420px;
      overflow: auto;
      padding: 14px;
      border-radius: 8px;
      background: #111827;
      color: #e5e7eb;
      line-height: 1.45;
      font-size: 13px;
      white-space: pre-wrap;
    }

    @media (max-width: 760px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; padding: 14px; }
      .field-row, .grid, .agent-strip, .session-status { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Kitchen Robot Testing 1</h1>
    <span id="state" class="status">Ready</span>
  </header>

  <main>
    <section>
      <h2>Readiness</h2>
      <div class="field-row">
        <div>
          <label for="cameraIndex">Camera index</label>
          <input id="cameraIndex" type="number" value="0" min="0">
        </div>
        <div>
          <label for="seconds">Video seconds</label>
          <input id="seconds" type="number" value="2" min="1" max="10" step="0.5">
        </div>
      </div>
      <div class="grid">
        <button data-action="camera-check">Check Python Camera</button>
        <button data-action="ask-browser-camera" class="primary">Ask Chrome Camera Permission</button>
        <button data-action="browser-camera-check">Check Browser Camera</button>
        <button data-action="serial-scan">Find Wired ESP32</button>
        <button data-action="api-check">Check API Key</button>
      </div>
    </section>

    <section>
      <h2>Camera Preview</h2>
      <div class="camera-box">
        <video id="cameraPreview" autoplay playsinline muted></video>
        <canvas id="cameraCanvas" hidden></canvas>
        <div class="hint">
          Use Google Chrome and click <strong>Ask Chrome Camera Permission</strong>. When Chrome asks, choose Allow.
        </div>
      </div>
    </section>

    <section>
      <h2>Stirrer</h2>
      <div class="field-row">
        <div>
          <label for="profile">Profile</label>
          <select id="profile">
            <option value="slow">slow</option>
            <option value="medium">medium</option>
            <option value="fast">fast</option>
          </select>
        </div>
        <div>
          <label for="delay">Delay micros</label>
          <input id="delay" type="number" value="2500" min="800">
        </div>
      </div>
      <div class="grid">
        <button data-action="wired-status">Status</button>
        <button data-action="wired-stop" class="warn">Stop</button>
        <button data-action="wired-start-profile" class="primary">Start Profile</button>
        <button data-action="wired-reverse">Reverse</button>
        <button data-action="wired-start-delay">Start Delay</button>
        <button data-action="wired-emergency" class="danger">Emergency Stop</button>
      </div>
    </section>

    <section class="wide">
      <h2>Session</h2>
      <div class="grid">
        <button data-action="upma-mode" class="primary">Start Upma Live</button>
        <button data-action="voice-control" class="primary">Start Voice Control</button>
        <button data-action="upma-next">Next Step</button>
        <button data-action="upma-analyze">Analyze Now</button>
        <button data-action="upma-stop" class="danger">Stop Upma Live</button>
        <button data-action="mock-run" class="primary">Run Mock Recipe</button>
        <button data-action="clear-log">Clear Log</button>
      </div>
      <div class="session-status">
        <div><strong>Current step:</strong> <span id="currentStep">Not started</span></div>
        <div><strong>Vision:</strong> <span id="visionState">Idle</span></div>
      </div>
      <div class="agent-strip">
        <div class="agent-pill"><strong>Voice</strong><span id="voiceAgent">Browser speech ready</span></div>
        <div class="agent-pill"><strong>Vision</strong><span id="visionAgent">Chrome frames</span></div>
        <div class="agent-pill"><strong>Main</strong><span id="mainAgent">Waiting</span></div>
        <div class="agent-pill"><strong>Stirring</strong><span id="stirAgent">USB wired</span></div>
        <div class="agent-pill"><strong>Safety</strong><span id="safetyAgent">Emergency stop ready</span></div>
      </div>
    </section>

    <section class="wide">
      <h2>Main Steps</h2>
      <ol class="steps">
        <li><strong>Safe motor test:</strong> check slow stir, stop, and emergency stop.</li>
        <li><strong>Camera check:</strong> confirm the kadai is clearly visible.</li>
        <li><strong>Vision agent:</strong> detect upma stages like suji added, light brown, water added, and thickened.</li>
        <li><strong>Speech output:</strong> speak recipe instructions through the speaker.</li>
        <li><strong>Voice input:</strong> add wake word and speech-to-text.</li>
        <li><strong>Safety agent:</strong> stop stirring if a hand comes near the pan.</li>
        <li><strong>Dry run:</strong> run full upma flow without heat or food.</li>
        <li><strong>Cooking test:</strong> cook upma with human supervision.</li>
      </ol>
    </section>

    <section class="wide">
      <h2>Upma Mode</h2>
      <ol class="steps">
        <li><strong>Prepare:</strong> place the kadai on heat and add oil.</li>
        <li><strong>Temper:</strong> add mustard seeds, curry leaves, green chili, and onion. Robot stirs slowly.</li>
        <li><strong>Roast suji:</strong> add suji. Robot stirs at medium speed and watches for light brown color.</li>
        <li><strong>Add water:</strong> when suji is light brown, robot asks you to add water slowly while it stirs.</li>
        <li><strong>Thicken:</strong> robot keeps slow stirring until the upma pulls together.</li>
        <li><strong>Finish:</strong> robot tells you to turn off heat and stops stirring.</li>
      </ol>
    </section>

    <section class="wide">
      <h2>Setup Notes</h2>
      <div style="color: var(--muted); font-size: 14px; line-height: 1.55;">
        Wired mode is the primary Testing 1 path. Keep the ESP32-C3 connected over USB. The app auto-detects the
        Espressif serial port and sends commands at <strong>115200 baud</strong>. Use <strong>Find Wired ESP32</strong>
        first, then <strong>Status</strong>.
      </div>
    </section>

    <section class="wide">
      <h2>Log</h2>
      <pre id="log">Waiting for command...</pre>
    </section>
  </main>

  <script>
    const log = document.getElementById("log");
    const state = document.getElementById("state");
    const cameraPreview = document.getElementById("cameraPreview");
    const cameraCanvas = document.getElementById("cameraCanvas");
    const currentStep = document.getElementById("currentStep");
    const visionState = document.getElementById("visionState");
    const voiceAgent = document.getElementById("voiceAgent");
    const visionAgent = document.getElementById("visionAgent");
    const mainAgent = document.getElementById("mainAgent");
    const stirAgent = document.getElementById("stirAgent");
    const safetyAgent = document.getElementById("safetyAgent");
    let browserCameraStream = null;
    let upmaRunning = false;
    let upmaStepIndex = 0;
    let upmaTimer = null;
    let upmaBusy = false;
    let upmaWaitingForAction = false;
    let upmaSafetyPaused = false;
    let voiceRecognition = null;
    let voiceActiveUntil = 0;
    let voiceListening = false;

    const UPMA_SAMPLE_MS = 9000;
    const UPMA_CONFIDENCE_TO_ADVANCE = 0.65;
    const UPMA_RECIPE = [
      {
        step_id: "prepare",
        label: "Prepare",
        instruction: "Place the kadai on heat and add oil.",
        human_action: "Add oil to the kadai.",
        action_goal: "oil has been added to the kadai",
        stir_mode: null,
        vision_goal: "kadai visible with oil added"
      },
      {
        step_id: "temper",
        label: "Temper",
        instruction: "Add mustard seeds, curry leaves, green chili, and onion.",
        human_action: "Add tempering ingredients.",
        action_goal: "mustard seeds, curry leaves, green chili, and onion have been added",
        stir_mode: "slow",
        vision_goal: "onion starts softening"
      },
      {
        step_id: "roast_suji",
        label: "Roast suji",
        instruction: "Add suji. I will stir while it roasts until light brown.",
        human_action: "Add suji.",
        action_goal: "suji has been added to the kadai",
        stir_mode: "medium",
        vision_goal: "suji turns light brown"
      },
      {
        step_id: "add_water",
        label: "Add water",
        instruction: "The suji looks ready. Add water slowly while I stir.",
        human_action: "Add water slowly.",
        action_goal: "water has been added to the suji",
        stir_mode: "slow",
        vision_goal: "water added and mixture bubbling"
      },
      {
        step_id: "cook_thicken",
        label: "Thicken",
        instruction: "Let it cook while I stir until it thickens.",
        human_action: "",
        action_goal: "",
        stir_mode: "slow",
        vision_goal: "upma thickened and pulling together"
      },
      {
        step_id: "finish",
        label: "Finish",
        instruction: "Upma looks done. Turn off the heat.",
        human_action: "Turn off heat.",
        action_goal: "heat is turned off or cooking is finished",
        stir_mode: null,
        vision_goal: "finished upma consistency"
      }
    ];

    function setState(text, cls = "") {
      state.className = `status ${cls}`.trim();
      state.textContent = text;
    }

    function appendLog(title, body) {
      const time = new Date().toLocaleTimeString();
      if (log.textContent === "Waiting for command...") log.textContent = "";
      log.textContent += `[${time}] ${title}\\n${body}\\n\\n`;
      log.scrollTop = log.scrollHeight;
    }

    function speak(text) {
      if (!("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
      voiceAgent.textContent = "Speaking";
    }

    function setAgentText(element, text) {
      element.textContent = text;
    }

    function startVoiceControl() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        appendLog("Voice Agent", "Speech recognition is not available in this browser. Use Google Chrome.");
        setAgentText(voiceAgent, "Not supported");
        return;
      }

      if (voiceRecognition && voiceListening) {
        appendLog("Voice Agent", "Voice control is already listening.");
        return;
      }

      voiceRecognition = new SpeechRecognition();
      voiceRecognition.continuous = true;
      voiceRecognition.interimResults = false;
      voiceRecognition.lang = "en-IN";

      voiceRecognition.onstart = () => {
        voiceListening = true;
        voiceActiveUntil = Date.now() + 15000;
        setAgentText(voiceAgent, "Listening");
        appendLog("Voice Agent", "Listening. Say 'hey robot', then commands like start upma, added, analyze, next, stop.");
      };

      voiceRecognition.onend = () => {
        voiceListening = false;
        setAgentText(voiceAgent, "Voice idle");
        if (upmaRunning) {
          try {
            voiceRecognition.start();
          } catch (error) {
            appendLog("Voice Agent", `Could not restart listening: ${error}`);
          }
        }
      };

      voiceRecognition.onerror = event => {
        appendLog("Voice Agent Error", event.error || "unknown error");
        setAgentText(voiceAgent, "Voice error");
      };

      voiceRecognition.onresult = event => {
        const latest = event.results[event.results.length - 1];
        const transcript = latest[0].transcript.trim();
        handleVoiceText(transcript);
      };

      try {
        voiceRecognition.start();
      } catch (error) {
        appendLog("Voice Agent Error", String(error));
      }
    }

    function handleVoiceText(transcript) {
      const text = transcript.toLowerCase();
      appendLog("Voice Heard", transcript);
      const woke = text.includes("hey robot") || text.includes("hai robot") || text.includes("robot");
      if (woke) {
        voiceActiveUntil = Date.now() + 15000;
        setAgentText(voiceAgent, "Awake");
      }

      const active = woke || Date.now() < voiceActiveUntil;
      if (!active) return;

      voiceActiveUntil = Date.now() + 15000;
      if (text.includes("emergency") || text.includes("stop now") || text === "stop" || text.includes("band karo")) {
        stopUpmaLive(true);
        return;
      }
      if (text.includes("clear") || text.includes("cleared") || text.includes("continue") || text.includes("resume") || text.includes("safe")) {
        resumeAfterSafety();
        return;
      }
      if (text.includes("start upma") || text.includes("make upma") || text.includes("upma start")) {
        runUpmaMode();
        return;
      }
      if (text.includes("added") || text.includes("i add") || text.includes("done") || text.includes("add kiya") || text.includes("डाल")) {
        userSaysAdded();
        return;
      }
      if (text.includes("analyze") || text.includes("check") || text.includes("देख")) {
        analyzeUpmaStep(true);
        return;
      }
      if (text.includes("next")) {
        nextUpmaStep();
      }
    }

    async function startBrowserCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("This browser does not support camera access. Open http://127.0.0.1:8787/ in Google Chrome.");
      }

      if (!browserCameraStream) {
        browserCameraStream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "environment"
          },
          audio: false
        });
        cameraPreview.srcObject = browserCameraStream;
      }

      await cameraPreview.play();
      return browserCameraStream;
    }

    function captureBrowserFrame() {
      if (!browserCameraStream || !cameraPreview.videoWidth) {
        throw new Error("Camera is not ready. Click Ask Chrome Camera Permission first.");
      }

      cameraCanvas.width = cameraPreview.videoWidth;
      cameraCanvas.height = cameraPreview.videoHeight;
      const context = cameraCanvas.getContext("2d");
      context.drawImage(cameraPreview, 0, 0, cameraCanvas.width, cameraCanvas.height);
      return cameraCanvas.toDataURL("image/jpeg", 0.72);
    }

    async function askBrowserCamera() {
      setState("Asking Camera", "busy");
      try {
        await startBrowserCamera();
        appendLog(
          "OK",
          `Chrome camera permission is working. Preview size: ${cameraPreview.videoWidth}x${cameraPreview.videoHeight}`
        );
        setState("Ready", "ok");
      } catch (error) {
        appendLog("Camera Permission Problem", String(error));
        setState("Needs Attention", "error");
      }
    }

    async function browserCameraCheck() {
      try {
        await startBrowserCamera();
        const frameJpeg = captureBrowserFrame();
        await callApi("/api/browser-camera-check", { frame_jpeg: frameJpeg });
      } catch (error) {
        appendLog("Camera Error", String(error));
        setState("Error", "error");
      }
    }

    async function runUpmaMode() {
      try {
        await startBrowserCamera();
        upmaRunning = true;
        upmaStepIndex = 0;
        appendLog("Upma Live", "Started live Upma mode with Chrome camera and wired stirrer.");
        await enterUpmaStep(0);
      } catch (error) {
        appendLog("Camera Error", String(error));
        setState("Error", "error");
      }
    }

    function currentUpmaStep() {
      return UPMA_RECIPE[upmaStepIndex];
    }

    async function enterUpmaStep(index) {
      if (!upmaRunning) return;
      upmaStepIndex = Math.min(index, UPMA_RECIPE.length - 1);
      const step = currentUpmaStep();
      currentStep.textContent = `${step.label}: ${step.vision_goal}`;
      upmaWaitingForAction = Boolean(step.human_action);
      visionState.textContent = upmaWaitingForAction ? "Waiting for add" : "Waiting for sample";
      setAgentText(mainAgent, "Guiding");
      setAgentText(visionAgent, "Chrome camera ready");

      const message = step.human_action ? `${step.instruction} ${step.human_action}` : step.instruction;
      appendLog("Recipe Agent", `${step.label}\\n${message}`);
      speak(message);
      if (upmaWaitingForAction) {
        setAgentText(mainAgent, "Waiting while user adds");
        setAgentText(stirAgent, "Paused for adding");
        await applyStirMode(null);
      } else {
        await applyStirMode(step.stir_mode);
      }

      clearTimeout(upmaTimer);
      upmaTimer = setTimeout(() => analyzeUpmaStep(false), upmaWaitingForAction ? 3500 : 1200);
    }

    async function applyStirMode(stirMode) {
      if (stirMode) {
        setAgentText(stirAgent, `Starting ${stirMode}`);
        await callApi("/api/wired-start-profile", { profile: stirMode }, { keepControlsEnabled: true });
      } else {
        setAgentText(stirAgent, "Stopping");
        await callApi("/api/wired-stop", {}, { keepControlsEnabled: true });
      }
    }

    async function analyzeUpmaStep(manual) {
      if (!upmaRunning || upmaBusy || upmaSafetyPaused) return;
      upmaBusy = true;
      const step = { ...currentUpmaStep() };
      step.phase = upmaWaitingForAction ? "awaiting_human_addition" : "cooking_stage";
      step.active_goal = upmaWaitingForAction ? step.action_goal : step.vision_goal;
      try {
        await startBrowserCamera();
        const frameJpeg = captureBrowserFrame();
        visionState.textContent = upmaWaitingForAction ? "Checking added" : (manual ? "Manual analyze" : "Sampling");
        setAgentText(visionAgent, "Sending one frame");
        const data = await callApi("/api/browser-vision-check", {
          frame_jpeg: frameJpeg,
          step
        }, { keepControlsEnabled: true, quietFailure: true, background: !manual });

        if (!data || !data.ok) {
          visionState.textContent = "Cloud slow";
          setAgentText(visionAgent, "Cloud slow; continuing");
          setAgentText(mainAgent, upmaWaitingForAction ? "Waiting for added" : "Watching");
          appendLog("Vision Agent", data?.output || "Cloud vision did not answer yet. Continuing without freezing.");
          clearTimeout(upmaTimer);
          upmaTimer = setTimeout(() => analyzeUpmaStep(false), upmaWaitingForAction ? 6000 : UPMA_SAMPLE_MS * 2);
          return;
        }
        const observation = data.observation || {};
        const confidence = Number(observation.confidence || 0);
        const summary = observation.summary || "No summary";
        const safetyNotes = observation.safety_notes || "";
        const safetyStop = Boolean(observation.safety_stop);
        visionState.textContent = `${confidence.toFixed(2)} confidence`;
        setAgentText(visionAgent, summary);
        setAgentText(mainAgent, observation.goal_met ? "Stage ready" : "Keep watching");

        if (isUnsafeObservation(safetyStop, safetyNotes, summary)) {
          appendLog("Safety Agent", `Possible unsafe condition: ${safetyNotes || summary}`);
          speak("Safety stop. Please clear the area, then say cleared or continue.");
          await pauseForSafety(safetyNotes || summary);
          return;
        }

        if (observation.goal_met && confidence >= UPMA_CONFIDENCE_TO_ADVANCE) {
          if (upmaWaitingForAction) {
            upmaWaitingForAction = false;
            appendLog("Main Agent", `I detected the add step for ${step.label}. Now I will stir and watch the cooking stage.\\n${summary}`);
            speak("Detected. Stirring now.");
            await applyStirMode(currentUpmaStep().stir_mode);
            clearTimeout(upmaTimer);
            upmaTimer = setTimeout(() => analyzeUpmaStep(false), UPMA_SAMPLE_MS);
            return;
          }

          appendLog("Main Agent", `Goal met for ${step.label}. Moving to next step.\\n${summary}`);
          if (upmaStepIndex >= UPMA_RECIPE.length - 1) {
            await stopUpmaLive(false);
            speak("Upma flow is complete.");
            return;
          }
          await enterUpmaStep(upmaStepIndex + 1);
          return;
        }

        appendLog("Vision Agent", `Still watching ${step.label}.\\n${summary}`);
        clearTimeout(upmaTimer);
        upmaTimer = setTimeout(() => analyzeUpmaStep(false), upmaWaitingForAction ? 6000 : UPMA_SAMPLE_MS);
      } finally {
        upmaBusy = false;
      }
    }

    function isUnsafeObservation(safetyStop, safetyNotes, summary) {
      const text = `${safetyNotes || ""} ${summary || ""}`.toLowerCase();
      return safetyStop || ["hand", "finger", "burn", "burning", "smoke", "fire", "blackening", "cloth", "cable"].some(word => text.includes(word));
    }

    async function pauseForSafety(reason) {
      upmaSafetyPaused = true;
      clearTimeout(upmaTimer);
      upmaTimer = null;
      visionState.textContent = "Safety paused";
      setAgentText(mainAgent, "Paused for safety");
      setAgentText(safetyAgent, reason || "Unsafe object detected");
      setAgentText(stirAgent, "Emergency stop");
      await callApi("/api/wired-emergency", {}, { keepControlsEnabled: true });
      appendLog("Upma Live", "Paused for safety. Clear the area, then say cleared or continue.");
    }

    async function resumeAfterSafety() {
      if (!upmaRunning) {
        appendLog("Safety Agent", "Nothing is running to resume.");
        return;
      }
      if (!upmaSafetyPaused) {
        appendLog("Safety Agent", "No active safety pause. Continuing normal watch.");
        analyzeUpmaStep(true);
        return;
      }

      appendLog("Safety Agent", "User says area is clear. Checking once before continuing.");
      speak("Checking safety. If clear, I will continue.");
      setAgentText(safetyAgent, "Checking clear");
      upmaSafetyPaused = false;
      const wasBusy = upmaBusy;
      upmaBusy = false;
      await analyzeUpmaStep(true);
      upmaBusy = wasBusy && upmaBusy;
      if (!upmaSafetyPaused) {
        setAgentText(safetyAgent, "Clear");
        speak("Continuing.");
        if (!upmaWaitingForAction && currentUpmaStep().stir_mode) {
          await applyStirMode(currentUpmaStep().stir_mode);
        }
        clearTimeout(upmaTimer);
        upmaTimer = setTimeout(() => analyzeUpmaStep(false), 2000);
      }
    }

    function userSaysAdded() {
      if (!upmaRunning) {
        appendLog("Voice Agent", "I heard added, but Upma Live is not running.");
        return;
      }
      if (!upmaWaitingForAction) {
        appendLog("Voice Agent", "I heard added. I am already in the cooking/watch phase.");
        analyzeUpmaStep(true);
        return;
      }

      upmaWaitingForAction = false;
      visionState.textContent = "User confirmed add";
      const step = currentUpmaStep();
      const actionOnlyStep = !step.stir_mode;
      setAgentText(mainAgent, actionOnlyStep ? "Accepted; next step" : "Accepted; stirring now");
      setAgentText(visionAgent, "Cloud verify in background");
      if (actionOnlyStep) {
        appendLog("Voice Agent", "User said the ingredient was added. Moving to the next step.");
        speak("Okay. Moving to the next step.");
        enterUpmaStep(upmaStepIndex + 1);
        return;
      }

      appendLog("Voice Agent", "User said the ingredient was added. Starting stir now. Cloud vision will verify in the background.");
      speak("Okay. Stirring now.");
      applyStirMode(step.stir_mode).then(() => {
        clearTimeout(upmaTimer);
        upmaTimer = setTimeout(() => analyzeUpmaStep(false), 2000);
      });
    }

    async function nextUpmaStep() {
      if (!upmaRunning) {
        appendLog("Upma Live", "Start Upma Live first.");
        return;
      }
      await enterUpmaStep(upmaStepIndex + 1);
    }

    async function stopUpmaLive(emergency) {
      upmaRunning = false;
      upmaWaitingForAction = false;
      upmaSafetyPaused = false;
      clearTimeout(upmaTimer);
      upmaTimer = null;
      currentStep.textContent = "Stopped";
      visionState.textContent = "Idle";
      setAgentText(mainAgent, "Stopped");
      setAgentText(stirAgent, emergency ? "Emergency stop" : "Stop");
      await callApi(emergency ? "/api/wired-emergency" : "/api/wired-stop", {}, { keepControlsEnabled: true });
      appendLog("Upma Live", emergency ? "Emergency stopped." : "Stopped.");
    }

    function timeoutForAction(path, payload) {
      if (path.includes("browser-camera-check")) return 12000;
      if (path.includes("browser-vision-check")) return 18000;
      if (path.includes("camera-check")) return Math.max(12000, (Number(payload.seconds) + 8) * 1000);
      if (path.includes("upma-mode")) return 25000;
      return 12000;
    }

    function setButtonsDisabled(disabled, keepControlsEnabled) {
      document.querySelectorAll("button").forEach(button => {
        const action = button.dataset.action || "";
        const alwaysEnabled = [
          "wired-emergency",
          "wired-stop",
          "upma-stop",
          "upma-next",
          "upma-analyze",
          "clear-log"
        ].includes(action);
        button.disabled = disabled && !(keepControlsEnabled && alwaysEnabled);
      });
    }

    async function callApi(path, payload = {}, options = {}) {
      if (!options.background) setState("Running", "busy");
      setButtonsDisabled(true, Boolean(options.keepControlsEnabled));
      const controller = new AbortController();
      const timeoutMs = timeoutForAction(path, payload);
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal
        });
        const data = await response.json();
        if (data.ok || !options.quietFailure) {
          appendLog(data.ok ? "OK" : "Problem", data.output || data.error || "");
        }
        if (!options.background) setState(data.ok ? "Ready" : "Needs Attention", data.ok ? "ok" : "error");
        return data;
      } catch (error) {
        const message = error.name === "AbortError"
          ? "This step took too long and was stopped. Check camera permission/port, then try again."
          : String(error);
        if (!options.quietFailure) appendLog("Error", message);
        if (!options.background) setState("Error", "error");
        return { ok: false, output: message };
      } finally {
        clearTimeout(timer);
        setButtonsDisabled(false, false);
      }
    }

    document.addEventListener("click", event => {
      const action = event.target.dataset.action;
      if (!action) return;

      if (action === "clear-log") {
        log.textContent = "Waiting for command...";
        setState("Ready");
        return;
      }

      if (action === "ask-browser-camera") {
        askBrowserCamera();
        return;
      }

      if (action === "browser-camera-check") {
        browserCameraCheck();
        return;
      }

      if (action === "upma-mode") {
        runUpmaMode();
        return;
      }

      if (action === "voice-control") {
        startVoiceControl();
        return;
      }

      if (action === "upma-next") {
        nextUpmaStep();
        return;
      }

      if (action === "upma-analyze") {
        analyzeUpmaStep(true);
        return;
      }

      if (action === "upma-stop") {
        stopUpmaLive(true);
        return;
      }

      const cameraIndex = Number(document.getElementById("cameraIndex").value);
      const seconds = Number(document.getElementById("seconds").value);
      const profile = document.getElementById("profile").value;
      const delay = document.getElementById("delay").value;

      const payload = { camera_index: cameraIndex, seconds, profile, delay };
      callApi(`/api/${action}`, payload);
    });
  </script>
</body>
</html>
"""


def run_gui(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), KitchenRobotRequestHandler)
    print(f"Kitchen Robot GUI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Kitchen Robot GUI")
    finally:
        server.server_close()


class KitchenRobotRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(INDEX_HTML)
            return
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "output": "ready"})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)
            return

        routes = {
            "/api/mock-run": self._mock_run,
            "/api/v1-wired-run": self._v1_wired_run,
            "/api/upma-mode": self._v1_wired_run,
            "/api/camera-check": self._camera_check,
            "/api/browser-camera-check": self._browser_camera_check,
            "/api/browser-vision-check": self._browser_vision_check,
            "/api/api-check": self._api_check,
            "/api/ble-scan": self._ble_scan,
            "/api/serial-scan": self._serial_scan,
            "/api/stir-status": lambda data: self._stirrer(data, "status"),
            "/api/stir-stop": lambda data: self._stirrer(data, "stop"),
            "/api/stir-emergency": lambda data: self._stirrer(data, "emergency_stop"),
            "/api/stir-reverse": lambda data: self._stirrer(data, "reverse"),
            "/api/stir-start-profile": self._stirrer_profile,
            "/api/stir-start-delay": self._stirrer_delay,
            "/api/wired-status": lambda data: self._wired_stirrer(data, "status"),
            "/api/wired-stop": lambda data: self._wired_stirrer(data, "stop"),
            "/api/wired-emergency": lambda data: self._wired_stirrer(data, "emergency_stop"),
            "/api/wired-reverse": lambda data: self._wired_stirrer(data, "reverse"),
            "/api/wired-start-profile": self._wired_stirrer_profile,
            "/api/wired-start-delay": self._wired_stirrer_delay,
        }

        handler = routes.get(parsed.path)
        if handler is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        result = handler(payload)
        self._send_json(result)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _mock_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        async def run() -> int:
            from kitchen_robot.orchestrator import Orchestrator

            settings = Settings.from_env(mock=True)
            orchestrator = Orchestrator(settings=settings, recipe_id="upma")
            await orchestrator.run()
            return 0

        return _capture_async(run())

    def _v1_wired_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        browser_frame = str(payload.get("browser_frame_jpeg") or "")
        if browser_frame:
            try:
                frame = _decode_browser_frame(browser_frame)
            except ValueError as exc:
                return {
                    "ok": False,
                    "output": f"Upma mode did not start, so the motor was not started.\n\n{exc}",
                    "code": 1,
                }
            camera_preflight_output = (
                "Chrome camera preflight passed.\n"
                f"Browser JPEG size: {len(frame)} bytes."
            )
            return {
                "ok": True,
                "output": (
                    f"{camera_preflight_output}\n\n"
                    "Upma Mode is ready using Chrome camera.\n"
                    "For this Testing 1 build, use Start Profile and Stop for stirring while Chrome camera stays live.\n"
                    "Next software step is connecting the live Chrome frames into the vision agent loop."
                ),
                "code": 0,
            }
        else:
            camera_index = str(int(payload.get("camera_index", 0)))
            seconds = str(min(float(payload.get("seconds", 2)), 2.0))
            camera_result = _run_cli(
                ["camera-check", "--camera-index", camera_index, "--seconds", seconds],
                timeout=max(8, float(seconds) + 6),
                timeout_message=(
                    "Upma mode did not start because camera preflight timed out.\n"
                    "Most likely reason: macOS camera permission, wrong camera index, or another app is using the camera."
                ),
            )
            if not camera_result["ok"]:
                return {
                    "ok": False,
                    "output": (
                        "Upma mode did not start, so the motor was not started.\n\n"
                        f"{camera_result['output']}"
                    ),
                    "code": camera_result.get("code", 1),
                }
            camera_preflight_output = camera_result["output"]

        result = _run_cli(
            ["run", "--recipe", "upma"],
            timeout=22,
            timeout_message=(
                "Upma mode took too long and was stopped.\n"
                "Chrome camera preflight passed, but the current recipe runner still needs browser-frame vision integration.\n"
                "I sent emergency stop to the stirrer before returning this message."
            ),
            emergency_stop_on_timeout=True,
        )
        if result.get("output"):
            result["output"] = f"{camera_preflight_output}\n\n{result['output']}"
        return result

    def _camera_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        camera_index = str(int(payload.get("camera_index", 0)))
        seconds = str(float(payload.get("seconds", 2)))
        return _run_cli(
            ["camera-check", "--camera-index", camera_index, "--seconds", seconds],
            timeout=max(8, float(seconds) + 6),
            timeout_message=(
                "Camera check took too long and was stopped.\n"
                "Most likely reason: macOS camera permission, wrong camera index, or another app is using the camera."
            ),
        )

    def _browser_camera_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            frame = _decode_browser_frame(str(payload.get("frame_jpeg") or ""))
        except ValueError as exc:
            return {"ok": False, "output": str(exc), "code": 1}

        return {
            "ok": True,
            "output": (
                "browser camera ok: Chrome captured 1 frame.\n"
                f"JPEG size: {len(frame)} bytes.\n"
                "This fixes the camera permission path for Testing 1."
            ),
            "code": 0,
        }

    def _browser_vision_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            frame = _decode_browser_frame(str(payload.get("frame_jpeg") or ""))
        except ValueError as exc:
            return {"ok": False, "output": str(exc), "code": 1}

        step = payload.get("step")
        if not isinstance(step, dict):
            return {"ok": False, "output": "Vision step payload is missing.", "code": 1}

        settings = Settings.from_env(mock=False)
        if not settings.openai_api_key:
            return {"ok": False, "output": "OPENAI_API_KEY is missing from .env", "code": 1}

        result = _run_browser_vision_worker(
            settings=settings,
            step=step,
            frame=frame,
            timeout=16.0,
        )
        if not result["ok"]:
            return {
                "ok": False,
                "output": result.get("error") or "Vision Agent timed out.",
                "code": 124,
            }
        observation = result["observation"]

        goal_met = bool(observation.get("goal_met", False))
        confidence = float(observation.get("confidence", 0.0))
        summary = str(observation.get("summary", ""))
        safety_notes = str(observation.get("safety_notes", ""))
        safety_stop = bool(observation.get("safety_stop", False))
        normalized = {
            "goal_met": goal_met,
            "confidence": confidence,
            "summary": summary,
            "safety_notes": safety_notes,
            "safety_stop": safety_stop,
        }
        return {
            "ok": True,
            "output": (
                "Vision Agent checked one Chrome camera frame.\n"
                f"Goal met: {goal_met}\n"
                f"Confidence: {confidence:.2f}\n"
                f"Summary: {summary}\n"
                f"Safety: {safety_notes or 'none'}"
            ),
            "observation": normalized,
            "code": 0,
        }

    def _api_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = Settings.from_env(mock=False)
        key = settings.openai_api_key or ""
        if not key:
            return {"ok": False, "output": "OPENAI_API_KEY is missing from .env"}
        if not key.startswith("sk-"):
            return {"ok": False, "output": "OPENAI_API_KEY is present but does not look valid"}
        return {
            "ok": True,
            "output": (
                "OPENAI_API_KEY is configured.\n"
                f"Reasoning model: {settings.reasoning_model}\n"
                f"Vision model: {settings.vision_model}\n"
                f"STT model: {settings.stt_model}\n"
                f"TTS model: {settings.tts_model}"
            ),
        }

    def _ble_scan(self, payload: dict[str, Any]) -> dict[str, Any]:
        async def run() -> int:
            settings = Settings.from_env(mock=False)
            return await ble_scan(settings, timeout=5)

        return _capture_async(run())

    def _serial_scan(self, payload: dict[str, Any]) -> dict[str, Any]:
        async def run() -> int:
            return await serial_scan()

        return _capture_async(run())

    def _stirrer_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = str(payload.get("profile") or "slow")
        return self._stirrer(payload, "start_profile", profile)

    def _stirrer_delay(self, payload: dict[str, Any]) -> dict[str, Any]:
        delay = str(payload.get("delay") or "2500")
        return self._stirrer(payload, "start_delay", delay)

    def _wired_stirrer_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = str(payload.get("profile") or "slow")
        return self._wired_stirrer(payload, "start_profile", profile)

    def _wired_stirrer_delay(self, payload: dict[str, Any]) -> dict[str, Any]:
        delay = str(payload.get("delay") or "2500")
        return self._wired_stirrer(payload, "start_delay", delay)

    def _stirrer(
        self,
        payload: dict[str, Any],
        command: str,
        value: str | None = None,
    ) -> dict[str, Any]:
        async def run() -> int:
            settings = Settings.from_env(mock=False)
            return await stirrer_command(settings, command, value)

        return _capture_async(run())

    def _wired_stirrer(
        self,
        payload: dict[str, Any],
        command: str,
        value: str | None = None,
    ) -> dict[str, Any]:
        async def run() -> int:
            return await wired_stirrer_command(command, value)

        return _capture_async(run())

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, body: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _capture_async(coro: Any) -> dict[str, Any]:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            code = asyncio.run(coro)
    except Exception as exc:
        output = buffer.getvalue()
        if output:
            output = f"{output}\n{exc}"
        else:
            output = str(exc)
        return {"ok": False, "output": output}

    return {"ok": code == 0, "output": buffer.getvalue(), "code": code}


def _run_browser_vision_worker(
    settings: Settings,
    step: dict[str, Any],
    frame: bytes,
    timeout: float,
) -> dict[str, Any]:
    context = get_context("spawn")
    queue: Queue = context.Queue()
    process = context.Process(
        target=_browser_vision_worker,
        args=(settings, step, frame, queue),
    )
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join(0.5)
        return {"ok": False, "error": f"Vision worker timed out after {timeout:.1f}s"}

    try:
        return queue.get_nowait()
    except Empty:
        return {"ok": False, "error": "Vision worker exited without a result"}


def _browser_vision_worker(
    settings: Settings,
    step: dict[str, Any],
    frame: bytes,
    queue: Queue,
) -> None:
    async def run() -> dict[str, Any]:
        from kitchen_robot.services.openai_gateway import OpenAiGateway

        gateway = OpenAiGateway(settings)
        return await gateway.inspect_video_window(
            recipe_step=step,
            jpeg_frames=[frame],
        )

    try:
        queue.put({"ok": True, "observation": asyncio.run(run())})
    except Exception as exc:
        queue.put({"ok": False, "error": str(exc)})


def _decode_browser_frame(data_url: str) -> bytes:
    prefix = "data:image/jpeg;base64,"
    if not data_url.startswith(prefix):
        raise ValueError("Browser camera frame is missing. Click Ask Chrome Camera Permission first.")

    try:
        frame = base64.b64decode(data_url[len(prefix) :], validate=True)
    except ValueError as exc:
        raise ValueError("Browser camera frame could not be decoded.") from exc

    if len(frame) < 1000:
        raise ValueError("Browser camera frame is too small. Try camera permission again.")
    return frame


def _run_cli(
    args: list[str],
    timeout: float,
    timeout_message: str,
    emergency_stop_on_timeout: bool = False,
) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    src_path = str(project_root / "src")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_path

    try:
        result = subprocess.run(
            [sys.executable, "-m", "kitchen_robot", *args],
            cwd=project_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output_parts = [timeout_message]
        if emergency_stop_on_timeout:
            output_parts.append(_emergency_stop_after_timeout())
        if exc.stdout:
            output_parts.append(str(exc.stdout))
        if exc.stderr:
            output_parts.append(str(exc.stderr))
        return {"ok": False, "output": "\n".join(output_parts), "code": 124}

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return {"ok": result.returncode == 0, "output": output, "code": result.returncode}


def _emergency_stop_after_timeout() -> str:
    result = _run_cli(
        ["wired-command", "emergency_stop"],
        timeout=12,
        timeout_message="Emergency stop timed out after the Upma session timeout.",
    )
    return (
        "Emergency stop after timeout:\n"
        f"{result.get('output') or 'No emergency stop output'}"
    )


def add_gui_parser(subparsers: argparse._SubParsersAction) -> None:
    gui_parser = subparsers.add_parser("gui", help="Run the local browser GUI")
    gui_parser.add_argument("--host", default="127.0.0.1")
    gui_parser.add_argument("--port", type=int, default=8787)
