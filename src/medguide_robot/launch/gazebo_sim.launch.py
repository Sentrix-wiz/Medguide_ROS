#!/usr/bin/env python3
"""
Gazebo Simulation Launch — Phase 2.

Launches TurtleBot3 Burger in the MedGuide hospital world.
This is the foundation for all simulation-based development.

Requires:
    export TURTLEBOT3_MODEL=burger

Usage:
    ros2 launch medguide_robot gazebo_sim.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """Launch Gazebo with TurtleBot3 in the hospital world."""
    # Package directories
    turtlebot3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    gazebo_ros_dir = get_package_share_directory('gazebo_ros')
    medguide_dir = get_package_share_directory('medguide_robot')

    # Path to our custom hospital world
    world_file = os.path.join(medguide_dir, 'worlds', 'hospital_floor.world')

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    x_pose = LaunchConfiguration('x_pose', default='1.0')   # Dock position
    y_pose = LaunchConfiguration('y_pose', default='1.2')

    # Ensure TURTLEBOT3_MODEL is set
    set_tb3_model = SetEnvironmentVariable(
        name='TURTLEBOT3_MODEL',
        value='burger'
    )

    # 1. Gazebo server (physics engine) with hospital world
    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_dir, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={'world': world_file}.items(),
    )

    # 2. Gazebo client (GUI)
    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_dir, 'launch', 'gzclient.launch.py')
        ),
    )

    # 3. Robot state publisher (TF from URDF)
    robot_state_pub = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_gazebo_dir, 'launch',
                         'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    # 4. Spawn TurtleBot3 at dock position
    spawn_robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_gazebo_dir, 'launch',
                         'spawn_turtlebot3.launch.py')
        ),
        launch_arguments={
            'x_pose': x_pose,
            'y_pose': y_pose,
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('x_pose', default_value='0.5',
                              description='Robot spawn X (dock)'),
        DeclareLaunchArgument('y_pose', default_value='0.5',
                              description='Robot spawn Y (dock)'),
        set_tb3_model,
        gzserver,
        gzclient,
        robot_state_pub,
        spawn_robot,
    ])
