#!/usr/bin/env python3
"""Visualize YOLO labels on dataset images for quality inspection."""
import os, sys, random, cv2

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(REPO_ROOT, "dataset", "images", "train")
LBL_DIR = os.path.join(REPO_ROOT, "dataset", "labels", "train")
OUT_DIR = os.path.join(REPO_ROOT, "dataset", "vis_check")

CLASS_NAMES = [
    "crowd_injured", "crowd_normal",
    "building_collapse", "building_fire", "building_gas", "building_electric",
    "trash_kitchen", "trash_recyclable", "trash_hazardous", "trash_other",
]
COLORS = [
    (0, 0, 255), (0, 128, 255), (255, 0, 0), (0, 255, 255),
    (255, 0, 255), (0, 255, 0), (128, 0, 128), (255, 255, 0),
    (128, 128, 0), (0, 128, 128),
]


def draw_label(img, label_line):
    parts = label_line.strip().split()
    if len(parts) < 5:
        return
    cls_id = int(parts[0])
    cx, cy, w, h = map(float, parts[1:5])
    h_img, w_img = img.shape[:2]
    x1 = int((cx - w / 2) * w_img)
    y1 = int((cy - h / 2) * h_img)
    x2 = int((cx + w / 2) * w_img)
    y2 = int((cy + h / 2) * h_img)
    color = COLORS[cls_id % len(COLORS)]
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    label = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"cls_{cls_id}"
    cv2.putText(img, label, (x1, max(y1 - 5, 15)), cv2.FONT_HERSHEY_SIMPLEX,
                0.4, color, 1)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    imgs = [f for f in os.listdir(IMG_DIR) if f.endswith(".jpg")]
    random.shuffle(imgs)
    os.makedirs(OUT_DIR, exist_ok=True)

    for fname in imgs[:n]:
        img_path = os.path.join(IMG_DIR, fname)
        lbl_path = os.path.join(LBL_DIR, fname.replace(".jpg", ".txt"))
        img = cv2.imread(img_path)
        if img is None:
            continue
        if os.path.exists(lbl_path):
            with open(lbl_path) as f:
                for line in f:
                    draw_label(img, line)
        cv2.imwrite(os.path.join(OUT_DIR, fname), img)
        print(f"  {fname}")

    print(f"\n{n} images saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
