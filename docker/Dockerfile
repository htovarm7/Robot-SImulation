# ROS 2 Humble + Gazebo Classic 11 + Nav2 + Whisper, ready to run fetch_home_sim.
FROM osrf/ros:humble-desktop-full

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
SHELL ["/bin/bash", "-c"]

# System deps: Nav2, SLAM, audio, build tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-humble-nav2-bringup \
      ros-humble-navigation2 \
      ros-humble-slam-toolbox \
      ros-humble-gazebo-ros-pkgs \
      ros-humble-robot-state-publisher \
      ros-humble-rviz2 \
      ros-humble-xacro \
      python3-colcon-common-extensions \
      python3-pip \
      portaudio19-dev \
      alsa-utils \
      pulseaudio-utils \
      git \
      sudo \
      vim \
      tmux \
    && rm -rf /var/lib/apt/lists/*

# Pin setuptools to the version ament_python expects (newer setuptools dropped
# the --editable flag colcon --symlink-install needs).
RUN pip3 install --no-cache-dir setuptools==58.2.0

# Python deps for the voice pipeline. Whisper pulls in numba, torch, etc.
RUN pip3 install --no-cache-dir \
      sounddevice \
      numpy \
      "coverage>=7.6" \
      openai-whisper \
      pyyaml

# Non-root user matching common host UID so bind-mounted files don't end up
# owned by root. Override at build time with --build-arg UID=$(id -u).
ARG UID=1000
ARG GID=1000
ARG USER=ros
RUN groupadd -g ${GID} ${USER} \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USER} \
    && echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Workspace layout. The repo gets bind-mounted at /repo at runtime; we symlink
# fetch_home_sim into the colcon src directory so colcon picks it up.
USER ${USER}
WORKDIR /home/${USER}
RUN mkdir -p /home/${USER}/fetch_ws/src

# Auto-source ROS + the workspace overlay in every shell.
RUN echo "source /opt/ros/humble/setup.bash" >> /home/${USER}/.bashrc \
    && echo "[ -f /home/${USER}/fetch_ws/install/setup.bash ] && source /home/${USER}/fetch_ws/install/setup.bash" >> /home/${USER}/.bashrc \
    && echo "export FETCH_HOME_SIM_REPO=/repo" >> /home/${USER}/.bashrc \
    && echo "export QT_X11_NO_MITSHM=1" >> /home/${USER}/.bashrc

COPY --chown=${USER}:${USER} entrypoint.sh /home/${USER}/entrypoint.sh
RUN chmod +x /home/${USER}/entrypoint.sh

ENTRYPOINT ["/home/ros/entrypoint.sh"]
CMD ["bash"]
