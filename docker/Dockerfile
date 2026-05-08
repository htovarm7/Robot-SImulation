FROM osrf/ros:humble-desktop-full

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-humble-nav2-bringup \
      ros-humble-navigation2 \
      ros-humble-slam-toolbox \
      ros-humble-nav2-smac-planner \
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

# ament_python needs setuptools < 64
RUN pip3 install --no-cache-dir setuptools==58.2.0

RUN pip3 install --no-cache-dir \
      sounddevice \
      numpy \
      "coverage>=7.6" \
      openai-whisper \
      pyyaml

ARG UID=1000
ARG GID=1000
ARG USER=ros
RUN groupadd -g ${GID} ${USER} \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USER} \
    && echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER ${USER}
WORKDIR /home/${USER}
RUN mkdir -p /home/${USER}/fetch_ws/src

RUN echo "source /opt/ros/humble/setup.bash" >> /home/${USER}/.bashrc \
    && echo "[ -f /home/${USER}/fetch_ws/install/setup.bash ] && source /home/${USER}/fetch_ws/install/setup.bash" >> /home/${USER}/.bashrc \
    && echo "export FETCH_HOME_SIM_REPO=/repo" >> /home/${USER}/.bashrc \
    && echo "export QT_X11_NO_MITSHM=1" >> /home/${USER}/.bashrc

COPY --chown=${USER}:${USER} entrypoint.sh /home/${USER}/entrypoint.sh
RUN chmod +x /home/${USER}/entrypoint.sh

ENTRYPOINT ["/home/ros/entrypoint.sh"]
CMD ["bash"]
