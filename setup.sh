#!/bin/bash
# One-time setup for gazebo-yolo-collector
# Usage: bash setup.sh

set -e
PROJECT="$(cd "$(dirname "$0")" && pwd)"

echo "=== gazebo-yolo-collector setup ==="
echo ""

# Install Python dependencies
echo "[1/3] Installing Python dependencies..."
pip install -r "$PROJECT/requirements.txt"
echo "  Done."

# Set GAZEBO_RESOURCE_PATH in ~/.bashrc if not already set
if ! grep -q "GAZEBO_RESOURCE_PATH.*gazebo-yolo-collector" ~/.bashrc 2>/dev/null; then
    echo "[2/3] Adding GAZEBO_RESOURCE_PATH to ~/.bashrc..."
    echo "" >> ~/.bashrc
    echo "# gazebo-yolo-collector" >> ~/.bashrc
    echo "export GAZEBO_RESOURCE_PATH=\"$PROJECT:\$GAZEBO_RESOURCE_PATH\"" >> ~/.bashrc
    echo "  Done. Run 'source ~/.bashrc' to apply."
else
    echo "[2/3] GAZEBO_RESOURCE_PATH already configured."
fi

# Verify ROS environment
echo "[3/3] Checking ROS environment..."
if [ -f /opt/ros/noetic/setup.bash ]; then
    echo "  ROS Noetic found."
else
    echo "  WARNING: ROS Noetic not found at /opt/ros/noetic/setup.bash"
    echo "  Install ROS Noetic: http://wiki.ros.org/noetic/Installation"
fi

if [ -f ~/catkin_ws/devel/setup.bash ]; then
    echo "  catkin_ws found."
else
    echo "  NOTE: ~/catkin_ws not found. You need a catkin workspace with turtlebot3 packages."
    echo "  Setup guide: https://emanual.robotis.com/docs/en/platform/turtlebot3/simulation/"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Prepare your texture images in textures/"
echo "  2. Configure config/texture_config.yaml"
echo "  3. Run: bash scripts/run_collect.sh --texture crowd_01 --test 5"
echo "  4. Read docs/usage.md for full instructions"
