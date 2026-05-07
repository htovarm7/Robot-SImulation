"""Listens on /reach_target and drives the arm into a pre-grasp pose.

The user requested that the robot "make the movement to achieve the place"
without needing to actually grasp. We just send a smooth joint trajectory
that raises the torso, lowers the shoulder and extends the arm forward —
visually a clear reach. We use the JointTrajectory topic exposed by the
``gazebo_ros_joint_pose_trajectory`` plugin attached to the URDF.
"""
from __future__ import annotations

from builtin_interfaces.msg import Duration
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

REACH_JOINTS = [
    "torso_lift_joint",
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "upperarm_roll_joint",
    "elbow_flex_joint",
    "forearm_roll_joint",
    "wrist_flex_joint",
    "wrist_roll_joint",
]

# Sequence: tuck → reach → hold. Times are seconds from start.
REACH_SEQUENCE = [
    (1.0, [0.05, 0.0, 1.0, 0.0, -1.5, 0.0, 1.5, 0.0]),     # tuck-ish
    (3.5, [0.30, 0.0, -0.6, 0.0, 0.4, 0.0, 0.6, 0.0]),     # extend forward
    (5.5, [0.30, 0.0, -0.4, 0.0, 0.2, 0.0, 0.4, 0.0]),     # hold
]


def _sec_to_duration(t: float) -> Duration:
    d = Duration()
    d.sec = int(t)
    d.nanosec = int((t - int(t)) * 1e9)
    return d


class ArmReach(Node):
    def __init__(self) -> None:
        super().__init__("arm_reach")
        self.pub = self.create_publisher(JointTrajectory, "/set_joint_trajectory", 10)
        self.sub = self.create_subscription(String, "/reach_target", self.on_target, 10)
        self.get_logger().info("arm_reach ready on /reach_target")

    def on_target(self, msg: String) -> None:
        self.get_logger().info(f"reaching for: {msg.data}")
        traj = JointTrajectory()
        traj.header.frame_id = "base_link"
        traj.joint_names = REACH_JOINTS
        for t, positions in REACH_SEQUENCE:
            point = JointTrajectoryPoint()
            point.positions = list(positions)
            point.time_from_start = _sec_to_duration(t)
            traj.points.append(point)
        self.pub.publish(traj)


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
