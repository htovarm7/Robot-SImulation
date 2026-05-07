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

    plugin_block = (PKG_URDF_DIR / "fetch_gazebo.xml").read_text()
    raw = re.sub(r"</robot>\s*$", plugin_block + "\n</robot>\n", raw)
    return raw


def prepare_scene_urdf(rel_path: str) -> str:
    """Read a scenario URDF and rewrite its mesh paths to absolute file URIs."""
    src = URDFS_DIR / "assets" / rel_path
    text = src.read_text()
    living_room_uri = _abs_file_uri(URDFS_DIR / "assets" / "living_room") + "/"
    text = text.replace("package://models_pkg/models/living_room/", living_room_uri)
    # Kitchen textures are referenced relative to the URDF; rewrite to absolute too.
    if rel_path.endswith("kitchen.urdf"):
        kitchen_dir = (URDFS_DIR / "assets" / "kitchen").resolve()
        text = text.replace('filename="textures/', f'filename="file://{kitchen_dir}/textures/')
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
