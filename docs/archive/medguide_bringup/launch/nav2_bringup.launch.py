#!/usr/bin/env python3
"""
Nav2 bringup launch for MedGuide hospital navigation.

Launches the Nav2 stack with hospital-specific parameters.
Requires: nav2_bringup package and TurtleBot3 Nav2 setup.
"""

import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for Nav2 stack."""
    
    from ament_index_python.packages import get_package_share_directory
    
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    medguide_bringup_dir = get_package_share_directory('medguide_bringup')
    
    # Paths to config files
    nav2_params_file = os.path.join(
        medguide_bringup_dir,
        '..',
        '..',
        'config',
        'nav2_params_hospital.yaml'
    )
    
    map_file = os.path.join(
        medguide_bringup_dir,
        '..',
        '..',
        'maps',
        'hospital_map.yaml'  # TODO: Create map file
    )
    
    # Declare launch arguments
    launch_args = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),
        DeclareLaunchArgument(
            'map',
            default_value=map_file,
            description='Path to hospital map YAML file'
        ),
    ]
    
    # Nav2 bringup (standard launch from nav2_bringup)
    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file': nav2_params_file,
            'map': LaunchConfiguration('map'),
        }.items(),
    )
    
    return LaunchDescription(launch_args + [nav2_bringup_launch])
