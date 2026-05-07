"""Always-on microphone → Whisper STT → /spoken_command (std_msgs/String).

Records short utterances using a simple energy gate (no wake-word required)
and publishes the transcribed text. The command_dispatcher consumes that
topic and turns intents into Nav2 goals + arm motions.

Heavy deps (sounddevice, numpy, whisper) are imported lazily so the rest of
the package still works on a machine without an audio stack.
"""
from __future__ import annotations

import collections
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class VoiceListener(Node):
    def __init__(self) -> None:
        super().__init__("voice_listener")
        self.declare_parameter("model", "base.en")
        self.declare_parameter("sample_rate", 16000)
        self.declare_parameter("frame_ms", 30)
        self.declare_parameter("silence_ms", 700)
        self.declare_parameter("speech_rms", 0.012)
        self.declare_parameter("min_speech_ms", 300)
        self.declare_parameter("max_utterance_ms", 8000)
        self.declare_parameter("device", -1)  # -1 = system default

        self.pub = self.create_publisher(String, "/spoken_command", 10)
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd
            import whisper
        except ImportError as exc:
            self.get_logger().error(
                f"voice_listener missing deps ({exc}). "
                "pip install sounddevice numpy openai-whisper"
            )
            return

        model_name = self.get_parameter("model").value
        sr = int(self.get_parameter("sample_rate").value)
        frame_ms = int(self.get_parameter("frame_ms").value)
        silence_ms = int(self.get_parameter("silence_ms").value)
        threshold = float(self.get_parameter("speech_rms").value)
        min_speech_ms = int(self.get_parameter("min_speech_ms").value)
        max_utter_ms = int(self.get_parameter("max_utterance_ms").value)
        device = int(self.get_parameter("device").value)
        device = None if device < 0 else device

        self.get_logger().info(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)
        self.get_logger().info("Whisper ready. Listening on default mic.")

        frame_len = int(sr * frame_ms / 1000)
        silence_frames = silence_ms // frame_ms
        min_speech_frames = min_speech_ms // frame_ms
        max_utter_frames = max_utter_ms // frame_ms

        def transcribe(samples) -> None:
            audio = np.concatenate(samples).astype(np.float32).flatten()
            if audio.size < min_speech_frames * frame_len:
                return
            try:
                result = model.transcribe(audio, language="en", fp16=False)
            except Exception as exc:  # noqa: BLE001
                self.get_logger().warn(f"whisper failed: {exc}")
                return
            text = (result.get("text") or "").strip()
            if not text:
                return
            self.get_logger().info(f"heard: {text}")
            msg = String()
            msg.data = text
            self.pub.publish(msg)

        buffer: list = []
        silence_count = 0
        speech_count = 0
        in_speech = False
        recent = collections.deque(maxlen=5)  # pre-roll

        with sd.InputStream(samplerate=sr, channels=1, blocksize=frame_len, device=device) as stream:
            while rclpy.ok():
                block, _ = stream.read(frame_len)
                rms = float(np.sqrt(np.mean(block ** 2)))
                recent.append(block.copy())
                if rms > threshold:
                    if not in_speech:
                        in_speech = True
                        buffer = list(recent)
                        speech_count = 0
                    buffer.append(block.copy())
                    speech_count += 1
                    silence_count = 0
                    if speech_count >= max_utter_frames:
                        transcribe(buffer)
                        buffer, in_speech, speech_count, silence_count = [], False, 0, 0
                elif in_speech:
                    buffer.append(block.copy())
                    silence_count += 1
                    if silence_count >= silence_frames:
                        transcribe(buffer)
                        buffer, in_speech, speech_count, silence_count = [], False, 0, 0


def main() -> None:
    rclpy.init()
    node = VoiceListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
