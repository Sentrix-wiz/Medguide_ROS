from setuptools import find_packages, setup

package_name = 'medguide_perception'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='MedGuide Team',
    maintainer_email='medguide@research.local',
    description='Perception layer for obstacle detection',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'obstacle_detector = medguide_perception.obstacle_detector_node:main',
        ],
    },
)
