FROM ros:humble-desktop

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install essential tools and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    nano \
    vim \
    python3-colcon-common-extensions \
    python3-colcon-cmake \
    python3-colcon-python-setup-py \
    python3-pip \
    gazebo \
    ros-humble-gazebo-ros \
    ros-humble-gazebo-plugins \
    ros-humble-gazebo-msgs \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-gazebo \
    ros-humble-turtlebot3-simulations \
    ros-humble-nav2-bringup \
    ros-humble-nav2-stack \
    ros-humble-navigation2 \
    ros-humble-rviz2 \
    ros-humble-rqt-graph \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
WORKDIR /home/ros/medguide_ws

# Copy workspace
COPY . /home/ros/medguide_ws/

# Build workspace
RUN /bin/bash -c 'source /opt/ros/humble/setup.bash && \
    colcon build --symlink-install'

# Source the built workspace
RUN echo "source /home/ros/medguide_ws/install/setup.bash" >> /home/ros/.bashrc

# Set up ROS environment
ENV PYTHONPATH=/home/ros/medguide_ws/install/lib/python3.10/site-packages:$PYTHONPATH
ENV ROS_PACKAGE_PATH=/home/ros/medguide_ws/src:$ROS_PACKAGE_PATH

# Default command
CMD ["/bin/bash"]

# Labels for documentation
LABEL maintainer="MedGuide Robotics Team"
LABEL description="MedGuide - Autonomous Hospital Assistant Robot ROS2 Humble"
LABEL version="0.1.0"
