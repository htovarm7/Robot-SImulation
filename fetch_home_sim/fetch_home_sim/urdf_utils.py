"""Helpers that prepare URDFs at launch time.

The original Fetch URDF references ``package://fetch_description/...`` and the
living-room URDFs reference ``package://models_pkg/...``. Neither package
exists in this workspace; the meshes live directly in ``urdfs/``. We rewrite
those prefixes to absolute ``file://`` paths so Gazebo Classic and RViz can
load the meshes without needing wrapper packages.

We also splice the Gazebo plugin block (urdf/fetch_gazebo.xml) into the Fetch
URDF before ``</robot>`` so the original URDF stays untouched on disk.
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
        "Could not locate repo root containing urdfs/. "
        "Set FETCH_HOME_SIM_REPO=/path/to/Robot-SImulation."
    )


def _find_pkg_urdf_dir() -> Path:
    """Locate the package's urdf/ directory (works for both src and install)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "urdf" / "fetch_gazebo.xml"
        if cand.exists():
            return parent / "urdf"
        cand = parent / "share" / "fetch_home_sim" / "urdf" / "fetch_gazebo.xml"
        if cand.exists():
            return parent / "share" / "fetch_home_sim" / "urdf"
    raise RuntimeError("Could not locate fetch_home_sim/urdf/")


REPO_ROOT = _find_repo_root()
URDFS_DIR = REPO_ROOT / "urdfs"
PKG_URDF_DIR = _find_pkg_urdf_dir()


def _abs_file_uri(path: Path) -> str:
    return "file://" + str(path.resolve())


