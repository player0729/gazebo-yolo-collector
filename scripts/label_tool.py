#!/usr/bin/env python3
"""
Simple annotation tool: click 2 corners to define bounding box for each texture.
Saves results to a JSON file for later use.
Usage: python3 label_tool.py
"""
import cv2, os, json, sys, yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "textures")
OUTPUT = os.path.join(REPO_ROOT, "config", "texture_bboxes.json")
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "texture_config.yaml")

def load_textures_from_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        config = yaml.safe_load(f)

    tex_list = []
    for t in config.get("textures", []):
        # Infer texture image path from material name for the sample project structure
        # Or look for it in textures/ directory
        mat_base = t["material"].split("/")[-1]

        # Try to guess the image filename from the conventions
        if "crowd" in mat_base:
            img_file = "crowd_medical.jpg"
        elif "building" in mat_base:
            img_file = "building_collapse.jpg"
        elif "trash" in mat_base:
            img_file = "trash_can_food.jpg"
        else:
            img_file = f"{t['name']}.jpg"

        tex_list.append((img_file, t["name"], t["class_id"]))
    return tex_list

bboxes = {}
drawing = False
pt1 = None
pt2 = None
current_img = None
current_name = None

def mouse_cb(event, x, y, flags, param):
    global drawing, pt1, pt2, current_img
    if event == cv2.EVENT_LBUTTONDOWN:
        pt1 = (x, y)
        drawing = True
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        pt2 = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        pt2 = (x, y)
        drawing = False

def main():
    global current_img, current_name, pt1, pt2

    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            bboxes = json.load(f)
        print(f"Loaded {len(bboxes)} existing annotations")
    else:
        bboxes = {}

    cv2.namedWindow("annotate", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("annotate", mouse_cb)

    textures = load_textures_from_config()

    for fname, name, cls in textures:
        if name in bboxes:
            print(f"  {name}: already annotated, skip (press 's' to skip, 'q' to quit)")

        path = os.path.join(SRC, fname)
        if not os.path.exists(path):
            print(f"  SKIP: {path}")
            continue

        img = cv2.imread(path)
        if img is None:
            continue

        # Resize for display
        h, w = img.shape[:2]
        scale = min(800 / w, 600 / h)
        display = cv2.resize(img, (int(w * scale), int(h * scale)))

        current_img = display.copy()
        current_name = name
        pt1 = None
        pt2 = None

        print(f"\n[{name}] Click top-left then bottom-right of the texture. 's'=skip, 'q'=quit, 'r'=redo")

        while True:
            show = current_img.copy()
            if pt1 and pt2:
                cv2.rectangle(show, pt1, pt2, (0, 255, 0), 2)
                # Show YOLO coords
                x1, y1 = min(pt1[0], pt2[0]), min(pt1[1], pt2[1])
                x2, y2 = max(pt1[0], pt2[0]), max(pt1[1], pt2[1])
                dw, dh = display.shape[1], display.shape[0]
                xc = (x1 + x2) / (2 * dw)
                yc = (y1 + y2) / (2 * dh)
                bw = (x2 - x1) / dw
                bh = (y2 - y1) / dh
                cv2.putText(show, f"YOLO: {xc:.3f} {yc:.3f} {bw:.3f} {bh:.3f}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("annotate", show)
            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                cv2.destroyAllWindows()
                with open(OUTPUT, "w") as f:
                    json.dump(bboxes, f, indent=2)
                print(f"Saved {len(bboxes)} annotations to {OUTPUT}")
                return
            elif key == ord('s'):
                print(f"  {name}: skipped")
                break
            elif key == ord('r'):
                pt1 = None
                pt2 = None
                current_img = display.copy()
            elif key == 13 and pt1 and pt2:  # Enter
                x1, y1 = min(pt1[0], pt2[0]), min(pt1[1], pt2[1])
                x2, y2 = max(pt1[0], pt2[0]), max(pt1[1], pt2[1])
                dw, dh = display.shape[1], display.shape[0]
                # Scale back to original image coords
                ox1, oy1 = int(x1 / scale), int(y1 / scale)
                ox2, oy2 = int(x2 / scale), int(y2 / scale)
                ow, oh = img.shape[1], img.shape[0]
                bboxes[name] = {
                    "class": cls,
                    "x1": ox1, "y1": oy1, "x2": ox2, "y2": oy2,
                    "yolo": [(ox1+ox2)/(2*ow), (oy1+oy2)/(2*oh),
                             (ox2-ox1)/ow, (oy2-oy1)/oh]
                }
                print(f"  {name}: saved! bbox=({ox1},{oy1})-({ox2},{oy2})")
                break

    cv2.destroyAllWindows()
    with open(OUTPUT, "w") as f:
        json.dump(bboxes, f, indent=2)
    print(f"\nSaved {len(bboxes)} annotations to {OUTPUT}")


if __name__ == "__main__":
    main()
