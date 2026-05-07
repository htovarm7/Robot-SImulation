"""Read commands from stdin and publish to /spoken_command.

Useful when the mic / Whisper stack is unavailable or for scripted demos.
Type a command and press Enter; type ``quit`` to exit.
"""
from __future__ import annotations

import sys
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TextInput(Node):
    def __init__(self) -> None:
        super().__init__("text_input")
        self.pub = self.create_publisher(String, "/spoken_command", 10)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.get_logger().info(
            "text_input ready. Type a command and press Enter (e.g. "
            "'pick up the banana from the kitchen'). Ctrl-D or 'quit' to exit."
        )

    def _loop(self) -> None:
        try:
            for line in sys.stdin:
                text = line.strip()
                if not text:
                    continue
                if text.lower() in ("quit", "exit"):
                    rclpy.shutdown()
                    return
                msg = String()
                msg.data = text
                self.pub.publish(msg)
                self.get_logger().info(f"sent: {text}")
        except (EOFError, KeyboardInterrupt):
            pass


def main() -> None:
    rclpy.init()
    node = TextInput()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
