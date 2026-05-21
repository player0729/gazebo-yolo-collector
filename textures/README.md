# Sample Textures

This directory contains 3 sample texture images for demonstration:

| File | Category | Class IDs |
|------|----------|-----------|
| `crowd_medical.jpg` | Person (injured/normal) | 0, 1 |
| `building_collapse.jpg` | Building (collapse/fire/gas/electric) | 2, 3, 4, 5 |
| `trash_can_food.jpg` | Trash can (food/recyclable/hazardous/other) | 6, 7, 8, 9 |

## Using Your Own Textures

1. Place your texture images in this directory
2. Create corresponding `.material` files in `materials/scripts/`
3. Add entries to `config/texture_config.yaml`
4. Add bounding box annotations to `config/texture_bboxes.json` (optional, for precise object-level labels)

See `docs/texture_prep.md` for detailed instructions.

## Important

These sample images are placeholders. For a real dataset, replace them with your own texture images. The quality of the collected dataset depends entirely on the textures you provide — the collector only handles the camera positioning and label projection.
