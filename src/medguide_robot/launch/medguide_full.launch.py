#!/usr/bin/env python3
"""
Full Stack MedGuide Launch — All Phases.

Launches the complete autonomous hospital robot:
    Gazebo + Nav2 + Safety + Missions + Diagnostics + Logging + RViz

Usage:
    ros2 launch medguide_robot medguide_full.launch.py

Then start a delivery mission:
    ros2 service call /start_mission std_srvs/srv/Trigger '{}'
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
    """Launch the full MedGuide autonomous robot stack."""
    medguide_dir = get_package_share_directory('medguide_robot')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    nav2_params = os.path.join(medguide_dir, 'config', 'nav2_params.yaml')
    robot_params = os.path.join(medguide_dir, 'config', 'robot_params.yaml')
    rviz_config = os.path.join(medguide_dir, 'rviz', 'nav2_navigation.rviz')

    default_map = os.path.join(
        os.path.expanduser('~'), 'medguide_ws', 'maps', 'hospital_map.yaml'
    )

    map_file = LaunchConfiguration('map', default=default_map)
    launch_rviz = LaunchConfiguration('launch_rviz', default='true')

    # 1. Gazebo simulation
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(medguide_dir, 'launch', 'gazebo_sim.launch.py')
        ),
    )

    # 2. Nav2 bringup
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_file,
            'use_sim_time': 'true',
            'params_file': nav2_params,
        }.items(),
    )

    # 3. Obstacle detector (Phase 5)
    obstacle_detector = Node(
        package='medguide_robot',
        executable='obstacle_detector',
        name='obstacle_detector',
        parameters=[robot_params, {'use_sim_time': True}],
        output='screen',
    )

    # 4. Mission scheduler (Phase 6)
    mission_scheduler = Node(
        package='medguide_robot',
        executable='mission_scheduler',
        name='mission_scheduler',
        parameters=[robot_params, {'use_sim_time': True}],
        output='screen',
    )

    # 5. Sensor monitor
    sensor_monitor = Node(
        package='medguide_robot',
        executable='sensor_monitor',
        name='sensor_monitor',
        parameters=[robot_params, {'use_sim_time': True}],
        output='screen',
    )

    # 6. Diagnostics aggregator (Phase 7)
    diagnostics = Node(
        package='medguide_robot',
        executable='diagnostics',
        name='diagnostics_node',
        parameters=[robot_params, {'use_sim_time': True}],
        output='screen',
    )

    # 7. Mission logger (Phase 7)
    mission_logger = Node(
        package='medguide_robot',
        executable='mission_logger',
        name='mission_logger',
        parameters=[robot_params, {'use_sim_time': True}],
        output='screen',
    )

    # 8. RViz2
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
        DeclareLaunchArgument('map', default_value=default_map),
        DeclareLaunchArgument('launch_rviz', default_value='true'),
        LogInfo(msg='╔══════════════════════════════════════════╗'),
        LogInfo(msg='║  MedGuide-ROS — Autonomous Hospital Bot ║'),
        LogInfo(msg='║  Full Stack v1.0.0                       ║'),
        LogInfo(msg='╚══════════════════════════════════════════╝'),
        LogInfo(msg=''),
        LogInfo(msg='Start a delivery mission:'),
        LogInfo(msg='  ros2 service call /start_mission std_srvs/srv/Trigger "{}"'),
        LogInfo(msg=''),
        LogInfo(msg='Monitor:'),
        LogInfo(msg='  ros2 topic echo /system_health    # Full diagnostics'),
        LogInfo(msg='  ros2 topic echo /mission_status   # Mission progress'),
        LogInfo(msg='  Logs saved to: ~/medguide_ws/logs/'),
        LogInfo(msg=''),
        gazebo_launch,
        nav2_bringup,
        obstacle_detector,
        mission_scheduler,
        sensor_monitor,
        diagnostics,
        mission_logger,
        rviz_node,
    ])
