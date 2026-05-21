#!/usr/bin/env python3
"""Generate a minimal Gazebo world file with one texture board."""
import sys, os

BOARD_W_DEFAULT, BOARD_D, BOARD_H = 0.001, 0.165, 0.22
# Box: thickness(0.001) x width(0.165) x height(0.22)
# Board on LEFT side (0, 0.5), rotated 90° so face points toward robot (camera faces left)
BOARD_Z = BOARD_H / 2.0
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
WORLDS_DIR = os.path.join(REPO_ROOT, "worlds")

WORLD_TEMPLATE = '''<sdf version="1.7">
<world name="collect_{name}">
<gui fullscreen="0">
  <camera name="user_camera">
    <pose>0 -2 1.5 0 0.5 0</pose>
    <view_controller>orbit</view_controller>
    <projection_type>perspective</projection_type>
  </camera>
</gui>
<physics type="ode">
  <max_step_size>0.001</max_step_size>
  <real_time_factor>1</real_time_factor>
  <real_time_update_rate>1000</real_time_update_rate>
</physics>
<scene>
  <ambient>0.4 0.4 0.4 1</ambient>
  <background>0.7 0.7 0.7 1</background>
  <shadows>1</shadows>
</scene>
<light name="sun" type="directional">
  <cast_shadows>1</cast_shadows>
  <pose>0 0 10 0 0 0</pose>
  <diffuse>0.8 0.8 0.8 1</diffuse>
  <specular>0.2 0.2 0.2 1</specular>
  <attenuation><range>1000</range><constant>0.9</constant><linear>0.01</linear><quadratic>0.001</quadratic></attenuation>
  <direction>-0.5 0.1 -0.9</direction>
  <spot><inner_angle>0</inner_angle><outer_angle>0</outer_angle><falloff>0</falloff></spot>
</light>
<model name="ground_plane">
  <static>1</static>
  <link name="link">
    <collision name="collision">
      <geometry><plane><normal>0 0 1</normal><size>100 100</size></plane></geometry>
    </collision>
    <visual name="visual">
      <cast_shadows>0</cast_shadows>
      <geometry><plane><normal>0 0 1</normal><size>100 100</size></plane></geometry>
      <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/Grey</name></script></material>
    </visual>
  </link>
</model>
<model name="texture_board">
  <static>1</static>
  <pose>0 0.5 {board_z:.4f} 0 0 -1.5708</pose>
  <link name="link">
    <collision name="c">
      <geometry><box><size>{bw:.4f} {bd:.4f} {bh:.4f}</size></box></geometry>
      <max_contacts>10</max_contacts>
      <surface><contact><ode/></contact><bounce/></surface>
    </collision>
    <visual name="v">
      <geometry><box><size>{bw:.4f} {bd:.4f} {bh:.4f}</size></box></geometry>
      <material>
        <script>
          <name>{material}</name>
          <uri>__default__</uri>
        </script>
      </material>
    </visual>
  </link>
</model>
</world>
</sdf>'''


def gen_world(texture_name, material_name, board_w=BOARD_W_DEFAULT, output_dir=None):
    """Generate a world file for one texture. Returns the file path."""
    if output_dir is None:
        output_dir = WORLDS_DIR
    os.makedirs(output_dir, exist_ok=True)

    xml = WORLD_TEMPLATE.format(
        name=texture_name,
        material=material_name,
        board_z=BOARD_Z,
        bw=board_w, bd=BOARD_D, bh=BOARD_H,
    )
    path = os.path.join(output_dir, f"collect_{texture_name}.world")
    with open(path, "w") as f:
        f.write(xml)
    return path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: gen_world.py <texture_name> <material_name> [board_w]")
        sys.exit(1)
    bw = float(sys.argv[3]) if len(sys.argv) > 3 else BOARD_W_DEFAULT
    p = gen_world(sys.argv[1], sys.argv[2], bw)
    print(f"Generated: {p}")
