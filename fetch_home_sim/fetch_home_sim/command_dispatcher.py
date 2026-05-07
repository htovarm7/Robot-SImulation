"""Parse free-form speech → Nav2 goal + optional arm reach.

Subscribes:
  /spoken_command (std_msgs/String)

Sends:
  Nav2 NavigateToPose action  (action server: /navigate_to_pose)
  /reach_target (std_msgs/String)  — consumed by arm_reach to do the
  pre-grasp motion when the intent is "pick up <object>".

Intent grammar is intentionally tiny — no LLM needed:

  pick up | grab | bring | get | fetch  <object>  [from <place>]
  go to | move to | head to            <place>
  stop | cancel | halt                  → cancel current goal

If a sentence contains a known object word we look up the mapped place in
``waypoints.yaml::objects``; if it contains a known place word we use that
directly. Multiple matches: place wins over object-implied place.
"""
from __future__ import annotations

import math
import os
import re

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, Quaternion
from rclpy.action import ActionClient
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String

PICKUP_VERBS = ("pick up", "pick-up", "pickup", "grab", "fetch", "bring", "get me", "get the")
GO_VERBS = ("go to", "move to", "head to", "drive to", "navigate to", "go")
STOP_WORDS = ("stop", "halt", "cancel", "abort")


def yaw_to_quat(yaw: float) -> Quaternion:
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class CommandDispatcher(Node):
    def __init__(self) -> None:
        super().__init__("command_dispatcher")
        self.declare_parameter("waypoints_file", "")
        wp_file = self.get_parameter("waypoints_file").value
        if not wp_file or not os.path.isfile(wp_file):
            raise RuntimeError(f"waypoints_file not found: {wp_file!r}")
        with open(wp_file) as f:
            cfg = yaml.safe_load(f)
        self.waypoints: dict = cfg.get("waypoints", {})
        self.objects: dict = cfg.get("objects", {})

        self.sub_text = self.create_subscription(String, "/spoken_command", self.on_command, 10)
        self.pub_reach = self.create_publisher(String, "/reach_target", 10)
        self.pub_status = self.create_publisher(String, "/dispatcher_status", 10)
        self.nav_client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self._goal_handle = None
        self._pending_reach: str | None = None

        self.get_logger().info(
            f"Loaded {len(self.waypoints)} waypoints, "
            f"{len(self.objects)} objects. Ready on /spoken_command."
        )

    # ------------------------------------------------------------------
    # Intent parsing
    # ------------------------------------------------------------------
    def parse(self, text: str) -> dict | None:
        t = text.lower().strip().rstrip(".!?")
        t = re.sub(r"\s+", " ", t)

        if any(w in t for w in STOP_WORDS):
            return {"action": "stop"}

        explicit_place = self._find_place(t)
        obj = self._find_object(t)

        if any(v in t for v in PICKUP_VERBS) or obj:
            place = explicit_place or (self.objects.get(obj) if obj else None)
            if not place:
                return None
            return {"action": "pick", "object": obj or "object", "place": place}

        if any(v in t for v in GO_VERBS) and explicit_place:
            return {"action": "goto", "place": explicit_place}

        if explicit_place:
            return {"action": "goto", "place": explicit_place}

        return None

    def _find_place(self, t: str) -> str | None:
        # Try multi-word names first (e.g. "living room").
        candidates = sorted(self.waypoints.keys(), key=len, reverse=True)
        for name in candidates:
            spoken = name.replace("_", " ")
            if re.search(rf"\b{re.escape(spoken)}\b", t):
                return name
        return None

    def _find_object(self, t: str) -> str | None:
        for obj in sorted(self.objects.keys(), key=len, reverse=True):
            if re.search(rf"\b{re.escape(obj)}\b", t):
                return obj
        return None

    # ------------------------------------------------------------------
    # ROS callbacks
    # ------------------------------------------------------------------
    def on_command(self, msg: String) -> None:
        # Loud, unambiguous ack so you can confirm the message reached us.
        self.get_logger().info("=" * 60)
        self.get_logger().info(f"COMMAND RECEIVED: {msg.data!r}")
        self.get_logger().info("=" * 60)

        intent = self.parse(msg.data)
        if intent is None:
            self._say(f"could not parse intent from: {msg.data!r}")
            return

        self.get_logger().info(f"parsed intent: {intent}")

        if intent["action"] == "stop":
            self._cancel_goal()
            self._say("stopping")
            return

        place = intent["place"]
        wp = self.waypoints.get(place)
        if wp is None:
            self._say(f"unknown place: {place}")
            return

        if intent["action"] == "pick":
            self._pending_reach = intent["object"]
            self._say(f"going to {place} to pick up the {intent['object']}")
        else:
            self._pending_reach = None
            self._say(f"going to {place}")

        self._send_goal(wp["x"], wp["y"], wp.get("yaw", 0.0))

    # ------------------------------------------------------------------
    # Nav2 plumbing
    # ------------------------------------------------------------------
    def _send_goal(self, x: float, y: float, yaw: float) -> None:
        self.get_logger().info(f"waiting for /navigate_to_pose action server...")
        if not self.nav_client.wait_for_server(timeout_sec=10.0):
            self._say(
                "Nav2 action server NOT AVAILABLE. Is navigation.launch.py "
                "running, and has it finished activating? (Watch its log for "
                "'Creating bond timer...')."
            )
            return
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.orientation = yaw_to_quat(float(yaw))
        self.get_logger().info(f"sending Nav2 goal: x={x:.2f} y={y:.2f} yaw={yaw:.2f}")
        future = self.nav_client.send_goal_async(goal)
        future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future) -> None:
        gh = future.result()
        if not gh.accepted:
            self._say("nav2 REJECTED the goal")
            return
        self.get_logger().info("nav2 ACCEPTED the goal — driving...")
        self._goal_handle = gh
        gh.get_result_async().add_done_callback(self._on_result)

    def _on_result(self, future) -> None:
        result = future.result()
        status = result.status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self._say("arrived")
            if self._pending_reach is not None:
                m = String()
                m.data = self._pending_reach
                self.pub_reach.publish(m)
                self.get_logger().info(f"requesting arm reach for: {self._pending_reach}")
                self._pending_reach = None
        else:
            self._say(f"navigation ended with status {status}")
        self._goal_handle = None

    def _cancel_goal(self) -> None:
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
            self._goal_handle = None

    def _say(self, text: str) -> None:
        self.get_logger().info(text)
        msg = String()
        msg.data = text
        self.pub_status.publish(msg)


def main() -> None:
    rclpy.init()
    node = CommandDispatcher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
