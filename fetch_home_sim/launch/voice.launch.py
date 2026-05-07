"""Command pipeline: optional voice node + dispatcher + arm_reach.

Args:
  mode:=voice         Live mic + Whisper STT (default).
  mode:=none          No input node — publish to /spoken_command yourself.

For text input, run the standalone node in its OWN terminal:

    ros2 run fetch_home_sim text_input

stdin is not piped through ros2 launch reliably, so the text node only works
when launched directly.
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg = get_package_share_directory("fetch_home_sim")
    waypoints = os.path.join(pkg, "config", "waypoints.yaml")

    mode = LaunchConfiguration("mode")
    is_voice = PythonExpression(["'", mode, "' == 'voice'"])

    voice_node = Node(
        package="fetch_home_sim",
        executable="voice_listener",
        name="voice_listener",
        output="screen",
        parameters=[{
            "model": LaunchConfiguration("whisper_model"),
            "device": LaunchConfiguration("mic_device"),
        }],
        condition=IfCondition(is_voice),
    )

    dispatcher = Node(
        package="fetch_home_sim",
        executable="command_dispatcher",
        name="command_dispatcher",
        output="screen",
        parameters=[{
            "use_sim_time": True,
            "waypoints_file": LaunchConfiguration("waypoints_file"),
        }],
    )

    arm = Node(
        package="fetch_home_sim",
        executable="arm_reach",
        name="arm_reach",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    return LaunchDescription([
        DeclareLaunchArgument("mode", default_value="voice",
                              description="voice | none. For text mode, run "
                              "'ros2 run fetch_home_sim text_input' separately."),
        DeclareLaunchArgument("whisper_model", default_value="base.en",
                              description="Whisper model: tiny.en | base.en | small.en | medium.en"),
        DeclareLaunchArgument("mic_device", default_value="-1",
                              description="sounddevice index, -1 = system default"),
        DeclareLaunchArgument("waypoints_file", default_value=waypoints),
        voice_node,
        dispatcher,
        arm,
    ])
