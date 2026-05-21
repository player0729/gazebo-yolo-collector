# Pipeline Overview

## End-to-End Flow

```
Textures  →  World Gen  →  Gazebo  →  Image Capture  →  Label Projection  →  Dataset  →  YOLO Train
```

## Detailed Steps

### 1. World Generation (`gen_world.py`)
For each texture, a minimal SDF world file is generated containing:
- Ground plane
- A single texture board at (0, 0.5, 0.11), 0.165m x 0.22m, facing +X
- Directional lighting
- Physics (ODE, 1000Hz)

### 2. Gazebo Launch (`launch/collect.launch`)
Each world is launched headless (`gui:=false`):
- TurtleBot3 Burger spawns at origin with camera (640x480, 30Hz, HFOV=1.047 rad)
- Camera publishes to `/image_raw`
- Robot state publisher provides TF transforms

### 3. Pose Generation (`generate_poses()`)
~110 poses per texture with weighted angle distribution:

| Angle Band | Images | Purpose |
|------------|--------|---------|
| +/-0-30 degrees | ~40 | Frontal views |
| +/-30-50 degrees | ~40 | Oblique views (dense) |
| +/-50-65 degrees | ~20 | Edge views |
| +/-65-75 degrees | ~7 | Extreme angles |

Distances: [0.4, 0.5, 0.6, 0.7]m from board.
Deduplication via angle/distance binning (0.5-degree bins).

### 4. Robot Teleportation
`/gazebo/set_model_state` service instantly moves the robot to each pose.
1.5s settling time for Gazebo rendering after each teleport.

### 5. Label Computation (`project_board()`)
Pinhole camera projection of known 3D board corners:

1. Camera world position = robot pose + camera offset (from URDF)
2. 4 board corners projected through camera matrix
3. Result: (x_center, y_center, width, height) normalized to [0, 1]

Camera intrinsics:
- FX = FY = 554.4 (from HFOV = 1.047 rad)
- CX = 320, CY = 240

### 6. Manual Bbox Correction (`object_label_from_board()`)
If `texture_bboxes.json` has an entry for the texture, the full-board YOLO label is refined to a precise object-level label using the manual annotation's relative position within the board.

### 7. Train/Val Split (`split_train_val()`)
Random 80/20 split with balanced distribution across textures.

### 8. Dataset YAML (`update_dataset_yaml()`)
Generates `dataset/dataset.yaml` with:
- Image/label paths
- Number of classes
- Class names (derived from material names)

## Incremental Collection

The `--append` flag enables incremental collection:

1. `collect_meta.json` stores angle/distance bins already collected per texture
2. `generate_poses()` skips existing bins
3. New images are appended, train/val split is re-run

This allows resuming interrupted collections or adding more poses to an existing dataset.

## Close-Up Mode

For textures with low detection confidence at standard ranges:
- Distances: [0.40, 0.45, 0.50, 0.55]m (closer)
- Angles: +/-20 degrees (frontal)

Invoke with `--close-up`. Targets `crowd_05` and `crowd_06` by default.

## Training Recommendation

```bash
# After collection:
yolo detect train \
  data=dataset/dataset.yaml \
  model=yolov8n.pt \
  epochs=100 \
  imgsz=640 \
  batch=16 \
  device=0 \
  patience=20 \
  name=safe_city
```

The trained model is saved to `runs/detect/safe_city/weights/best.pt`.
