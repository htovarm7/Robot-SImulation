"""Log arm-reach intent when the robot arrives at a pick-up target.

Arm joints are locked fixed (no controllers) so no trajectory is sent.
The node exists as a placeholder for future ros2_control integration.
"""
from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ArmReach(Node):
    def __init__(self) -> None:
        super().__init__("arm_reach")
        self.sub = self.create_subscription(String, "/reach_target", self.on_target, 10)
        self.get_logger().info("arm_reach ready on /reach_target")

    def on_target(self, msg: String) -> None:
        self.get_logger().info(f"[reach] arrived at target — would grasp: {msg.data}")


def main() -> None:
    rclpy.init()
    node = ArmReach()
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
