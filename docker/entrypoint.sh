#!/usr/bin/env bash
# Entrypoint that links the bind-mounted repo into the colcon workspace and
# builds it the first time the container starts.

set -e

source /opt/ros/humble/setup.bash

REPO=/repo
WS=/home/ros/fetch_ws

if [ ! -d "$REPO/fetch_home_sim" ]; then
    echo "ERROR: $REPO/fetch_home_sim not found."
    echo "Run the container with -v /path/to/Robot-SImulation:/repo"
    exit 1
fi

# (Re)create the symlink so we always reference the bind-mounted source.
rm -f "$WS/src/fetch_home_sim"
ln -s "$REPO/fetch_home_sim" "$WS/src/fetch_home_sim"

# Build only if the install dir is missing (first run) or src is newer.
if [ ! -d "$WS/install/fetch_home_sim" ] || [ "$1" = "--rebuild" ]; then
    echo ">>> Building fetch_home_sim ..."
    cd "$WS"
    colcon build --symlink-install
    [ "$1" = "--rebuild" ] && shift
fi

source "$WS/install/setup.bash"
export FETCH_HOME_SIM_REPO="$REPO"

exec "$@"
