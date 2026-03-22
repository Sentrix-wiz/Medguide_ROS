from setuptools import find_packages, setup

package_name = 'medguide_navigation'

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
    description='Navigation goal sender and Nav2 wrapper',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'navigation_goal_sender = medguide_navigation.navigation_goal_sender_node:main',
        ],
    },
)
