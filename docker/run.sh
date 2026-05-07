#!/usr/bin/env bash
# One-shot helper: builds the image (first time only) and opens an
# interactive shell inside the container with X11 + audio forwarded.

set -e

IMAGE=fetch_home_sim:humble
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Build the image if it doesn't exist (rebuild with: docker build ...).
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo ">>> Building $IMAGE (one-time, ~5–10 min) ..."
    docker build \
        --build-arg UID="$(id -u)" \
        --build-arg GID="$(id -g)" \
        -t "$IMAGE" \
        "$(dirname "$0")"
fi

# 2. Allow the container to talk to your X server.
xhost +local:docker >/dev/null 2>&1 || true

# 3. Audio: bind-mount PulseAudio socket if it exists (voice mode only).
PULSE_ARGS=()
if [ -n "$XDG_RUNTIME_DIR" ] && [ -S "$XDG_RUNTIME_DIR/pulse/native" ]; then
    PULSE_ARGS+=(
        -e "PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native"
        -v "$XDG_RUNTIME_DIR/pulse/native:/run/user/$(id -u)/pulse/native"
        -v "$HOME/.config/pulse/cookie:/home/ros/.config/pulse/cookie:ro"
    )
fi

# 4. GPU passthrough (NVIDIA only). Comment out if you don't have it.
GPU_ARGS=()
if command -v nvidia-smi >/dev/null 2>&1; then
    GPU_ARGS+=(--gpus all)
fi

echo ">>> Starting $IMAGE — repo mounted at /repo"
exec docker run --rm -it \
    --name fetch_home_sim \
    --network host \
    -e DISPLAY="$DISPLAY" \
    -e QT_X11_NO_MITSHM=1 \
    -e XAUTHORITY=/tmp/.Xauthority \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
    -v "${XAUTHORITY:-$HOME/.Xauthority}:/tmp/.Xauthority:ro" \
    -v "$REPO_ROOT:/repo" \
    --device /dev/snd \
    "${PULSE_ARGS[@]}" \
    "${GPU_ARGS[@]}" \
    "$IMAGE"
