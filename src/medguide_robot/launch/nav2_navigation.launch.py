#!/usr/bin/env python3
"""
Nav2 Navigation Launch.

Launches Gazebo + Nav2 stack + RViz for autonomous navigation on a saved map.
The robot uses AMCL for localization and Nav2 for path planning.

Requires a saved map from the SLAM mapping step.

Usage:
    ros2 launch medguide_robot nav2_navigation.launch.py
    ros2 launch medguide_robot nav2_navigation.launch.py map:=/path/to/map.yaml
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Launch Nav2 navigation with Gazebo simulation."""
    medguide_dir = get_package_share_directory('medguide_robot')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    nav2_params = os.path.join(medguide_dir, 'config', 'nav2_params.yaml')
    robot_params = os.path.join(medguide_dir, 'config', 'robot_params.yaml')
    rviz_config = os.path.join(medguide_dir, 'rviz', 'nav2_navigation.rviz')

    # Default map from Phase 3 SLAM
    default_map = os.path.join(
        os.path.expanduser('~'), 'medguide_ws', 'maps', 'hospital_map.yaml'
    )

    # Launch arguments
    map_file = LaunchConfiguration('map', default=default_map)
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    launch_rviz = LaunchConfiguration('launch_rviz', default='true')

    # 1. Gazebo simulation (TurtleBot3 in hospital world)
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(medguide_dir, 'launch', 'gazebo_sim.launch.py')
        ),
    )

    # 2. Nav2 bringup (AMCL + planners + controller + costmaps + lifecycle)
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_file,
            'use_sim_time': use_sim_time,
            'params_file': nav2_params,
        }.items(),
    )

    # 3. Sensor monitor (from Phase 2 — see robot position + lidar stats)
    sensor_monitor = Node(
        package='medguide_robot',
        executable='sensor_monitor',
        name='sensor_monitor',
        parameters=[robot_params, {'use_sim_time': True}],
        output='screen',
    )

    # 4. RViz2 with Nav2 config
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(launch_rviz),
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map,
                              description='Full path to map YAML'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('launch_rviz', default_value='true'),
        LogInfo(msg='=== MedGuide-ROS: Nav2 Navigation ==='),
        LogInfo(msg='Set a goal in RViz (2D Goal Pose), or call /start_mission service.'),
        LogInfo(msg='=========================================='),
        gazebo_launch,
        nav2_bringup,
        sensor_monitor,
        rviz_node,
    ])
