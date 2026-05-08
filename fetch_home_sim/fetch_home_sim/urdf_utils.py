"""Prepare Fetch and scenario URDFs at launch time.

Rewrites package:// mesh paths to absolute file:// URIs, applies Gazebo
plugin block, and patches the Fetch URDF for stable simulation.
"""
from __future__ import annotations

import os
import re
from pathlib import Path


def _find_repo_root() -> Path:
    env = os.environ.get("FETCH_HOME_SIM_REPO")
    if env and (Path(env) / "urdfs" / "fetch" / "robots" / "fetch.urdf").exists():
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "urdfs" / "fetch" / "robots" / "fetch.urdf").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root. Set FETCH_HOME_SIM_REPO=/path/to/Robot-SImulation."
    )


def _find_pkg_urdf_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "urdf" / "fetch_gazebo.xml"
        if cand.exists():
            return parent / "urdf"
        cand = parent / "share" / "fetch_home_sim" / "urdf" / "fetch_gazebo.xml"
        if cand.exists():
            return parent / "share" / "fetch_home_sim" / "urdf"
    raise RuntimeError("Could not locate fetch_home_sim/urdf/")


def _abs_file_uri(path: Path) -> str:
    return "file://" + str(path.resolve())


REPO_ROOT = _find_repo_root()
URDFS_DIR = REPO_ROOT / "urdfs"
PKG_URDF_DIR = _find_pkg_urdf_dir()


def prepare_fetch_urdf() -> str:
    raw = (URDFS_DIR / "fetch" / "robots" / "fetch.urdf").read_text()

    # Rewrite mesh paths
    meshes_uri = _abs_file_uri(URDFS_DIR / "fetch" / "meshes") + "/"
    raw = raw.replace("package://fetch_description/meshes/", meshes_uri)

    # Remove legacy sensor:camera block — undefined XML namespace breaks the parser
    raw = re.sub(
        r'<gazebo reference="head_camera_rgb_optical_frame">.*?</gazebo>',
        "", raw, flags=re.DOTALL,
    )

    # Restore base_link inertia zeroed in the shipped URDF (causes NaN TFs)
    raw = re.sub(
        r'<inertia\s+ixx="0"\s+ixy="0"\s+ixz="0"\s+iyy="0"\s+iyz="0"\s+izz="0\.987"\s*/>',
        '<inertia ixx="1.225" ixy="0.0099" ixz="0.0062" iyy="1.2853" iyz="-0.0034" izz="0.987" />',
        raw,
    )

    # Lower base_link cylinder to floor level — acts as a zero-friction sled
    # that prevents front/rear rocking on two sphere drive wheels
    raw = re.sub(
        r'(<origin rpy="0 0 0" xyz="0 0 )0\.20(" />\n      <geometry>\n        '
        r'<cylinder length=")0\.33(" radius=")0\.28(")',
        r'\g<1>0.03\g<2>0.06\g<3>0.27\g<4>',
        raw, count=1,
    )

    # Lock non-drive joints fixed — free joints without controllers produce
    # NaN velocities under gravity, breaking base_link physics
    JOINTS_TO_FIX = (
        "torso_lift_joint",
        "shoulder_pan_joint", "shoulder_lift_joint",
        "upperarm_roll_joint", "elbow_flex_joint",
        "forearm_roll_joint", "wrist_flex_joint", "wrist_roll_joint",
        "l_gripper_finger_joint", "r_gripper_finger_joint",
        "bellows_joint",
    )
    for jname in JOINTS_TO_FIX:
        raw = re.sub(
            rf'(<joint\s+name="{jname}"\s+type=)"(prismatic|revolute|continuous)"',
            r'\1"fixed"', raw,
        )

    # Bake tuck pose into fixed arm joints so arm doesn't stick out
    TUCK_RPY = {
        "shoulder_pan_joint":  "0 0 1.32",
        "shoulder_lift_joint": "0 1.40 0",
        "upperarm_roll_joint": "-0.20 0 0",
        "elbow_flex_joint":    "0 1.72 0",
        "forearm_roll_joint":  "0 0 0",
        "wrist_flex_joint":    "0 1.66 0",
        "wrist_roll_joint":    "0 0 0",
    }
    for jname, new_rpy in TUCK_RPY.items():
        raw = re.sub(
            rf'(<joint\s+name="{jname}"\s+type="fixed">\s*<origin\s+)rpy="[^"]*"',
            rf'\1rpy="{new_rpy}"', raw,
        )

    # Make arm/torso links massless so offset mass doesn't tip the robot
    MASSLESS_LINKS = (
        "torso_lift_link", "torso_fixed_link",
        "shoulder_pan_link", "shoulder_lift_link",
        "upperarm_roll_link", "elbow_flex_link",
        "forearm_roll_link", "wrist_flex_link", "wrist_roll_link",
        "gripper_link", "l_gripper_finger_link", "r_gripper_finger_link",
        "estop_link", "laser_link", "head_pan_link", "head_tilt_link",
        "head_camera_link", "bellows_link2",
    )
    for link in MASSLESS_LINKS:
        pattern = rf'(<link\s+name="{link}"[^>]*>)\s*<inertial>.*?</inertial>'
        replacement = (
            r'\1\n    <inertial>'
            '<mass value="0.001"/>'
            '<inertia ixx="1e-6" ixy="0" ixz="0" iyy="1e-6" iyz="0" izz="1e-6"/>'
            '</inertial>'
        )
        raw = re.sub(pattern, replacement, raw, flags=re.DOTALL)

    plugin_block = (PKG_URDF_DIR / "fetch_gazebo.xml").read_text()
    raw = re.sub(r"</robot>\s*$", plugin_block + "\n</robot>\n", raw)
    return raw


def prepare_scene_urdf(rel_path: str) -> str:
    src = URDFS_DIR / "assets" / rel_path
    text = src.read_text()
    living_room_uri = _abs_file_uri(URDFS_DIR / "assets" / "living_room") + "/"
    text = text.replace("package://models_pkg/models/living_room/", living_room_uri)

    if rel_path.endswith("kitchen.urdf"):
        kitchen_dir = (URDFS_DIR / "assets" / "kitchen").resolve()
        text = text.replace('filename="textures/', f'filename="file://{kitchen_dir}/textures/')

    # Lock movable joints (kitchen drawers, fridge door)
    text = re.sub(
        r'(<joint\s+name="[^"]+"\s+type=)"(prismatic|revolute|continuous)"',
        r'\1"fixed"', text,
    )

    if "<static>" not in text:
        text = re.sub(
            r"</robot>\s*$",
            "<gazebo><static>true</static></gazebo>\n</robot>\n", text,
        )
    return text


def write_prepared(out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "fetch":    ("fetch.urdf",    prepare_fetch_urdf()),
        "kitchen":  ("kitchen.urdf",  prepare_scene_urdf("kitchen/kitchen.urdf")),
        "couch":    ("couch.urdf",    prepare_scene_urdf("living_room/couch.urdf")),
        "armchair": ("armchair.urdf", prepare_scene_urdf("living_room/armchair.urdf")),
        "tv":       ("tv.urdf",       prepare_scene_urdf("living_room/tv.urdf")),
        "tv_table": ("tv_table.urdf", prepare_scene_urdf("living_room/tv_table.urdf")),
        "table":    ("table.urdf",    prepare_scene_urdf("living_room/table.urdf")),
    }
    out = {}
    for key, (name, body) in files.items():
        path = out_dir / name
        path.write_text(body)
        out[key] = path
    return out


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/fetch_home_sim_urdf")
    for k, v in write_prepared(target).items():
        print(f"{k}: {v}")
