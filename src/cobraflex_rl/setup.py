from setuptools import setup
from glob import glob
import os

package_name = "cobraflex_rl"


setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=[
        "setuptools",
        "numpy",
        "PyYAML",
        "gymnasium",
        "stable-baselines3",
    ],
    zip_safe=True,
    maintainer="admit",
    maintainer_email="admit@example.com",
    description="ROS2 PPO lane-following package for Gazebo.",
    license="Apache License 2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "train_ppo = cobraflex_rl.train_ppo:main",
            "eval_policy = cobraflex_rl.eval_policy:main",
            "gazebo_lane_env = cobraflex_rl.gazebo_lane_env:main",
        ],
    },
)
