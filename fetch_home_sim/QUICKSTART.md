# fetch_home_sim — Quickstart

Autonomous Fetch home simulation for **ROS 2 Humble + Gazebo Classic 11**.

The robot listens on a live mic, transcribes with Whisper, parses simple
intents like *"pick up the banana from the kitchen"*, sends a Nav2
`NavigateToPose` goal to the matching named waypoint, and executes a smooth
arm reach when it arrives. Obstacle avoidance is handled by Nav2's DWB +
inflation/voxel costmaps using the Fetch's 2-D laser.

> The original Fetch URDF and scenario URDFs live in `../urdfs/`. They are
> **not modified**; `urdf_utils.py` rewrites their `package://` mesh paths
> to absolute `file://` URIs at launch time and splices a Gazebo plugin
> block onto the Fetch.

---

## 1. Install system deps

```bash
sudo apt install \
  ros-humble-nav2-bringup \
  ros-humble-slam-toolbox \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-robot-state-publisher \
  ros-humble-rviz2 \
  ros-humble-xacro \
  python3-colcon-common-extensions

# Voice deps (live mic + Whisper)
sudo apt install portaudio19-dev
pip install --user sounddevice numpy openai-whisper
```

## 2. Make a workspace and symlink this package

```bash
mkdir -p ~/fetch_ws/src
ln -s ~/Desktop/Robot-SImulation/fetch_home_sim ~/fetch_ws/src/fetch_home_sim
cd ~/fetch_ws
colcon build --symlink-install
source install/setup.bash

# Required so launch can find the original URDFs/meshes
export FETCH_HOME_SIM_REPO=~/Desktop/Robot-SImulation
```

## 3. Run it (3 terminals)

```bash
# Terminal 1 — Gazebo + robot + scene
ros2 launch fetch_home_sim simulation.launch.py

# Terminal 2 — Nav2 with online SLAM
ros2 launch fetch_home_sim navigation.launch.py mode:=slam

# Terminal 3 — voice listener + command dispatcher + arm reach
ros2 launch fetch_home_sim voice.launch.py whisper_model:=base.en
```

Or all in one (after the above works):

```bash
ros2 launch fetch_home_sim bringup.launch.py
```

## 4. Talk to the robot

Speak naturally; the energy gate triggers Whisper after ~700 ms of silence.

| Say | Result |
|-----|--------|
| *"Pick up the banana from the kitchen"* | Drives to `kitchen` waypoint, performs a pre-grasp arm reach. |
| *"Go to the living room"* | Navigates to `living_room`. |
| *"Move to the couch"* | Navigates to `couch`. |
| *"Stop"* | Cancels the active Nav2 goal. |

If voice setup is fussy, publish text directly:

```bash
ros2 topic pub --once /spoken_command std_msgs/String \
  "{data: 'pick up the banana from the kitchen'}"
```

Add new objects/waypoints in `config/waypoints.yaml` — no code change needed.

## 5. Layout

```
fetch_home_sim/
├── worlds/home.world          # ground + walls + room floors + banana
├── urdf/fetch_gazebo.xml      # plugins spliced onto fetch.urdf at launch
├── config/
│   ├── nav2_params.yaml
│   ├── slam_toolbox_params.yaml
│   └── waypoints.yaml         # named places + object→place table
├── launch/
│   ├── simulation.launch.py   # Gazebo + Fetch + scene URDFs
│   ├── navigation.launch.py   # Nav2 (slam | localization)
│   ├── voice.launch.py        # mic + dispatcher + arm reach
│   └── bringup.launch.py      # all of the above
└── fetch_home_sim/
    ├── urdf_utils.py          # rewrites package:// → file://, adds plugins
    ├── voice_listener.py      # sounddevice + Whisper → /spoken_command
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
| `/spoken_command` | `std_msgs/String` | voice → dispatcher |
| `/reach_target` | `std_msgs/String` | dispatcher → arm_reach |

## 7. Known limitations

- The Fetch URDF carries no `<transmission>` elements; arm motion goes
  through the `gazebo_ros_joint_pose_trajectory` plugin (kinematic, not
  ros2_control). Good enough for the visual reach demo, not for precise
  manipulation.
- Online SLAM mode means the global costmap is empty until the robot has
  driven around. Either drive manually first (RViz "Nav2 Goal") or run a
  scripted exploration before issuing distant goals.
- The banana is a yellow capsule placeholder, not the URDF asset folder
  (those are utensils — fork/spoon/knife/bowl). Add a real banana mesh
  by dropping it into `worlds/` and editing `home.world`.
- Gazebo Classic is EOL upstream; the plugin layer here will need rewriting
  for Gazebo Harmonic (`ros_gz_*`) when you migrate.
