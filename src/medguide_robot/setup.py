import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'medguide_robot'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
        (os.path.join('share', package_name, 'worlds'),
            glob('worlds/*.world')),
        (os.path.join('share', package_name, 'rviz'),
            glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='sentrix',
    maintainer_email='sentrix@research.local',
    description='MedGuide-ROS: Autonomous Hospital Assistant Robot',
    license='Apache-2.0',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'sensor_monitor  = medguide_robot.sensor_monitor_node:main',
            'obstacle_detector = medguide_robot.obstacle_detector_node:main',
            'mission_scheduler = medguide_robot.mission_scheduler_node:main',
            'diagnostics     = medguide_robot.diagnostics_node:main',
            'mission_logger  = medguide_robot.mission_logger_node:main',
            'orchestrator    = medguide_robot.experiment_orchestrator_node:main',
        ],
    },
)
