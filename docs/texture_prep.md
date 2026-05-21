# Texture Preparation Guide

## Overview

The collector renders texture images on flat boards in Gazebo and captures them from a robot-mounted camera. This guide explains how to prepare your own textures.

## Texture Image Requirements

- **Format:** JPG or PNG
- **Resolution:** Recommended 1024x1024 or higher. The textures should be clear at the simulated viewing distances (0.4-1.1m)
- **Content:** A distinct object or pattern you want to detect

## Step 1: Add Texture Image

Copy your image to the `textures/` directory:
```bash
cp my_texture.jpg textures/
```

## Step 2: Create OGRE Material File

Create a `.material` file in `materials/scripts/`:
```
material MyCategory/my_material
{
  technique
  {
    pass
    {
      texture_unit
      {
        texture textures/my_texture.jpg
        scale 1 1
      }
    }
  }
}
```

The material name format is `Category/Name`. Gazebo looks up materials by this name using `GAZEBO_RESOURCE_PATH`.

## Step 3: Add to Texture Config

Edit `config/texture_config.yaml`:
```yaml
textures:
  - class_id: 0
    material: MyCategory/my_material
    name: my_texture_01
```

| Field | Description |
|-------|-------------|
| `class_id` | YOLO class ID (0-9, or extend for more classes) |
| `material` | Material name matching the `.material` file |
| `name` | Short identifier used for output filenames |

## Step 4: Manual Bounding Box Annotation (Optional)

If your texture image contains the object but doesn't fill the entire board, add a manual annotation to `config/texture_bboxes.json`:

```json
{
  "my_texture_01": {
    "class": 0,
    "x1": 100, "y1": 200, "x2": 900, "y2": 800,
    "yolo": [0.5, 0.5, 0.8, 0.6]
  }
}
```

- `x1, y1, x2, y2`: pixel coordinates of the object in the source texture image
- `yolo`: [x_center, y_center, width, height] as relative positions within the board (0=left/top, 1=right/bottom)

Without manual annotations, the collector labels the entire board as the bounding box. With annotations, it computes a precise object-level box from the board-level projection.

## Board Geometry

The default board is 0.165m wide x 0.22m high x 0.001m thick, positioned at (0, 0.5, 0.11) in the Gazebo world, facing the robot. The pinhole projection uses these dimensions to compute bounding boxes. If your board has different dimensions, update `board_size` in `texture_config.yaml`.

## Class Name Mapping

The class names in `dataset.yaml` are derived from the material names in your config. Material `crowd/crowd_medical_1` becomes class name `crowd_medical`. For custom names, edit `update_dataset_yaml()` in `gazebo_collect.py`.
