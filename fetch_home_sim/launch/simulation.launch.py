"""Bring up Gazebo Classic, the Fetch robot, and the static scene URDFs.

The original Fetch URDF references ``package://fetch_description/...`` and
the living-room URDFs reference ``package://models_pkg/...`` — neither
package exists in this workspace. We rewrite those to absolute file paths
at launch time using fetch_home_sim/urdf_utils.py and write the prepared
URDFs into ``/tmp/fetch_home_sim_urdf/``.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


# Static scenario items: name → (urdf_key, x, y, z, yaw)
SCENE_LAYOUT = [
    ("kitchen_main", "kitchen", 1.6, 1.5, 0.0, 0.0),
    ("dining_table", "table", 0.5, -1.5, 0.0, 0.0),
    ("couch", "couch", -1.5, -3.2, 0.0, 0.0),
    ("armchair", "armchair", -2.8, -1.4, 0.0, 1.5708),
    ("tv_table", "tv_table", -3.5, -2.0, 0.0, 1.5708),
    ("tv", "tv", -3.6, -2.0, 0.55, 1.5708),
]


def _prepare_urdfs(context, *args, **kwargs):
    """Generate prepared URDFs and emit spawn actions referencing them."""
    # Import here so the launch system loads even if Python path setup is partial.
    import sys
    pkg_root = Path(get_package_share_directory("fetch_home_sim")).parent.parent
    src_root = pkg_root.parent  # workspace src
    # Walk back to repo root regardless of where we were installed.
    candidate = Path(__file__).resolve()
    repo_root = None
    for parent in candidate.parents:
        if (parent / "urdfs" / "fetch" / "robots" / "fetch.urdf").exists():
            repo_root = parent
            break
    if repo_root is None:
        # Fallback: env var
        env_root = os.environ.get("FETCH_HOME_SIM_REPO")
        if env_root:
            repo_root = Path(env_root)
    if repo_root is None:
        raise RuntimeError(
            "Could not locate repo root (urdfs/). Set FETCH_HOME_SIM_REPO env var."
        )

    sys.path.insert(0, str(repo_root / "fetch_home_sim"))
    from fetch_home_sim.urdf_utils import write_prepared

    out_dir = Path(tempfile.gettempdir()) / "fetch_home_sim_urdf"
    prepared = write_prepared(out_dir)

    fetch_urdf_path = prepared["fetch"]
    robot_description = fetch_urdf_path.read_text()

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{
            "use_sim_time": True,
            "robot_description": robot_description,
            "publish_frequency": 30.0,
        }],
    )

    spawn_fetch = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        output="screen",
        arguments=[
            "-entity", "fetch",
            "-topic", "robot_description",
            "-x", "0.0", "-y", "-0.5", "-z", "0.01",
            "-Y", "1.5708",
        ],
    )

    actions = [rsp, spawn_fetch]
    for name, key, x, y, z, yaw in SCENE_LAYOUT:
        urdf_path = prepared[key]
        actions.append(
            Node(
                package="gazebo_ros",
                executable="spawn_entity.py",
                name=f"spawn_{name}",
                output="screen",
                arguments=[
                    "-entity", name,
                    "-file", str(urdf_path),
                    "-x", str(x), "-y", str(y), "-z", str(z),
                    "-Y", str(yaw),
                ],
            )
        )
    return actions


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("fetch_home_sim")
    world = os.path.join(pkg_share, "worlds", "home.world")

    gazebo_ros = get_package_share_directory("gazebo_ros")
    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_ros, "launch", "gzserver.launch.py")),
        launch_arguments={"world": world, "verbose": "true"}.items(),
    )
    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_ros, "launch", "gzclient.launch.py")),
    )

    return LaunchDescription([
        DeclareLaunchArgument("headless", default_value="false"),
        gzserver,
        gzclient,
        OpaqueFunction(function=_prepare_urdfs),
    ])
