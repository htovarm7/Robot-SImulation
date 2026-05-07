"""Convenience launcher: simulation + navigation (SLAM) + voice stack.

For first-time runs prefer launching the three files separately so logs are
easier to read; this combo file is for once everything works.
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    pkg = get_package_share_directory("fetch_home_sim")

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, "launch", "simulation.launch.py")),
    )
    nav = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, "launch", "navigation.launch.py")),
        launch_arguments={"mode": LaunchConfiguration("mode")}.items(),
    )
    voice = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, "launch", "voice.launch.py")),
        launch_arguments={
            "whisper_model": LaunchConfiguration("whisper_model"),
            "mic_device": LaunchConfiguration("mic_device"),
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument("mode", default_value="slam"),
        DeclareLaunchArgument("whisper_model", default_value="base.en"),
        DeclareLaunchArgument("mic_device", default_value="-1"),
        sim,
        # Give Gazebo a head start before nav/voice come up.
        TimerAction(period=8.0, actions=[nav]),
        TimerAction(period=12.0, actions=[voice]),
    ])