def prepare_fetch_urdf() -> str:
    """Return Fetch URDF as a string, with package:// rewritten and Gazebo plugins added."""
    raw = (URDFS_DIR / "fetch" / "robots" / "fetch.urdf").read_text()
    meshes_uri = _abs_file_uri(URDFS_DIR / "fetch" / "meshes") + "/"
    raw = raw.replace("package://fetch_description/meshes/", meshes_uri)

    # Strip the legacy <sensor:camera> block — uses an undefined XML namespace
    # prefix from Gazebo Classic 1.x, which the URDF parser rejects. We replace
    # it with a modern camera plugin via fetch_gazebo.xml.
    raw = re.sub(
        r'<gazebo reference="head_camera_rgb_optical_frame">.*?</gazebo>',
        "",
        raw,
        flags=re.DOTALL,
    )

    # The shipped URDF zeroed base_link's diagonal inertia (only izz is set).
    # Gazebo's physics produce NaN poses/velocities with that, which cascades
    # into TF as NaN translations on torso_lift_link and the gripper fingers,
    # which then breaks Nav2. Restore the original positive Fetch values.
    raw = re.sub(
        r'<inertia\s+ixx="0"\s+ixy="0"\s+ixz="0"\s+iyy="0"\s+iyz="0"\s+izz="0\.987"\s*/>',
        '<inertia ixx="1.225" ixy="0.0099" ixz="0.0062" iyy="1.2853" iyz="-0.0034" izz="0.987" />',
        raw,
    )

    # Lock every non-driving joint as fixed. Without controllers, free
    # revolute/prismatic joints (arm, torso, grippers) flop under gravity
    # and the solver produces NaN velocities — which cascades into
    # base_link physics and the diff drive can't move. Wheels stay
    # continuous so they roll; head joints stay revolute so the head can
    # be commanded later. Everything else: fixed.
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
            r'\1"fixed"',
            raw,
        )

    # Bake the Fetch "tuck" pose into the now-fixed arm joint origins so
    # the arm folds against the body instead of sticking out forward.
    # Each joint's origin had rpy="0 0 0" and a clean axis (z/y/x), so we
    # can write the tuck angle directly into the matching rpy component.
    TUCK_RPY = {
        "shoulder_pan_joint":  "0 0 1.32",      # axis z, swing arm to the side
        "shoulder_lift_joint": "0 1.40 0",      # axis y, lift up
        "upperarm_roll_joint": "-0.20 0 0",     # axis x, slight roll
        "elbow_flex_joint":    "0 1.72 0",      # axis y, bend elbow back
        "forearm_roll_joint":  "0 0 0",         # neutral
        "wrist_flex_joint":    "0 1.66 0",      # axis y, curl wrist
        "wrist_roll_joint":    "0 0 0",         # neutral
    }
    for jname, new_rpy in TUCK_RPY.items():
        raw = re.sub(
            rf'(<joint\s+name="{jname}"\s+type="fixed">\s*<origin\s+)rpy="[^"]*"',
            rf'\1rpy="{new_rpy}"',
            raw,
        )

    # Make every fixed manipulator link massless. Their default URDF masses
    # are offset from base_link's center, which torques the robot under
    # gravity (arm pulls it onto its side, costmap then says "out of
    # bounds"). With mass≈0 the visual model is unchanged but the rigid
    # body's inertia is dominated by base_link, keeping the robot level.
    MASSLESS_LINKS = (
        "torso_lift_link", "torso_fixed_link",
        "shoulder_pan_link", "shoulder_lift_link",
        "upperarm_roll_link", "elbow_flex_link",
        "forearm_roll_link", "wrist_flex_link", "wrist_roll_link",
        "gripper_link", "l_gripper_finger_link", "r_gripper_finger_link",
        "estop_link", "laser_link",
        "head_pan_link", "head_tilt_link",
        "head_camera_link", "bellows_link2",
    )
    for link in MASSLESS_LINKS:
        # Replace the <inertial>...</inertial> block of each named link with
        # a tiny but well-conditioned inertial so Gazebo doesn't divide by 0.
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
    """Read a scenario URDF and rewrite its mesh paths to absolute file URIs.

    Also:
      * locks every prismatic/revolute joint (kitchen drawers, fridge door)
        into a fixed joint so they don't dangle or self-actuate;
      * marks the model static via a <gazebo> block so the robot can't
        push furniture around.
    """
    src = URDFS_DIR / "assets" / rel_path
    text = src.read_text()
    living_room_uri = _abs_file_uri(URDFS_DIR / "assets" / "living_room") + "/"
    text = text.replace("package://models_pkg/models/living_room/", living_room_uri)

    if rel_path.endswith("kitchen.urdf"):
        kitchen_dir = (URDFS_DIR / "assets" / "kitchen").resolve()
        text = text.replace('filename="textures/', f'filename="file://{kitchen_dir}/textures/')

    # Convert non-fixed joints to fixed (drawer prismatic, fridge revolute, etc.)
    text = re.sub(
        r'(<joint\s+name="[^"]+"\s+type=)"(prismatic|revolute|continuous)"',
        r'\1"fixed"',
        text,
    )

    # Add <gazebo><static>true</static></gazebo> if not already present.
    if "<static>" not in text:
        text = re.sub(
            r"</robot>\s*$",
            "<gazebo><static>true</static></gazebo>\n</robot>\n",
            text,
        )
    return text


def write_prepared(out_dir: Path) -> dict[str, Path]:
    """Materialize all prepared URDFs into out_dir; return name -> path map."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "fetch": ("fetch.urdf", prepare_fetch_urdf()),
        "kitchen": ("kitchen.urdf", prepare_scene_urdf("kitchen/kitchen.urdf")),
        "couch": ("couch.urdf", prepare_scene_urdf("living_room/couch.urdf")),
        "armchair": ("armchair.urdf", prepare_scene_urdf("living_room/armchair.urdf")),
        "tv": ("tv.urdf", prepare_scene_urdf("living_room/tv.urdf")),
        "tv_table": ("tv_table.urdf", prepare_scene_urdf("living_room/tv_table.urdf")),
        "table": ("table.urdf", prepare_scene_urdf("living_room/table.urdf")),
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
    out = write_prepared(target)
    for k, v in out.items():
        print(f"{k}: {v}")
