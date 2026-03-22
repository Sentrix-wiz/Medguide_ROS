#!/usr/bin/env python3
"""
SLAM Mapping Launch.

Launches Gazebo + slam_toolbox + sensor_monitor + RViz for map building.
Drive the robot with turtlebot3_teleop while SLAM builds an occupancy grid map.

After mapping, save the map with:
    ros2 run nav2_map_server map_saver_cli -f ~/medguide_ws/maps/hospital_map

Requires:
    export TURTLEBOT3_MODEL=burger

Usage:
    ros2 launch medguide_robot slam_mapping.launch.py
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
    """Launch SLAM mapping with Gazebo simulation."""
    medguide_dir = get_package_share_directory('medguide_robot')
    config_file = os.path.join(medguide_dir, 'config', 'robot_params.yaml')
    slam_config = os.path.join(medguide_dir, 'config', 'slam_params.yaml')
    rviz_config = os.path.join(medguide_dir, 'rviz', 'slam_mapping.rviz')

    launch_rviz = LaunchConfiguration('launch_rviz', default='true')

    # 1. Gazebo simulation (TurtleBot3 in hospital world)
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(medguide_dir, 'launch', 'gazebo_sim.launch.py')
        ),
    )

    # 2. slam_toolbox — online async SLAM
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        parameters=[slam_config],
        output='screen',
    )

    # 3. Sensor monitor (from Phase 2)
    sensor_monitor = Node(
        package='medguide_robot',
        executable='sensor_monitor',
        name='sensor_monitor',
        parameters=[config_file, {'use_sim_time': True}],
        output='screen',
    )

    # 5. RViz2 with SLAM-specific config
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
        DeclareLaunchArgument('launch_rviz', default_value='true'),
        LogInfo(msg='=== MedGuide-ROS: SLAM Mapping ==='),
        LogInfo(msg='Drive with teleop to build the map:'),
        LogInfo(msg='  export TURTLEBOT3_MODEL=burger'),
        LogInfo(msg='  ros2 run turtlebot3_teleop teleop_keyboard'),
        LogInfo(msg=''),
        LogInfo(msg='When mapping is complete, save the map:'),
        LogInfo(msg='  ros2 run nav2_map_server map_saver_cli -f ~/medguide_ws/maps/hospital_map'),
        LogInfo(msg='=========================================='),
        gazebo_launch,
        slam_toolbox_node,
        sensor_monitor,
        rviz_node,
    ])
