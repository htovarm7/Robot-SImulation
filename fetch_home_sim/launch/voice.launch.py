"""Voice listener + command dispatcher + arm reach helper."""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg = get_package_share_directory("fetch_home_sim")
    waypoints = os.path.join(pkg, "config", "waypoints.yaml")

    return LaunchDescription([
        DeclareLaunchArgument("whisper_model", default_value="base.en"),
        DeclareLaunchArgument("mic_device", default_value="-1"),
        DeclareLaunchArgument("waypoints_file", default_value=waypoints),
        DeclareLaunchArgument("enable_voice", default_value="true"),

        Node(
            package="fetch_home_sim",
            executable="voice_listener",
            name="voice_listener",
            output="screen",
            parameters=[{
                "model": LaunchConfiguration("whisper_model"),
                "device": LaunchConfiguration("mic_device"),
            }],
            condition=None,
        ),
        Node(
            package="fetch_home_sim",
            executable="command_dispatcher",
            name="command_dispatcher",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "waypoints_file": LaunchConfiguration("waypoints_file"),
            }],
        ),
        Node(
            package="fetch_home_sim",
            executable="arm_reach",
            name="arm_reach",
            output="screen",
            parameters=[{"use_sim_time": True}],
        ),
    ])
