# Setup Guide

## Prerequisites

### 1. ROS Noetic (Ubuntu 20.04)

```bash
# Install ROS Noetic: http://wiki.ros.org/noetic/Installation/Ubuntu
sudo apt install ros-noetic-desktop-full
```

### 2. Gazebo 11

Included with `ros-noetic-desktop-full`. Verify:
```bash
gazebo --version  # should be 11.x
```

### 3. TurtleBot3 Packages

```bash
sudo apt install ros-noetic-turtlebot3-gazebo ros-noetic-turtlebot3-description
```

### 4. Create a catkin workspace (if not already)

```bash
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws
catkin_make
echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
```

### 5. Python Dependencies

```bash
pip install numpy opencv-python pyyaml ultralytics
```

## Installation

```bash
# Clone the repository
git clone https://github.com/player0729/gazebo-yolo-collector.git
cd gazebo-yolo-collector

# Run setup (installs pip deps, configures environment)
bash setup.sh

# Reload shell
source ~/.bashrc
```

## Verify

```bash
# Test with 3 diagnostic poses
bash scripts/run_collect.sh --texture crowd_01 --test 3

# Check output
ls dataset/images/train/
ls dataset/labels/train/
```

## Troubleshooting

**Gazebo black screen / camera no image:**
```bash
killall -9 gzserver gzclient
export TURTLEBOT3_MODEL=burger
```

**ImportError: No module named rospy:**
```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
```

**Material/texture not found:**
Ensure `GAZEBO_RESOURCE_PATH` includes the repo root:
```bash
export GAZEBO_RESOURCE_PATH=/path/to/gazebo-yolo-collector:$GAZEBO_RESOURCE_PATH
```
