"""Drive the robot through a fixed exploration tour to seed the SLAM map.

Reads ``exploration:`` from waypoints.yaml, sends each pose in sequence to
Nav2's ``/navigate_to_pose`` action, then publishes a single status string
"READY" to ``/dispatcher_status`` and exits. After this finishes once the
SLAM map covers the whole house and the regular text/voice commands can
plan anywhere.

Run AFTER ``simulation`` and ``navigation`` launches are up:

    ros2 run fetch_home_sim auto_mapper
"""
from __future__ import annotations

import math
import os
import sys
import time

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, Quaternion
from nav_msgs.msg import OccupancyGrid
from rclpy.action import ActionClient
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String


def yaw_to_quat(yaw: float) -> Quaternion:
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class AutoMapper(Node):
    def __init__(self) -> None:
        super().__init__("auto_mapper")
        # use_sim_time MUST match Nav2 (Gazebo publishes /clock). Without it,
        # goal headers carry wall-clock stamps and Nav2 rejects them as stale.
        self.set_parameters([rclpy.parameter.Parameter(
            "use_sim_time", rclpy.Parameter.Type.BOOL, True)])
        self.declare_parameter("waypoints_file", "")
        self.declare_parameter("per_goal_timeout", 90.0)

        wp_file = self.get_parameter("waypoints_file").value
        if not wp_file:
            wp_file = os.path.join(
                get_package_share_directory("fetch_home_sim"),
                "config", "waypoints.yaml",
            )
        with open(wp_file) as f:
            cfg = yaml.safe_load(f)

        self.poses: list[dict] = cfg.get("exploration") or []
        if not self.poses:
            self.get_logger().error(
                "No 'exploration' list in waypoints.yaml — nothing to do."
            )
            sys.exit(1)

        self.timeout = float(self.get_parameter("per_goal_timeout").value)
        self.client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.status_pub = self.create_publisher(String, "/dispatcher_status", 10)

        self._map_ready = False
        self._map_sub = self.create_subscription(
            OccupancyGrid, "/map", self._on_map, 1)

        self.get_logger().info(
            f"AutoMapper loaded {len(self.poses)} exploration poses. "
            f"Per-goal timeout = {self.timeout:.0f}s."
        )

    def _on_map(self, msg: OccupancyGrid) -> None:
        free = sum(1 for c in msg.data if c == 0)
        if free > 200 and not self._map_ready:
            self._map_ready = True
            self.get_logger().info(
                f"Map ready: {msg.info.width}x{msg.info.height} cells, "
                f"{free} free. Starting tour."
            )

    # ------------------------------------------------------------------
    # Public driver
    # ------------------------------------------------------------------
    def run(self) -> bool:
        self.get_logger().info("waiting for /navigate_to_pose action server...")
        if not self.client.wait_for_server(timeout_sec=15.0):
            self.get_logger().error("Nav2 action server not available — is navigation.launch.py up?")
            return False

        self.get_logger().info("waiting for SLAM map to populate (need >200 free cells)...")
        deadline = time.time() + 30.0
        while not self._map_ready and time.time() < deadline and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.5)
        if not self._map_ready:
            self.get_logger().warn("Map did not populate in 30s — starting anyway.")
        else:
            # Give nav2 costmap a moment to receive the map from slam_toolbox
            self.get_logger().info("Map received. Waiting 3s for costmap to update...")
            deadline2 = time.time() + 3.0
            while time.time() < deadline2 and rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.1)

        for i, p in enumerate(self.poses, 1):
            self._announce(
                f"[{i}/{len(self.poses)}] going to "
                f"x={p['x']:.2f} y={p['y']:.2f} yaw={p.get('yaw', 0.0):.2f}"
            )
            ok = self._send_and_wait(p["x"], p["y"], p.get("yaw", 0.0))
            if not ok:
                self.get_logger().warn(
                    f"goal {i} failed/timed out — continuing tour anyway"
                )

        self._announce("=" * 60)
        self._announce("MAPPING TOUR COMPLETE — robot is READY for commands.")
        self._announce("=" * 60)
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _send_and_wait(self, x: float, y: float, yaw: float) -> bool:
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = "map"
        # Leaving stamp at zero is treated as "use latest" by tf2 — avoids
        # stale-stamp rejections if our clock is out of sync with Nav2's.
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.orientation = yaw_to_quat(float(yaw))

        future = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if not future.done():
            self.get_logger().warn("goal send timed out")
            return False

        gh = future.result()
        if not gh.accepted:
            self.get_logger().warn(
                "Nav2 rejected the goal. Common causes: Nav2 not fully "
                "active yet (wait ~10s after navigation.launch.py); planner "
                "failed (track_unknown_space=true with empty SLAM map); "
                "or the goal sits in a lethal cell."
            )
            return False

        result_future = gh.get_result_async()
        deadline = time.time() + self.timeout
        while time.time() < deadline and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.5)
            if result_future.done():
                break

        if not result_future.done():
            gh.cancel_goal_async()
            return False

        status = result_future.result().status
        return status == GoalStatus.STATUS_SUCCEEDED

    def _announce(self, text: str) -> None:
        self.get_logger().info(text)
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = AutoMapper()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
