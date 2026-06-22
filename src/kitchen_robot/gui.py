import argparse
import asyncio
import contextlib
import io
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from kitchen_robot.config import Settings
from kitchen_robot.operator import ble_scan, camera_check, stirrer_command
from kitchen_robot.orchestrator import Orchestrator


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
        <button data-action="ble-scan">Scan BLE</button>
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
        <button data-action="stir-status">Status</button>
        <button data-action="stir-stop" class="warn">Stop</button>
        <button data-action="stir-start-profile" class="primary">Start Profile</button>
        <button data-action="stir-reverse">Reverse</button>
        <button data-action="stir-start-delay">Start Delay</button>
        <button data-action="stir-emergency" class="danger">Emergency Stop</button>
      </div>
    </section>

    <section class="wide">
      <h2>Session</h2>
      <div class="grid">
        <button data-action="mock-run" class="primary">Run Mock Recipe</button>
        <button data-action="clear-log">Clear Log</button>
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

    async function callApi(path, payload = {}) {
      setState("Running", "busy");
      document.querySelectorAll("button").forEach(button => button.disabled = true);
      try {
        const response = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        appendLog(data.ok ? "OK" : "Problem", data.output || data.error || "");
        setState(data.ok ? "Ready" : "Needs Attention", data.ok ? "ok" : "error");
      } catch (error) {
        appendLog("Error", String(error));
        setState("Error", "error");
      } finally {
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
            "/api/camera-check": self._camera_check,
            "/api/ble-scan": self._ble_scan,
            "/api/stir-status": lambda data: self._stirrer(data, "status"),
            "/api/stir-stop": lambda data: self._stirrer(data, "stop"),
            "/api/stir-emergency": lambda data: self._stirrer(data, "emergency_stop"),
            "/api/stir-reverse": lambda data: self._stirrer(data, "reverse"),
            "/api/stir-start-profile": self._stirrer_profile,
            "/api/stir-start-delay": self._stirrer_delay,
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
            settings = Settings.from_env(mock=True)
            orchestrator = Orchestrator(settings=settings, recipe_id="upma")
            await orchestrator.run()
            return 0

        return _capture_async(run())

    def _camera_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        async def run() -> int:
            settings = Settings.from_env(mock=False).with_overrides(
                camera_index=int(payload.get("camera_index", 0)),
                video_window_seconds=float(payload.get("seconds", 2)),
            )
            return await camera_check(settings)

        return _capture_async(run())

    def _ble_scan(self, payload: dict[str, Any]) -> dict[str, Any]:
        async def run() -> int:
            settings = Settings.from_env(mock=False)
            return await ble_scan(settings, timeout=5)

        return _capture_async(run())

    def _stirrer_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = str(payload.get("profile") or "slow")
        return self._stirrer(payload, "start_profile", profile)

    def _stirrer_delay(self, payload: dict[str, Any]) -> dict[str, Any]:
        delay = str(payload.get("delay") or "2500")
        return self._stirrer(payload, "start_delay", delay)

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


def add_gui_parser(subparsers: argparse._SubParsersAction) -> None:
    gui_parser = subparsers.add_parser("gui", help="Run the local browser GUI")
    gui_parser.add_argument("--host", default="127.0.0.1")
    gui_parser.add_argument("--port", type=int, default=8787)
