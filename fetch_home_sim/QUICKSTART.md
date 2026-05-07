# fetch_home_sim — Quickstart

Autonomous Fetch home simulation for **ROS 2 Humble + Gazebo Classic 11**.

The robot listens for commands (mic or stdin), parses simple intents like
*"pick up the banana from the kitchen"*, sends a Nav2 `NavigateToPose` goal
to the matching named waypoint, avoids obstacles, drives smoothly, and
performs an arm-reach gesture on arrival.

> The original Fetch URDF and scenario URDFs live in `../urdfs/`. They are
> **not modified**; `urdf_utils.py` rewrites their `package://` mesh paths
> to absolute `file://` URIs at launch time, locks kitchen drawer/fridge
> joints to fixed, marks scene URDFs as static, and splices a Gazebo
> plugin block onto the Fetch.

---

## Option A — Docker (recommended for first run)

```bash
cd docker
./run.sh
```

This builds the image (ROS 2 Humble + Gazebo Classic + Nav2 + Whisper) and
opens a shell inside the container with X11 forwarding so the Gazebo GUI
can display on your host. Inside the container, jump straight to
[Step 4 — Run](#4-run).

## Option B — Native install

### 1. System deps

```bash
sudo apt install \
  ros-humble-nav2-bringup \
  ros-humble-navigation2 \
  ros-humble-slam-toolbox \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-robot-state-publisher \
  ros-humble-rviz2 \
  ros-humble-xacro \
  python3-colcon-common-extensions

# For voice mode only
sudo apt install portaudio19-dev
pip install --user sounddevice numpy openai-whisper
```

If `colcon build` fails with `option --editable not recognized`, pin
setuptools: `pip install setuptools==58.2.0`.

### 2. Workspace

```bash
mkdir -p ~/fetch_ws/src
ln -s ~/Desktop/Robot-SImulation/fetch_home_sim ~/fetch_ws/src/fetch_home_sim
cd ~/fetch_ws
colcon build --symlink-install
source install/setup.bash
export FETCH_HOME_SIM_REPO=~/Desktop/Robot-SImulation
```

### 3. Run

Three terminals (each needs `source ~/fetch_ws/install/setup.bash` and the
`FETCH_HOME_SIM_REPO` export):

```bash
# Terminal 1 — Gazebo + robot + scene
ros2 launch fetch_home_sim simulation.launch.py

# Terminal 2 — Nav2 + online SLAM (RViz comes up too)
ros2 launch fetch_home_sim navigation.launch.py mode:=slam

# Terminal 3 — input pipeline (pick one mode)
ros2 launch fetch_home_sim voice.launch.py mode:=text                    # type at terminal
ros2 launch fetch_home_sim voice.launch.py mode:=voice whisper_model:=base.en   # live mic
ros2 launch fetch_home_sim voice.launch.py mode:=none                    # publish manually
```

## 4. Talk to the robot

### Text mode

After `mode:=text`, just type and press Enter:

```
> pick up the banana from the kitchen
> go to the living room
> move to the couch
> stop
> quit
```

### Voice mode

After `mode:=voice`, speak naturally — the energy gate triggers Whisper
after ~700 ms of silence; no wake word needed.

| Say | Result |
|-----|--------|
| *"Pick up the banana from the kitchen"* | Drives to `kitchen`, performs a pre-grasp arm reach. |
| *"Fetch the spoon"* | Object word implies the kitchen, navigates + reaches. |
| *"Go to the living room"* | Navigates to `living_room`. |
| *"Move to the couch"* | Navigates to `couch`. |
| *"Stop"* / *"Cancel"* | Cancels the active Nav2 goal. |

Whisper model trade-offs:

| Model | Size | CPU latency | Use when |
|-------|------|-------------|----------|
| `tiny.en` | 39 MB | ~150 ms | Quick iteration on a slow CPU |
| `base.en` | 74 MB | ~500 ms | **Default — best balance** |
| `small.en` | 244 MB | ~1.5 s | Accents or noise |
| `medium.en` | 769 MB | ~4 s CPU | GPU only |

### None / manual mode

```bash
ros2 topic pub --once /spoken_command std_msgs/String \
  "{data: 'pick up the banana from the kitchen'}"
```

## 5. Layout

```
fetch_home_sim/
├── worlds/home.world          # 14×14m house, two rooms, doorway, banana
├── urdf/fetch_gazebo.xml      # plugins spliced onto fetch.urdf at launch
├── config/
│   ├── nav2_params.yaml
│   ├── slam_toolbox_params.yaml
│   └── waypoints.yaml         # named places + object→place table
├── launch/
│   ├── simulation.launch.py   # Gazebo + Fetch + scene URDFs
│   ├── navigation.launch.py   # Nav2 (slam | localization)
│   ├── voice.launch.py        # mode: voice | text | none
│   └── bringup.launch.py      # all of the above
└── fetch_home_sim/
    ├── urdf_utils.py          # rewrites package:// → file://, locks joints, adds plugins
    ├── voice_listener.py      # sounddevice + Whisper → /spoken_command
    ├── text_input.py          # stdin → /spoken_command
    ├── command_dispatcher.py  # intent parsing → NavigateToPose
    └── arm_reach.py           # /reach_target → JointTrajectory
```

## 6. Topics worth knowing

| Topic | Type | Direction |
|-------|------|-----------|
| `/cmd_vel` | `geometry_msgs/Twist` | Nav2 → diff drive |
| `/odom` | `nav_msgs/Odometry` | Gazebo → Nav2 |
| `/scan` | `sensor_msgs/LaserScan` | Gazebo → Nav2 |
| `/joint_states` | `sensor_msgs/JointState` | Gazebo → robot_state_publisher |
| `/set_joint_trajectory` | `trajectory_msgs/JointTrajectory` | arm_reach → Gazebo |
| `/spoken_command` | `std_msgs/String` | input → dispatcher |
| `/reach_target` | `std_msgs/String` | dispatcher → arm_reach |

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `option --editable not recognized` | `pip install setuptools==58.2.0` then re-`colcon build` |
| `package 'nav2_bringup' not found` | `sudo apt install ros-humble-nav2-bringup ros-humble-navigation2` |
| `Invalid XML: Namespace prefix sensor on camera` | Already handled — make sure you're on the latest `urdf_utils.py` and rebuilt. |
| `EXCEPTION: Unknown geometry type` | Already handled — banana switched from capsule to cylinder. Rebuild. |
| Whisper crashes with `module 'coverage' has no attribute 'types'` | `pip install --user -U numba "coverage>=7.6"` |
| Kitchen materials show as white | Cosmetic; URDF materials don't map to Ogre scripts. Ignore. |
| Robot can't reach a goal across the house | SLAM map is empty until you've driven there. Drive manually with the RViz "Nav2 Goal" tool first, or pre-build a map. |
