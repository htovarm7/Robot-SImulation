# Fetch Home Simulation — Gazebo Classic + ROS 2 Humble

> Created by [Hector Tovar](https://github.com/htovarm7)

A Gazebo simulation of the **Fetch mobile manipulator** operating inside a furnished home. The robot listens to spoken commands like *"pick up the banana from the kitchen"*, parses the intent, plans a path with Nav2 around obstacles, drives smoothly to the target room, and performs an arm-reach gesture on arrival.

The Fetch URDF and the scenario URDFs (kitchen, living room furniture) live in [urdfs/](urdfs/) and are **not modified**. The ROS 2 package in [fetch_home_sim/](fetch_home_sim/) wraps them with Gazebo plugins, navigation config, and a voice → intent → action pipeline.

---

## Table of Contents

- [What it does](#what-it-does)
- [Stack](#stack)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Install](#install)
- [Run](#run)
- [Talking to the robot](#talking-to-the-robot)
- [How it fits together](#how-it-fits-together)
- [Customizing](#customizing)
- [Known limitations](#known-limitations)
- [License](#license)

---

## What it does

- **Home environment** — outer walls + partition with a doorway between a kitchen and living room, your URDF furniture (couch, armchair, dining table, TV + TV table, kitchen counter) spawned in place, and a banana on the kitchen counter.
- **Autonomous navigation** — Nav2 with DWB local planner, voxel + inflation costmaps from the Fetch's 2-D laser, online SLAM (slam_toolbox) so no prebuilt map is required.
- **Smooth motion + obstacle avoidance** — capped at 0.45 m/s with 0.55 m inflation radius around the 0.30 m robot footprint; recoveries (spin / back-up / wait) on stuck detection.
- **Voice commands** — always-on microphone with an energy gate, transcribed locally with OpenAI Whisper, published as plain text on `/spoken_command`.
- **Intent dispatch** — small regex parser maps utterances to a Nav2 `NavigateToPose` goal at a named waypoint, plus an arm-reach gesture when the intent is *"pick up X"*. As specified, the robot does **not** actually grasp — it drives to the place and performs the reach motion.

## Stack

| Component | Choice |
|-----------|--------|
| Simulator | Gazebo Classic 11 |
| Middleware | ROS 2 Humble |
| Navigation | Nav2 (DWB + voxel costmap) |
| Mapping | slam_toolbox (online async) |
| Speech-to-text | OpenAI Whisper (local, CPU or GPU) |
| Audio capture | sounddevice + numpy |
| Robot model | Fetch Robotics URDF (lightly modified — see [urdfs/fetch/robots/FETCH_MODIFICATIONS.md](urdfs/fetch/robots/FETCH_MODIFICATIONS.md)) |

## Repository layout

```
Robot-SImulation/
├── urdfs/
│   ├── fetch/                          # Fetch URDF + meshes (unmodified)
│   └── assets/                         # Kitchen + living-room URDFs and meshes
│       ├── kitchen/
│       └── living_room/
├── fetch_home_sim/                     # ROS 2 package (ament_python)
│   ├── worlds/home.world               # walls, floors, partition, banana
│   ├── urdf/fetch_gazebo.xml           # Gazebo plugin block spliced into fetch.urdf
│   ├── config/
│   │   ├── nav2_params.yaml            # Nav2 + DWB + costmaps
│   │   ├── slam_toolbox_params.yaml    # online SLAM
│   │   └── waypoints.yaml              # named places + object→place table
│   ├── launch/
│   │   ├── simulation.launch.py        # Gazebo + Fetch + scene URDFs
│   │   ├── navigation.launch.py        # Nav2 (slam | localization)
│   │   ├── voice.launch.py             # mic + dispatcher + arm_reach
│   │   └── bringup.launch.py           # all of the above
│   └── fetch_home_sim/
│       ├── urdf_utils.py               # rewrites package:// → file://, adds plugins
│       ├── voice_listener.py           # sounddevice + Whisper → /spoken_command
│       ├── command_dispatcher.py       # intent parser → NavigateToPose
│       └── arm_reach.py                # /reach_target → JointTrajectory
├── fetch_home_sim/QUICKSTART.md        # short version of these run instructions
└── README.md
```

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Ubuntu | 22.04 LTS |
| ROS 2 | Humble Hawksbill |
| Gazebo | Classic 11 |
| Python | ≥ 3.10 |
| RAM | 8 GB minimum, 16 GB recommended |
| GPU (optional) | speeds up Whisper transcription |

## Install

### Option A — Docker (zero setup)

```bash
git clone <this-repo> Robot-SImulation
cd Robot-SImulation/docker
./run.sh
```

The script builds an image with ROS 2 Humble + Gazebo Classic + Nav2 + Whisper, sets up X11 forwarding so the Gazebo GUI displays on your host, and drops you into a shell inside the container with the workspace already built. Skip ahead to [Run](#run).

### Option B — Native install on Ubuntu 22.04

```bash
# 1. ROS 2 + Gazebo + Nav2
sudo apt install \
  ros-humble-nav2-bringup \
  ros-humble-navigation2 \
  ros-humble-slam-toolbox \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-robot-state-publisher \
  ros-humble-rviz2 \
  ros-humble-xacro \
  python3-colcon-common-extensions

# 2. Voice deps (only if you want mic input — text mode works without these)
sudo apt install portaudio19-dev
pip install --user sounddevice numpy openai-whisper

# 3. If colcon complains about --editable, pin setuptools
pip install setuptools==58.2.0

# 4. Workspace + symlink + build
mkdir -p ~/fetch_ws/src
ln -s ~/Desktop/Robot-SImulation/fetch_home_sim ~/fetch_ws/src/fetch_home_sim
cd ~/fetch_ws && colcon build --symlink-install
source install/setup.bash

# 5. Tell the launch files where the URDFs/meshes live
export FETCH_HOME_SIM_REPO=~/Desktop/Robot-SImulation
```

## Run

Each terminal needs `source ~/fetch_ws/install/setup.bash` and the `FETCH_HOME_SIM_REPO` export.

```bash
# Terminal 1 — Gazebo + robot + scene
ros2 launch fetch_home_sim simulation.launch.py

# Terminal 2 — Nav2 with online SLAM (RViz comes up too)
ros2 launch fetch_home_sim navigation.launch.py mode:=slam

# Terminal 3 — auto-mapping tour (one-shot). Drives a fixed loop through the
# whole house so the SLAM map covers everything, then returns home and prints
# "MAPPING TOUR COMPLETE — robot is READY for commands." Takes ~1–2 minutes.
ros2 run fetch_home_sim auto_mapper

# Terminal 4 — dispatcher + arm_reach + (optional) voice listener
ros2 launch fetch_home_sim voice.launch.py mode:=voice whisper_model:=base.en    # live mic + Whisper
ros2 launch fetch_home_sim voice.launch.py mode:=none                            # no input node

# Terminal 5 (only for text mode) — run text_input standalone, stdin only works this way
ros2 run fetch_home_sim text_input
```

> **Why the auto_mapper step?** In SLAM mode the costmap only knows what the
> laser has seen. Sending *"go to the kitchen"* before the robot has driven
> there causes Nav2 to reject the goal because the destination is in
> unknown space. The tour seeds the map; after it finishes, every named
> waypoint is reachable. You can skip it once you save a map (see below).

Or once everything is happy, the all-in-one:

```bash
ros2 launch fetch_home_sim bringup.launch.py
```

### Localization mode (with a saved map)

```bash
# Drive around manually first to map, then save:
ros2 run nav2_map_server map_saver_cli -f ~/fetch_ws/src/fetch_home_sim/maps/home_map

# Re-run with the saved map instead of SLAM:
ros2 launch fetch_home_sim navigation.launch.py mode:=localization \
  map:=$HOME/fetch_ws/src/fetch_home_sim/maps/home_map.yaml
```

## Talking to the robot

Three input modes, picked via the `mode:=` arg on `voice.launch.py`:

### Text mode (`ros2 run fetch_home_sim text_input`)
Run the text node in its own terminal — no audio stack needed. Best for first run, scripted demos, or when the mic is uncooperative.

```
> pick up the banana from the kitchen
> go to the living room
> stop
> quit
```

The dispatcher prints `COMMAND RECEIVED: ...` for every message on `/spoken_command`, followed by the parsed intent and the Nav2 goal lifecycle.

### Voice mode (`mode:=voice`)
Live microphone → energy gate → Whisper STT → `/spoken_command`. No wake word; Whisper fires after ~700 ms of silence.

| Say | Result |
|-----|--------|
| *"Pick up the banana from the kitchen"* | Drives to the `kitchen` waypoint, performs a pre-grasp arm reach. |
| *"Fetch the spoon"* | Object word implies the kitchen, navigates there + reaches. |
| *"Go to the living room"* | Navigates to the `living_room` waypoint. |
| *"Move to the couch"* | Navigates to the couch. |
| *"Stop"* / *"Cancel"* | Cancels the active Nav2 goal. |

Whisper model trade-offs (set via `whisper_model:=...`): `tiny.en` (39 MB, ~150 ms) → `base.en` (74 MB, ~500 ms, **default**) → `small.en` (244 MB, ~1.5 s) → `medium.en` (769 MB, GPU recommended). Larger models = better accent / noise robustness, slower CPU latency.

### Manual mode (`mode:=none`)
Skip both input nodes; publish to `/spoken_command` yourself:

```bash
ros2 topic pub --once /spoken_command std_msgs/String \
  "{data: 'pick up the banana from the kitchen'}"
```

## How it fits together

```
┌─────────────────────────────────────────────────────────────────┐
│                       Gazebo Classic 11                         │
│  home.world  ──►  Fetch URDF + plugins  ──►  /scan /odom /tf   │
│                   Static scene URDFs                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │ ROS 2 topics
        ┌─────────────┼─────────────────────────┐
        ▼             ▼                         ▼
   ┌─────────┐   ┌──────────┐           ┌───────────────┐
   │  Nav2   │   │ slam_    │           │ voice_listener│ mic
   │ (DWB +  │◄──┤ toolbox  │           │   (Whisper)   │◄────
   │ costmap)│   │  /map    │           └──────┬────────┘
   └────┬────┘   └──────────┘                  │ /spoken_command
        ▲                                      ▼
        │                              ┌───────────────────┐
        │      NavigateToPose          │ command_dispatcher│
        └──────────────────────────────┤ (intent parsing)  │
                                       └───────┬───────────┘
                                               │ /reach_target
                                               ▼
                                       ┌───────────────────┐
                                       │    arm_reach      │
                                       │ JointTrajectory   │
                                       └───────────────────┘
```

`urdf_utils.py` runs at launch time:
1. Reads [urdfs/fetch/robots/fetch.urdf](urdfs/fetch/robots/fetch.urdf) and rewrites `package://fetch_description/meshes/...` to absolute `file://` paths so meshes load without a wrapper package.
2. Splices [fetch_home_sim/urdf/fetch_gazebo.xml](fetch_home_sim/urdf/fetch_gazebo.xml) (diff drive, laser, RGBD camera, joint state, joint pose trajectory plugins) before `</robot>`.
3. Does the same `package://` → `file://` rewrite for the scenario URDFs in [urdfs/assets/](urdfs/assets/).

The prepared URDFs are written to `/tmp/fetch_home_sim_urdf/` and spawned by `gazebo_ros::spawn_entity.py`.

## Customizing

### Add a new waypoint or object

Edit [fetch_home_sim/config/waypoints.yaml](fetch_home_sim/config/waypoints.yaml):

```yaml
waypoints:
  bedroom:
    x: 3.5
    y: -3.0
    yaw: 1.5708
objects:
  pillow: bedroom
```

Now *"go to the bedroom"* and *"fetch the pillow"* both work — no code change.

### Add furniture

Drop a URDF into [urdfs/assets/](urdfs/assets/), add it to the `SCENE_LAYOUT` list and the prepared-URDF map in [fetch_home_sim/launch/simulation.launch.py](fetch_home_sim/launch/simulation.launch.py) and [fetch_home_sim/fetch_home_sim/urdf_utils.py](fetch_home_sim/fetch_home_sim/urdf_utils.py).

### Tune motion

Speed, acceleration, footprint and inflation are in [fetch_home_sim/config/nav2_params.yaml](fetch_home_sim/config/nav2_params.yaml). Defaults: `max_vel_x: 0.45`, `acc_lim_x: 1.0`, `inflation_radius: 0.55`, `robot_radius: 0.30`.

## Known limitations

- The Fetch URDF carries no `<transmission>` elements — arm motion is driven through the `gazebo_ros_joint_pose_trajectory` plugin (kinematic, not ros2_control). Good enough for a visual reach demo, not for precise manipulation or grasping.
- Online SLAM means the global costmap is empty until the robot has driven around. Either drive manually first via the RViz "Nav2 Goal" tool, or save a map and switch to `mode:=localization`.
- The banana is a yellow capsule placeholder — the [urdfs/assets/](urdfs/assets/) folder ships utensils (fork, spoon, knife, bowl) but no banana mesh. Drop one in and edit `home.world` to upgrade.
- Gazebo Classic is EOL upstream; the plugin layer in `urdf/fetch_gazebo.xml` will need rewriting for Gazebo Harmonic (`ros_gz_*` packages) when you migrate.

## Author

**Hector Tovar** — [h.tovarm07@gmail.com](mailto:h.tovarm07@gmail.com)

## License

This project is released under the [Apache 2.0 License](LICENSE).

The Fetch robot model is © Fetch Robotics and distributed under BSD-3-Clause. Scenario meshes retain their original licenses (see [urdfs/](urdfs/)).
