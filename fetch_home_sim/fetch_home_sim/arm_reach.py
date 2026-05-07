"""Acknowledges /reach_target. Currently a logging stub.

Originally this drove a JointTrajectory through the gazebo_ros_joint_pose_
trajectory plugin, but free arm joints under gravity produce NaN velocities
in Gazebo (no controllers to hold them), which destabilises base_link
physics and prevents the robot from driving. Until controllers are added,
all arm/torso joints are locked fixed in the prepared URDF, and this node
just logs the reach intent so you can see in the dispatcher console that
the robot "would have" reached when it arrived at the target.
"""
from __future__ import annotations

from builtin_interfaces.msg import Duration
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

REACH_JOINTS = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "upperarm_roll_joint",
    "elbow_flex_joint",
    "forearm_roll_joint",
    "wrist_flex_joint",
    "wrist_roll_joint",
]

TUCK_POSE = [0.0, 1.32, 0.0, -2.0, 0.0, 1.5, 0.0]

# Reach sequence: ensure we start from tuck so the arm matches what RViz shows,
# extend forward, and hold. (torso_lift_joint is locked fixed; see urdf_utils.py.)
REACH_SEQUENCE = [
    (1.0, TUCK_POSE),
    (3.5, [ 0.0, -0.6, 0.0,  0.4, 0.0, 0.6, 0.0]),
    (5.5, [ 0.0, -0.4, 0.0,  0.2, 0.0, 0.4, 0.0]),
]


def _sec_to_duration(t: float) -> Duration:
    d = Duration()
    d.sec = int(t)
    d.nanosec = int((t - int(t)) * 1e9)
    return d


class ArmReach(Node):
    def __init__(self) -> None:
        super().__init__("arm_reach")
        self.sub = self.create_subscription(String, "/reach_target", self.on_target, 10)
        self.get_logger().info("arm_reach ready on /reach_target (logging stub)")

    def on_target(self, msg: String) -> None:
        self.get_logger().info(
            f"[reach gesture] would extend arm to grasp: {msg.data} "
            "(arm joints locked fixed; see arm_reach.py docstring)"
        )


def main() -> None:
    rclpy.init()
    node = ArmReach()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
