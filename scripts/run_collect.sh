#!/bin/bash
# Convenience launcher for gazebo_collect.py
# Usage: bash scripts/run_collect.sh [--texture NAME] [--append] [--close-up] [--test N]

set -e

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"

# Source ROS environment
source /opt/ros/noetic/setup.bash 2>/dev/null || true
source ~/catkin_ws/devel/setup.bash 2>/dev/null || true

export TURTLEBOT3_MODEL=burger
export GAZEBO_RESOURCE_PATH="$PROJECT:$GAZEBO_RESOURCE_PATH"

cd "$PROJECT"
python3 gazebo_collect.py "$@"
