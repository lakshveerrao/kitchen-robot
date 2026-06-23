from dataclasses import dataclass
import glob
import os
import select
import termios
import time
import tty


@dataclass(frozen=True)
class SerialDeviceInfo:
    port: str
    description: str
    hwid: str


@dataclass(frozen=True)
class SerialCommandResult:
    ok: bool
    port: str | None
    message: str


def serialize_serial_stir_command(payload: dict) -> str:
    command_type = payload.get("type")

    if command_type == "start_profile":
        profile = str(payload.get("profile", "slow"))
        delay_by_profile = {
            "slow": 5000,
            "medium": 2500,
            "fast": 1200,
        }
        return f"start {delay_by_profile.get(profile, 5000)}"

    if command_type == "start_delay":
        return f"start {int(payload['delay_micros'])}"

    if command_type in {"status", "stop", "emergency_stop", "reverse"}:
        return str(command_type)

    if command_type == "servo":
        target = str(payload["target"])
        position = str(payload["position"])
        if target == "home":
            return "servo home"
        if target != "lift":
            raise ValueError(f"Unsupported servo target: {target}")
        return f"servo {target} {position}"

    raise ValueError(f"Unsupported wired stir command: {payload}")


def list_serial_devices() -> list[SerialDeviceInfo]:
    devices = []
    for port in sorted(set(glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*"))):
        devices.append(
            SerialDeviceInfo(
                port=port,
                description=_describe_port(port),
                hwid="",
            )
        )
    return devices


def detect_esp32_port() -> str | None:
    devices = list_serial_devices()
    preferred_terms = ("Espressif", "USB JTAG", "usbmodem", "CP210", "CH340")

    for device in devices:
        combined = f"{device.port} {device.description} {device.hwid}".lower()
        if "usbmodem603ntczr" in combined:
            continue
        if any(term.lower() in combined for term in preferred_terms):
            return device.port

    for device in devices:
        if device.port.startswith("/dev/cu.usb") or device.port.startswith("/dev/tty.usb"):
            return device.port

    return None


class Esp32SerialClient:
    def __init__(self, port: str | None = None, baudrate: int = 115200) -> None:
        self.port = port
        self.baudrate = baudrate

    def send_command(
        self,
        command: str,
        timeout: float = 3.0,
        attempts: int = 2,
    ) -> SerialCommandResult:
        last_result = SerialCommandResult(ok=False, port=None, message="Command was not sent")
        for attempt in range(max(1, attempts)):
            result = self._send_command_once(command, timeout)
            if result.ok or "No response from ESP32" not in result.message:
                return result
            last_result = result
            if attempt < attempts - 1:
                time.sleep(0.4)
        return last_result

    def _send_command_once(self, command: str, timeout: float) -> SerialCommandResult:
        port = self.port or detect_esp32_port()
        if port is None:
            return SerialCommandResult(ok=False, port=None, message="No ESP32 serial port found")

        fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            _configure_serial(fd, self.baudrate)
            time.sleep(1.5)
            _drain(fd)
            os.write(fd, (command.strip() + "\n").encode("utf-8"))

            deadline = time.monotonic() + timeout
            lines: list[str] = []
            buffer = b""
            while time.monotonic() < deadline:
                readable, _, _ = select.select([fd], [], [], 0.1)
                if not readable:
                    continue
                chunk = os.read(fd, 1024)
                if not chunk:
                    continue
                buffer += chunk
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        lines.append(line)
                        if line.startswith(("OK", "ERR", "STATUS")):
                            return SerialCommandResult(
                                ok=not line.startswith("ERR"),
                                port=port,
                                message=line,
                            )
        finally:
            os.close(fd)

        message = "\n".join(lines) if lines else "No response from ESP32"
        return SerialCommandResult(ok=False, port=port, message=message)


def _describe_port(port: str) -> str:
    lower = port.lower()
    if "usbmodem603ntczr" in lower:
        return "LG monitor controls"
    if "usbmodem" in lower:
        return "USB serial device"
    if "bluetooth" in lower:
        return "Bluetooth serial port"
    return "Serial port"


def _configure_serial(fd: int, baudrate: int) -> None:
    attrs = termios.tcgetattr(fd)
    tty.setraw(fd)
    attrs = termios.tcgetattr(fd)

    speed = _baud_constant(baudrate)
    attrs[4] = speed
    attrs[5] = speed

    attrs[2] |= termios.CLOCAL | termios.CREAD
    if hasattr(termios, "HUPCL"):
        attrs[2] &= ~termios.HUPCL
    attrs[2] &= ~termios.PARENB
    attrs[2] &= ~termios.CSTOPB
    attrs[2] &= ~termios.CSIZE
    attrs[2] |= termios.CS8

    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def _baud_constant(baudrate: int) -> int:
    mapping = {
        9600: termios.B9600,
        19200: termios.B19200,
        38400: termios.B38400,
        57600: termios.B57600,
        115200: termios.B115200,
    }
    return mapping.get(baudrate, termios.B115200)


def _drain(fd: int) -> None:
    while True:
        readable, _, _ = select.select([fd], [], [], 0)
        if not readable:
            return
        try:
            if not os.read(fd, 1024):
                return
        except BlockingIOError:
            return
