from setuptools import find_packages, setup

package_name = 'medguide_tasks'

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
    description='Task management and mission scheduling',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'mission_scheduler = medguide_tasks.mission_scheduler_node:main',
        ],
    },
)
