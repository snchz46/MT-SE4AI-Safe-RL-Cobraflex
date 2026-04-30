"""
Safety cage package.

Contains the runtime safety cage as a ROS2 node and its constituent rules.
See docs/04_cage_specification.md for the design specification.
"""

from .cage_node import SafetyCageNode

__all__ = ["SafetyCageNode"]
