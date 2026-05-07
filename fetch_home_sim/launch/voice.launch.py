"""Command pipeline: input source + dispatcher + arm_reach.

Args:
  mode:=voice         Live mic + Whisper STT (default).
  mode:=text          stdin prompt (no audio deps required).
  mode:=none          No input node — publish to /spoken_command yourself.

Examples:
  ros2 launch fetch_home_sim voice.launch.py mode:=voice whisper_model:=base.en
  ros2 launch fetch_home_sim voice.launch.py mode:=text
  ros2 launch fetch_home_sim voice.launch.py mode:=none
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
    is_text = PythonExpression(["'", mode, "' == 'text'"])

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

    text_node = Node(
        package="fetch_home_sim",
        executable="text_input",
        name="text_input",
        output="screen",
        emulate_tty=True,
        condition=IfCondition(is_text),
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
                              description="voice | text | none"),
        DeclareLaunchArgument("whisper_model", default_value="base.en",
                              description="Whisper model: tiny.en | base.en | small.en | medium.en"),
        DeclareLaunchArgument("mic_device", default_value="-1",
                              description="sounddevice index, -1 = system default"),
        DeclareLaunchArgument("waypoints_file", default_value=waypoints),
        voice_node,
        text_node,
        dispatcher,
        arm,
    ])
