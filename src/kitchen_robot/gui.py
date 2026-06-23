import argparse
import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
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
      .field-row, .grid { grid-template-columns: 1fr; }
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
        <button data-action="camera-check">Check Camera</button>
        <button data-action="serial-scan">Find Wired ESP32</button>
        <button data-action="api-check">Check API Key</button>
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
        <button data-action="upma-mode" class="primary">Upma Making Mode</button>
        <button data-action="mock-run" class="primary">Run Mock Recipe</button>
        <button data-action="clear-log">Clear Log</button>
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

    function timeoutForAction(path, payload) {
      if (path.includes("camera-check")) return Math.max(12000, (Number(payload.seconds) + 8) * 1000);
      if (path.includes("upma-mode")) return 25000;
      return 12000;
    }

    async function callApi(path, payload = {}) {
      setState("Running", "busy");
      document.querySelectorAll("button").forEach(button => button.disabled = true);
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
        appendLog(data.ok ? "OK" : "Problem", data.output || data.error || "");
        setState(data.ok ? "Ready" : "Needs Attention", data.ok ? "ok" : "error");
      } catch (error) {
        const message = error.name === "AbortError"
          ? "This step took too long and was stopped. Check camera permission/port, then try again."
          : String(error);
        appendLog("Error", message);
        setState("Error", "error");
      } finally {
        clearTimeout(timer);
        document.querySelectorAll("button").forEach(button => button.disabled = false);
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

        return _run_cli(
            ["run", "--recipe", "upma"],
            timeout=22,
            timeout_message=(
                "Upma mode took too long and was stopped.\n"
                "Most likely reason: camera capture, OpenAI vision, or ESP32 serial did not answer.\n"
                "I sent emergency stop to the stirrer before returning this message."
            ),
            emergency_stop_on_timeout=True,
        )

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
