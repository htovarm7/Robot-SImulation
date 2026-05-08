# Docker

Self-contained ROS 2 Humble + Gazebo Classic 11 + Nav2 + Whisper environment.

## Requirements

- Docker ≥ 20.10
- Linux with X11 (Xorg or XWayland)
- Optional: PulseAudio (voice mode), NVIDIA GPU + nvidia-container-toolkit (faster Whisper)

## Quick start

```bash
cd docker
./run.sh
```

First run builds the image (~5–10 min). Inside the container the workspace is
at `~/fetch_ws` and is built automatically on first start.

Run the simulation (use `tmux` or `docker exec` for extra terminals):

```bash
ros2 launch fetch_home_sim simulation.launch.py
ros2 launch fetch_home_sim navigation.launch.py mode:=slam
ros2 launch fetch_home_sim voice.launch.py mode:=none
ros2 run fetch_home_sim auto_mapper
ros2 run fetch_home_sim text_input
```

## Extra terminals

```bash
docker exec -it fetch_home_sim bash
```

## docker-compose alternative

```bash
UID=$(id -u) GID=$(id -g) docker compose run --rm fetch
```

## Rebuild after editing Python code

Python files are bind-mounted so edits are live. For entry-point or launch
file changes, rebuild inside the container:

```bash
cd ~/fetch_ws && colcon build --symlink-install && source install/setup.bash
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `cannot connect to X server` | Run `xhost +local:docker` on the host |
| No audio in voice mode | Check `pactl info` on the host; verify PulseAudio socket mount |
| Whisper models re-download every run | Mount `~/.cache/whisper` as a volume in `run.sh` |
