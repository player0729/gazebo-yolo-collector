# gazebo-yolo-collector

[中文版](README_zh.md)

Auto-generate YOLO-format object detection datasets from Gazebo simulations — **zero manual labeling required**.

A TurtleBot3 with a camera is teleported to hundreds of poses in front of texture boards. Images are captured and ground-truth bounding boxes are computed via pinhole camera projection from known 3D board positions. The result is a perfectly labeled dataset ready for YOLO training.

## Features

- **Gazebo + ROS** — Uses standard robotics simulation tools, no proprietary engines
- **Automatic labels** — Pinhole projection computes YOLO-format bounding boxes from known board geometry
- **Multi-view collection** — Weighted angle/distance sampling covers frontal to extreme (75 degrees) viewpoints
- **Incremental collection** — Resume interrupted runs without duplicating poses
- **Manual bbox correction** — Optional per-texture annotations for precise object-level labels within boards
- **Train/val split** — Automatic 80/20 split with dataset.yaml generation

## Quickstart

```bash
# 1. Setup
bash setup.sh

# 2. Test with one texture (5 diagnostic poses)
bash scripts/run_collect.sh --texture crowd_01 --test 5

# 3. Full collection (all textures)
bash scripts/run_collect.sh

# 4. Train YOLO
yolo detect train data=dataset/dataset.yaml model=yolov8n.pt epochs=100 imgsz=640
```

## Requirements

- Ubuntu 20.04 + ROS Noetic
- Gazebo 11
- TurtleBot3 simulation packages (`turtlebot3_gazebo`, `turtlebot3_description`)
- Python 3.8+, PyTorch, ultralytics
- NVIDIA GPU recommended for training (CPU works for collection)

## How It Works

1. **World generation** — `gen_world.py` creates a minimal Gazebo world with one texture board on a wall
2. **Robot teleportation** — `gazebo_collect.py` launches Gazebo headless, spawns a TurtleBot3 with camera, and teleports it to ~110 poses per texture via `/gazebo/set_model_state`
3. **Image capture** — Camera images are captured at each pose (640x480, HFOV=1.047 rad)
4. **Label projection** — Known 3D board corner coordinates are projected to 2D pixel coordinates using the pinhole camera model, producing YOLO-format labels
5. **Dataset assembly** — Images and labels are saved to `dataset/`, split 80/20 train/val, and `dataset.yaml` is generated

## Project Structure

```
├── gazebo_collect.py        # Core collection pipeline
├── gen_world.py             # Per-texture world file generator
├── setup.sh                 # One-time environment setup
├── config/
│   ├── texture_config.yaml  # Texture definitions (class IDs, materials)
│   └── texture_bboxes.json  # Manual bounding box annotations
├── launch/
│   └── collect.launch       # ROS launch file for headless Gazebo
├── urdf/
│   └── turtlebot3_burger_cam.urdf.xacro
├── materials/scripts/       # OGRE material files (20 textures)
├── textures/                # Your texture images
├── scripts/
│   ├── run_collect.sh       # Convenience launcher
│   └── vis_labels.py        # Label visualization tool
└── docs/                    # Detailed documentation
```

## Documentation

- [Setup Guide](docs/setup.md) — Environment setup and prerequisites
- [Usage Guide](docs/usage.md) — CLI reference and workflows
- [Texture Preparation](docs/texture_prep.md) — Preparing your own textures
- [Pipeline Overview](docs/pipeline.md) — End-to-end collection to training

## License

MIT — see [LICENSE](LICENSE)

## Citation

If you use this tool in your research, please cite:

```bibtex
@software{gazebo_yolo_collector,
  author = {player0729},
  title = {gazebo-yolo-collector: Auto-generate YOLO datasets from Gazebo},
  year = {2026},
  url = {https://github.com/player0729/gazebo-yolo-collector}
}
```
