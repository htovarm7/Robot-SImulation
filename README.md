# Fetch Home Simulation — Gazebo + ROS 2

> **HackDays 2026 Demo** — Created by [Hector Tovar](https://github.com/htovar)

A full-stack robot simulation of a **Fetch mobile manipulator** operating inside a furnished home environment built in Gazebo. The system integrates autonomous navigation, obstacle avoidance, human-robot interaction (HRI), voice command recognition, and a Retrieval-Augmented Generation (RAG) module for natural-language Q&A.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Simulation](#running-the-simulation)
- [Voice Commands](#voice-commands)
- [RAG Question-Answering](#rag-question-answering)
- [HRI Interface](#hri-interface)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

This simulation recreates a residential interior (living room, kitchen, hallway, bedroom) populated with realistic Gazebo assets. The Fetch robot navigates the environment autonomously, reacts to humans in its field of view, listens for spoken commands, and can answer contextual questions about its surroundings or tasks using a RAG pipeline backed by a local language model.

| Component | Technology |
|-----------|-----------|
| Simulator | Gazebo Harmonic / Classic 11 |
| Middleware | ROS 2 Humble |
| Navigation | Nav2 (AMCL + SLAM Toolbox) |
| Obstacle avoidance | DWB local planner + costmap layers |
| HRI | OpenCV face detection, TF-based proximity manager |
| Voice commands | Whisper (OpenAI) + Piper TTS |
| RAG pipeline | LangChain + ChromaDB + Ollama (Llama 3) |
| Robot model | Fetch Robotics URDF / `fetch_ros` |

---

## Features

### Autonomous Navigation
- SLAM-based map building with SLAM Toolbox
- AMCL for localization on pre-built maps
- Nav2 goal sending via CLI, RViz2 interactive markers, or voice
- Dynamic re-planning around moving obstacles

### Obstacle Avoidance
- 3-D costmap inflated from LiDAR and RGBD point cloud
- Recovery behaviours: in-place spin, back-up, clear costmap
- Person-aware costmap layer that inflates around detected humans

### Human-Robot Interaction (HRI)
- Face and body detection via the robot's RGB-D camera
- Proximity zones: Fetch stops and acknowledges humans within 1.5 m
- Gaze-tracking: robot head follows the nearest detected person
- Social navigation: planner biases paths away from human standing areas

### Voice Commands
- Always-on wake-word detection (`hey fetch`)
- Whisper STT transcription (runs locally on CPU or GPU)
- Intent parser maps utterances to Nav2 goals, manipulation tasks, or RAG queries
- Piper TTS provides spoken responses through the robot's speaker topic

### RAG Q&A System
- Knowledge base built from room descriptions, object manifests, and task logs
- LangChain retrieval chain over ChromaDB vector store
- Ollama serves the local LLM (default: `llama3.2:3b` for low-resource machines)
- Answers streamed back as TTS output and logged to `~/fetch_logs/`

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Gazebo Simulation                        │
│   Home World ──► Fetch URDF ──► Sensor plugins (LiDAR, RGBD)   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ ROS 2 topics / TF
        ┌───────────────────┼───────────────────────┐
        ▼                   ▼                       ▼
  ┌──────────┐       ┌────────────┐          ┌──────────────┐
  │  Nav2    │       │    HRI     │          │ Voice / RAG  │
  │  Stack   │       │  Manager   │          │  Pipeline    │
  │ (AMCL +  │◄─────►│ (OpenCV + │          │ (Whisper +   │
  │  DWB)    │       │  TF zones) │          │  LangChain)  │
  └──────────┘       └────────────┘          └──────┬───────┘
        ▲                   ▲                       │
        └───────────────────┴───────────────────────┘
                    /fetch/cmd_vel, /tf, /joy …
```

---

## Project Structure

```
Robot-SImulation/
├── fetch_home_sim/              # Main ROS 2 package
│   ├── launch/
│   │   ├── simulation.launch.py       # Gazebo + robot_state_publisher
│   │   ├── navigation.launch.py       # Nav2 full stack
│   │   ├── hri.launch.py              # Face detection + proximity manager
│   │   └── voice_rag.launch.py        # Whisper + TTS + RAG node
│   ├── config/
│   │   ├── nav2_params.yaml
│   │   ├── slam_toolbox_params.yaml
│   │   └── rag_config.yaml
│   ├── worlds/
│   │   ├── home.world                 # Full home SDF world
│   │   └── assets/                    # Meshes, textures, model SDFs
│   │       ├── furniture/
│   │       ├── appliances/
│   │       └── decorations/
│   ├── maps/
│   │   └── home_map.pgm / .yaml       # Pre-built map for localization
│   ├── fetch_home_sim/
│   │   ├── hri_manager.py
│   │   ├── voice_interface.py
│   │   └── rag_node.py
│   ├── rag/
│   │   ├── knowledge_base/            # Markdown docs ingested into ChromaDB
│   │   ├── ingest.py                  # Builds / updates the vector store
│   │   └── query.py                   # Standalone RAG query tool
│   ├── package.xml
│   ├── setup.py
│   └── CMakeLists.txt
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   └── architecture.png
└── README.md
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Ubuntu | 22.04 LTS |
| ROS 2 | Humble Hawksbill |
| Gazebo | Classic 11 **or** Harmonic (via `ros_gz`) |
| Python | ≥ 3.10 |
| CUDA (optional) | ≥ 11.8 (speeds up Whisper) |
| Ollama | ≥ 0.3 |
| RAM | ≥ 16 GB recommended |

### ROS 2 packages

```bash
sudo apt install \
  ros-humble-nav2-bringup \
  ros-humble-slam-toolbox \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-robot-state-publisher \
  ros-humble-rviz2 \
  ros-humble-tf2-tools \
  ros-humble-image-transport
```

### Python dependencies

```bash
pip install \
  openai-whisper \
  piper-tts \
  langchain \
  langchain-community \
  chromadb \
  ollama \
  opencv-python \
  numpy \
  sounddevice \
  pvporcupine        # wake-word engine
```

---

## Installation

```bash
# 1. Create a ROS 2 workspace
mkdir -p ~/fetch_ws/src && cd ~/fetch_ws/src

# 2. Clone this repository
git clone https://github.com/<your-org>/Robot-SImulation.git

# 3. Clone Fetch robot description
git clone https://github.com/fetchrobotics/fetch_ros.git -b ros2

# 4. Install rosdep dependencies
cd ~/fetch_ws
rosdep install --from-paths src --ignore-src -r -y

# 5. Build
colcon build --symlink-install
source install/setup.bash

# 6. Pull the local LLM
ollama pull llama3.2:3b

# 7. Ingest the knowledge base into ChromaDB
python src/Robot-SImulation/fetch_home_sim/rag/ingest.py
```

---

## Running the Simulation

### Option A — All-in-one launch

```bash
# Terminal 1: Gazebo + robot
ros2 launch fetch_home_sim simulation.launch.py

# Terminal 2: Nav2 navigation stack
ros2 launch fetch_home_sim navigation.launch.py

# Terminal 3: HRI manager
ros2 launch fetch_home_sim hri.launch.py

# Terminal 4: Voice + RAG pipeline
ros2 launch fetch_home_sim voice_rag.launch.py
```

### Option B — Docker Compose

```bash
cd docker/
docker compose up
```

### Sending a navigation goal manually

```bash
ros2 topic pub /goal_pose geometry_msgs/PoseStamped \
  "{ header: { frame_id: 'map' },
     pose: { position: { x: 2.5, y: -1.0, z: 0.0 },
             orientation: { w: 1.0 } } }" --once
```

### SLAM mapping mode

```bash
ros2 launch fetch_home_sim navigation.launch.py mode:=slam
```

Save the map after exploration:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/fetch_ws/src/Robot-SImulation/fetch_home_sim/maps/home_map
```

---

## Voice Commands

After launch, say **"Hey Fetch"** to activate the listening window (3 s).

| Utterance | Action |
|-----------|--------|
| `"Go to the kitchen"` | Nav2 goal → named waypoint `kitchen` |
| `"Go to the living room"` | Nav2 goal → named waypoint `living_room` |
| `"Follow me"` | Activates person-following behaviour |
| `"Stop"` | Cancels active Nav2 goal |
| `"Come here"` | Robot navigates to the speaker's last-seen position |
| `"What is in front of you?"` | Triggers RAG query with current camera context |
| `"Tell me about the bedroom"` | RAG Q&A over knowledge base |

Custom waypoints can be added in `config/nav2_params.yaml` under `waypoints`.

---

## RAG Question-Answering

The RAG module uses a two-stage pipeline:

1. **Retrieval** — the user's question is embedded and the top-k most relevant chunks are retrieved from ChromaDB (knowledge base covers room layouts, object locations, robot capabilities, and task history).
2. **Generation** — the retrieved context + question are sent to the local Ollama LLM which generates a grounded answer.

### Standalone query (no voice)

```bash
python fetch_home_sim/rag/query.py --question "Where is the coffee machine?"
```

### Adding documents to the knowledge base

Drop any `.txt` or `.md` file into `rag/knowledge_base/` and re-run ingest:

```bash
python fetch_home_sim/rag/ingest.py --incremental
```

---

## HRI Interface

The `hri_manager` node subscribes to `/camera/color/image_raw` and `/camera/depth/image_rect_raw` and publishes:

| Topic | Type | Description |
|-------|------|-------------|
| `/hri/persons_detected` | `std_msgs/Int32` | Number of people in frame |
| `/hri/nearest_person_distance` | `std_msgs/Float32` | Distance in metres |
| `/hri/social_costmap_update` | `nav2_msgs/Costmap` | Extra inflation around humans |

Behaviour zones (configurable in `config/nav2_params.yaml`):

- **> 3 m** — normal operation
- **1.5 – 3 m** — reduced speed (0.3 m/s max)
- **< 1.5 m** — full stop, verbal acknowledgement via TTS

---

## Configuration

All tunable parameters live in `fetch_home_sim/config/`:

### `nav2_params.yaml` (selection)
```yaml
controller_server:
  ros__parameters:
    FollowPath:
      max_vel_x: 0.5
      min_vel_x: -0.25
      max_vel_theta: 1.0
```

### `rag_config.yaml`
```yaml
rag:
  model: "llama3.2:3b"       # Ollama model tag
  embedding_model: "nomic-embed-text"
  top_k: 4
  chunk_size: 512
  chunk_overlap: 64
  chroma_persist_dir: "~/.fetch_chroma"
```

### `slam_toolbox_params.yaml`
```yaml
slam_toolbox:
  ros__parameters:
    mode: localization           # or 'mapping'
    map_file_name: "home_map"
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Gazebo opens but robot not visible | Missing Fetch meshes | Re-run `rosdep install` and rebuild |
| Nav2 fails to initialise | Map not found | Check path in `nav2_params.yaml` → `yaml_filename` |
| Whisper not transcribing | No microphone detected | `arecord -l` to list devices; set `sounddevice` index in `voice_interface.py` |
| Ollama timeout | Model not pulled | `ollama pull llama3.2:3b` |
| ChromaDB empty | Ingest not run | `python rag/ingest.py` |
| Robot oscillates near goals | DWB tolerance too tight | Increase `xy_goal_tolerance` in `nav2_params.yaml` |

---

## Author

**Hector Tovar** — [h.tovarm07@gmail.com](mailto:h.tovarm07@gmail.com)

Built as a live demo for **HackDays 2026**, showcasing how open-source robotics stacks (ROS 2, Nav2, Gazebo) can be combined with modern AI tooling (Whisper, RAG, local LLMs) to produce an interactive home robot in simulation.

---

## License

This project is released under the [Apache 2.0 License](LICENSE).

The Fetch robot model is © Fetch Robotics and distributed under BSD-3-Clause.
Gazebo assets sourced from the Open-Source Robotics Foundation model database are distributed under their respective licenses (see `worlds/assets/LICENSES`).
