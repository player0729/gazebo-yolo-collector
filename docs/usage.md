# Usage Guide

## CLI Reference

```bash
python3 gazebo_collect.py [OPTIONS]
# or
bash scripts/run_collect.sh [OPTIONS]
```

### Options

| Flag | Description |
|------|-------------|
| `--texture NAME` | Collect only one texture (e.g., `crowd_01`) |
| `--test N` | Diagnostic mode: collect only N poses per texture |
| `--append` | Incremental mode: skip already-collected poses |
| `--close-up` | Near + frontal capture for hard textures (0.40-0.55m, +/-20°) |

### Examples

**Diagnostic test (5 poses, one texture):**
```bash
python3 gazebo_collect.py --texture crowd_01 --test 5
```

**Full collection (all 20 textures, ~110 poses each):**
```bash
python3 gazebo_collect.py
```

**Incremental collection (resume after interruption):**
```bash
python3 gazebo_collect.py --append
```

**Close-up pass for hard textures:**
```bash
python3 gazebo_collect.py --close-up
```

## Output Structure

```
dataset/
├── dataset.yaml              # YOLO dataset config
├── collect_meta.json         # Collection state (for --append)
├── images/
│   ├── train/                # Training images (80%)
│   └── val/                  # Validation images (20%)
└── labels/
    ├── train/                # YOLO-format labels (80%)
    └── val/                  # YOLO-format labels (20%)
```

## Label Format

Each `.txt` file contains one line per object:
```
<class_id> <x_center> <y_center> <width> <height>
```
All coordinates are normalized [0, 1].

## Visualizing Labels

```bash
# View 20 random labeled images
python3 scripts/vis_labels.py 20
# Output: dataset/vis_check/
```

## Customization

### Camera Intrinsics

Edit the constants at the top of `gazebo_collect.py`:
```python
IMG_W, IMG_H = 640, 480       # Image resolution
HFOV = 1.047                   # Horizontal field of view (radians)
CAM_X, CAM_Y, CAM_Z = -0.032, 0.0, 0.105  # Camera offset from robot base
```

### Pose Distribution

Edit `generate_poses()` in `gazebo_collect.py`:
- `DISTANCES`: distance rings in meters
- `BANDS`: angle bands with target image counts per side

### Adding New Textures

1. Add image to `textures/`
2. Create `.material` file in `materials/scripts/`
3. Add entry to `config/texture_config.yaml`
4. Optionally add bbox annotation to `config/texture_bboxes.json`

## Training

After collection:
```bash
yolo detect train data=dataset/dataset.yaml model=yolov8n.pt epochs=100 imgsz=640 batch=16 device=0
```

## Tips

- First run: use `--test 10` to verify everything works before full collection
- Use `--append` if Gazebo crashes mid-collection — it skips already-covered poses
- Use `--close-up` for textures that have low confidence at standard ranges
- The `--texture` flag is useful when adding new textures to an existing dataset
