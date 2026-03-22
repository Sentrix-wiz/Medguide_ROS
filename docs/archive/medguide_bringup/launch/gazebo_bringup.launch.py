#!/usr/bin/env python3
"""
Gazebo simulation launch for MedGuide hospital environment.

Spawns TurtleBot3 Burger in hospital world with initial setup.
"""

import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for Gazebo simulation."""
    
    # Get packages
    from ament_index_python.packages import get_package_share_directory
    
    gazebo_ros_dir = get_package_share_directory('gazebo_ros')
    turtlebot3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    medguide_bringup_dir = get_package_share_directory('medguide_bringup')
    
    # Paths
    world_file = os.path.join(
        medguide_bringup_dir,
        '..',
        '..',
        'worlds',
        'hospital_floor.world'
    )
    
    # Declare launch arguments
    launch_args = [
        DeclareLaunchArgument(
            'gazebo_gui',
            default_value='true',
            description='Launch Gazebo GUI'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),
    ]
    
    # Gazebo server
    gazebo_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_dir, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={'world': world_file}.items(),
    )
    
    # Gazebo client (GUI) - conditional
    gazebo_client = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_dir, 'launch', 'gzclient.launch.py')
        ),
        condition=LaunchConfiguration('gazebo_gui'),
    )
    
    # TurtleBot3 spawn (from turtlebot3_gazebo package)
    # This assumes TurtleBot3 packages are installed
    spawn_turtlebot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_gazebo_dir, 'launch', 'spawn_turtlebot3.launch.py')
        ),
        launch_arguments={
            'x_pose': '0.5',
            'y_pose': '0.5',
            'z_pose': '0.0'
        }.items(),
    )
    
    return LaunchDescription(
        launch_args + [
            gazebo_server,
            gazebo_client,
            spawn_turtlebot,
        ]
    )
