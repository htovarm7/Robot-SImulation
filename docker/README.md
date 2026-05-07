# Docker setup for fetch_home_sim

A self-contained ROS 2 Humble + Gazebo Classic 11 + Nav2 + Whisper
environment so you don't have to install anything on your host beyond Docker.

## Requirements

- Docker (≥ 20.10)
- Linux host with X11 (Xorg or XWayland) — Gazebo and RViz need a display.
- (Optional) PulseAudio for voice mode.
- (Optional) NVIDIA GPU + `nvidia-container-toolkit` for faster Whisper.

> **macOS / Windows:** the GUI parts (Gazebo, RViz) need extra setup
> (XQuartz / VcXsrv). Text mode works as-is.

## Quick start

```bash
cd docker
./run.sh
```

First run takes 5–10 minutes to download the base image and install deps.
Subsequent runs are instant. The script:

1. Builds the image as your UID/GID so bind-mounted files don't end up root-owned.
2. Allows the container to use your X server (`xhost +local:docker`).
3. Forwards `/dev/snd` and the PulseAudio socket if available.
4. Adds `--gpus all` if `nvidia-smi` is on your host.
5. Bind-mounts the repo at `/repo` and drops you into a bash shell.

Inside the container the workspace is at `/home/ros/fetch_ws` and is built
on first start. Then run the simulation in three terminals (use `tmux` or
`docker exec` for additional terminals — see below):

```bash
# Terminal 1
ros2 launch fetch_home_sim simulation.launch.py

# Terminal 2
ros2 launch fetch_home_sim navigation.launch.py mode:=slam

# Terminal 3
ros2 launch fetch_home_sim voice.launch.py mode:=text
```

## Extra terminals into the same container

```bash
docker exec -it fetch_home_sim bash
```

(or use `tmux` inside the container — it's installed.)

## Rebuild after editing code

The repo is bind-mounted, so Python edits are live. For Python entry-point
or launch-file changes, rebuild inside the container:

```bash
cd ~/fetch_ws
colcon build --symlink-install
source install/setup.bash
```

To rebuild the Docker image itself (e.g. after editing the Dockerfile):

```bash
docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) \
  -t fetch_home_sim:humble docker/
```

## docker-compose alternative

```bash
cd docker
UID=$(id -u) GID=$(id -g) docker compose run --rm fetch
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `cannot connect to X server` | Run `xhost +local:docker` on the host. |
| Gazebo opens but everything is black | Add `--gpus all` (NVIDIA) or install Mesa GL drivers in the image. |
| No audio in voice mode | Check `pactl info` works on the host; verify the PulseAudio socket bind-mount. |
| `nvidia-smi` not found in container | Install `nvidia-container-toolkit` on the host: `sudo apt install nvidia-container-toolkit`. |
| Whisper download is slow | Models are cached in `~/.cache/whisper` *inside the container*; mount a host dir to keep them between runs (edit `run.sh`). |
