#!/usr/bin/env python3
"""
Unified MedGuide system launcher.

Orchestrates startup of entire MedGuide system in the correct dependency order:
  1. Gazebo simulation environment
  2. Nav2 stack
  3. Perception layer (obstacle detection)
  4. Navigation layer (goal sender)
  5. Task layer (mission scheduler)
  6. Legacy robot status/sensor nodes

This is the single entry point for starting the complete hospital assistant robot.

Usage:
    ros2 launch medguide_bringup unified.launch.py
    
Optional parameters:
    use_sim_time:=true/false         - Use simulated time (default: true)
    launch_gazebo:=true/false        - Launch Gazebo simulation (default: true)
    launch_nav2:=true/false          - Launch Nav2 stack (default: true)
    log_level:=INFO/DEBUG/WARN       - Log level for all nodes (default: INFO)
"""

import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node


def generate_launch_description():
    """Generate unified MedGuide launch description."""
    
    from ament_index_python.packages import get_package_share_directory
    
    medguide_bringup_dir = get_package_share_directory('medguide_bringup')
    
    # Declare launch arguments
    launch_args = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulated time (required for Gazebo)'
        ),
        DeclareLaunchArgument(
            'launch_gazebo',
            default_value='true',
            description='Launch Gazebo simulation environment'
        ),
        DeclareLaunchArgument(
            'launch_nav2',
            default_value='true',
            description='Launch Nav2 navigation stack'
        ),
        DeclareLaunchArgument(
            'launch_rviz',
            default_value='true',
            description='Launch RViz visualization'
        ),
        DeclareLaunchArgument(
            'log_level',
            default_value='INFO',
            choices=['DEBUG', 'INFO', 'WARN', 'ERROR'],
            description='Log level for all nodes'
        ),
    ]
    
    # Get launch configuration
    use_sim_time = LaunchConfiguration('use_sim_time')
    launch_gazebo = LaunchConfiguration('launch_gazebo')
    launch_nav2 = LaunchConfiguration('launch_nav2')
    launch_rviz = LaunchConfiguration('launch_rviz')
    log_level = LaunchConfiguration('log_level')
    
    # Startup logging
    startup_logging = [
        LogInfo(msg='=== MedGuide Hospital Assistant Robot System ==='),
        LogInfo(msg='Simulation time: $(var use_sim_time)'),
        LogInfo(msg='Gazebo enabled: $(var launch_gazebo)'),
        LogInfo(msg='Nav2 enabled: $(var launch_nav2)'),
        LogInfo(msg='Log level: $(var log_level)'),
        LogInfo(msg='================================================'),
    ]
    
    # 1. Gazebo simulation (optional)
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(medguide_bringup_dir, 'launch', 'gazebo_bringup.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'gazebo_gui': 'true',
        }.items(),
        condition=IfCondition(launch_gazebo),
    )
    
    # 2. Nav2 stack (optional)
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(medguide_bringup_dir, 'launch', 'nav2_bringup.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
        condition=IfCondition(launch_nav2),
    )
    
    # 3. Perception layer
    perception_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(medguide_bringup_dir, 'launch', 'medguide_perception.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'log_level': log_level,
        }.items(),
    )
    
    # 4. Navigation layer
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(medguide_bringup_dir, 'launch', 'medguide_navigation.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'log_level': log_level,
        }.items(),
    )
    
    # 5. Task layer (mission scheduler)
    tasks_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(medguide_bringup_dir, 'launch', 'medguide_tasks.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'log_level': log_level,
        }.items(),
    )
    
    # 6. Legacy robot status nodes (existing medguide_robot package)
    robot_status_node = Node(
        package='medguide_robot',
        executable='robot_status',
        name='robot_status',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=['--ros-args', '--log-level', log_level],
        output='screen',
    )
    
    # 7. RViz2 (optional) - visualization
    # TODO: Create/load medguide_simulation.rviz config
    # rviz_config = os.path.join(medguide_bringup_dir, '..', '..', 'rviz', 'medguide_simulation.rviz')
    # rviz_node = Node(
    #     package='rviz2',
    #     executable='rviz2',
    #     name='rviz2',
    #     arguments=['-d', rviz_config],
    #     condition=IfCondition(launch_rviz),
    #     output='screen',
    # )
    
    return LaunchDescription(
        startup_logging +
        launch_args +
        [
            gazebo_launch,
            nav2_launch,
            perception_launch,
            navigation_launch,
            tasks_launch,
            robot_status_node,
            # rviz_node,
        ]
    )
