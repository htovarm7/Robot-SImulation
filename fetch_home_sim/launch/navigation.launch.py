"""Bring up Nav2 with online SLAM (default) or pre-built map localization.

Usage:
  ros2 launch fetch_home_sim navigation.launch.py mode:=slam
  ros2 launch fetch_home_sim navigation.launch.py mode:=localization map:=$PWD/home_map.yaml
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg = get_package_share_directory("fetch_home_sim")
    nav2_bringup = get_package_share_directory("nav2_bringup")

    nav2_params = os.path.join(pkg, "config", "nav2_params.yaml")
    slam_params = os.path.join(pkg, "config", "slam_toolbox_params.yaml")
    default_map = os.path.join(pkg, "maps", "home_map.yaml")

    mode = LaunchConfiguration("mode")
    map_yaml = LaunchConfiguration("map")
    use_rviz = LaunchConfiguration("rviz")

    is_slam = PythonExpression(["'", mode, "' == 'slam'"])
    is_loc = PythonExpression(["'", mode, "' == 'localization'"])

    slam_node = Node(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name="slam_toolbox",
        output="screen",
        parameters=[slam_params, {"use_sim_time": True}],
        condition=IfCondition(is_slam),
    )

    nav2_with_slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup, "launch", "navigation_launch.py")),
        launch_arguments={
            "use_sim_time": "true",
            "params_file": nav2_params,
            "autostart": "true",
        }.items(),
        condition=IfCondition(is_slam),
    )

    nav2_with_map = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup, "launch", "bringup_launch.py")),
        launch_arguments={
            "use_sim_time": "true",
            "params_file": nav2_params,
            "map": map_yaml,
            "autostart": "true",
        }.items(),
        condition=IfCondition(is_loc),
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", os.path.join(nav2_bringup, "rviz", "nav2_default_view.rviz")],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument("mode", default_value="slam",
                              description="slam | localization"),
        DeclareLaunchArgument("map", default_value=default_map),
        DeclareLaunchArgument("rviz", default_value="true"),
        slam_node,
        nav2_with_slam,
        nav2_with_map,
        rviz_node,
    ])
