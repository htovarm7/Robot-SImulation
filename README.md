# Fetch Home Simulation — Gazebo Classic + ROS 2 Humble

> Created by [Hector Tovar](https://github.com/htovarm7)

A Gazebo simulation of the **Fetch mobile manipulator** operating autonomously inside a furnished home. The robot accepts natural-language commands like *"pick up the banana from the kitchen"*, plans a collision-free path with Nav2, navigates smoothly to the target room, and logs the reach intent on arrival.

---

## Stack

| Component | Choice |
|-----------|--------|
| Simulator | Gazebo Classic 11 |
| Middleware | ROS 2 Humble |
| Navigation | Nav2 — SmacPlanner2D + DWB local planner |
| Mapping | slam_toolbox (online async) |
| Speech-to-text | OpenAI Whisper (local) |
| Robot model | Fetch Robotics URDF |

---

## Repository layout

```
Robot-SImulation/
├── urdfs/
│   ├── fetch/              # Fetch URDF + meshes
│   └── assets/             # Kitchen + living-room URDFs and meshes
├── fetch_home_sim/         # ROS 2 package (ament_python)
│   ├── worlds/home.world   # 14×14 m home — two rooms, doorway, furniture, banana
│   ├── urdf/fetch_gazebo.xml
│   ├── config/
│   │   ├── nav2_params.yaml
│   │   ├── slam_toolbox_params.yaml
│   │   └── waypoints.yaml
│   ├── maps/               # Save maps here after auto_mapper run
│   ├── launch/
│   │   ├── simulation.launch.py
│   │   ├── navigation.launch.py
│   │   ├── voice.launch.py
│   │   └── bringup.launch.py
│   └── fetch_home_sim/
│       ├── urdf_utils.py       # Patches Fetch URDF at launch time
│       ├── voice_listener.py   # Whisper STT → /spoken_command
│       ├── text_input.py       # stdin → /spoken_command
│       ├── command_dispatcher.py
│       ├── arm_reach.py
│       └── auto_mapper.py
└── docker/
    ├── Dockerfile
    ├── docker-compose.yml
    └── run.sh
```

---

## Install

### Option A — Docker (recommended)

```bash
cd docker
./run.sh
```

Builds a ROS 2 Humble + Gazebo + Nav2 + Whisper image, sets up X11 forwarding, and drops you into a ready shell. Skip to [Run](#run).

### Option B — Native (Ubuntu 22.04)

```bash
sudo apt install \
  ros-humble-nav2-bringup \
  ros-humble-navigation2 \
  ros-humble-slam-toolbox \
  ros-humble-nav2-smac-planner \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-robot-state-publisher \
  ros-humble-rviz2 \
  ros-humble-xacro \
  python3-colcon-common-extensions

# Voice input only
sudo apt install portaudio19-dev
pip install --user sounddevice numpy openai-whisper

# Fix colcon --symlink-install on newer setuptools
pip install setuptools==58.2.0

mkdir -p ~/fetch_ws/src
ln -s ~/Desktop/Robot-SImulation/fetch_home_sim ~/fetch_ws/src/fetch_home_sim
cd ~/fetch_ws && colcon build --symlink-install
source install/setup.bash
export FETCH_HOME_SIM_REPO=~/Desktop/Robot-SImulation
```

---

## Run

Each terminal needs `source ~/fetch_ws/install/setup.bash` and `export FETCH_HOME_SIM_REPO=~/Desktop/Robot-SImulation`.

```bash
# T1 — Gazebo + robot + scene
ros2 launch fetch_home_sim simulation.launch.py

# T2 — Nav2 + SLAM (wait for "Managed nodes are active")
ros2 launch fetch_home_sim navigation.launch.py mode:=slam

# T3 — dispatcher + arm_reach
ros2 launch fetch_home_sim voice.launch.py mode:=none

# T4 — auto-mapping tour (~3 min, covers both rooms)
ros2 run fetch_home_sim auto_mapper

# Save the map after the tour so you only map once
ros2 run nav2_map_server map_saver_cli -f ~/fetch_ws/src/fetch_home_sim/maps/home_map

# T5 — text commands
ros2 run fetch_home_sim text_input
```

After saving the map, use localization mode to skip re-mapping:

```bash
ros2 launch fetch_home_sim navigation.launch.py mode:=localization \
  map:=$HOME/fetch_ws/src/fetch_home_sim/maps/home_map.yaml
```

---

## Commands

### Text mode

```
> pick up the banana from the kitchen
> go to the kitchen
> go to the living room
> move to the couch
> stop
```

### Voice mode (Whisper)

```bash
ros2 launch fetch_home_sim voice.launch.py mode:=voice whisper_model:=base.en
```

Speak naturally — Whisper transcribes after ~700 ms of silence.

| Model | Size | CPU latency |
|-------|------|-------------|
| `tiny.en` | 39 MB | ~150 ms |
| `base.en` | 74 MB | ~500 ms (default) |
| `small.en` | 244 MB | ~1.5 s |

### Manual publish

```bash
ros2 topic pub --once /spoken_command std_msgs/String \
  "{data: 'pick up the banana from the kitchen'}"
```

---

## Available places

`kitchen`, `living_room`, `couch`, `tv`, `armchair`, `dining_table`, `home`

Add new places in [config/waypoints.yaml](fetch_home_sim/config/waypoints.yaml) — no code change needed.

---

## Architecture

```
Gazebo ──► /scan /odom /tf ──► Nav2 (SmacPlanner + DWB)
                                      ▲
/spoken_command ──► command_dispatcher ─┘
                           │
                     /reach_target ──► arm_reach (logs intent)
```

The original Fetch URDF and asset URDFs are **not modified on disk**. `urdf_utils.py` patches them at launch time: rewrites `package://` mesh paths to absolute `file://` URIs, restores correct inertia values, locks arm joints in a tuck pose, and lowers the base collision to prevent wheel wobble.

---

## Known limitations

- Arm joints are locked fixed (no ros2_control). The reach gesture is logged but not physically executed.
- Navigation in unmapped areas will fail — run `auto_mapper` first or provide a saved map.
- Gazebo Classic is EOL; migrating to Gazebo Harmonic requires rewriting the plugin layer.

---

## Author

**Hector Tovar** — [h.tovarm07@gmail.com](mailto:h.tovarm07@gmail.com)

## License

Apache 2.0. Fetch robot model © Fetch Robotics, BSD-3-Clause.
