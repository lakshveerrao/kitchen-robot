import time

from kitchen_robot.config import Settings


class LiveVideoWindow:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def capture_jpeg_window(self) -> list[bytes]:
        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install 'opencv-python' to use live video capture.") from exc

        capture = cv2.VideoCapture(self.settings.camera_index)
        if not capture.isOpened():
            raise RuntimeError(f"Could not open camera index {self.settings.camera_index}.")

        frames: list[bytes] = []
        start = time.monotonic()
        frame_index = 0
        try:
            while time.monotonic() - start < self.settings.video_window_seconds:
                ok, frame = capture.read()
                if not ok:
                    continue

                if frame_index % self.settings.video_sample_every_n_frames == 0:
                    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    if ok:
                        frames.append(buffer.tobytes())
                frame_index += 1
        finally:
            capture.release()

        if not frames:
            raise RuntimeError("No frames captured from live video window.")
        return frames

