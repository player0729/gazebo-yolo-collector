#!/usr/bin/env python3
"""
Gazebo-based YOLO Dataset Collector.
Teleports robot to various poses, captures camera images,
and generates YOLO labels via pinhole projection.
"""
import os, sys, time, math, random, subprocess, signal, glob, shutil, yaml, json
import numpy as np

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(REPO_ROOT, "dataset")
WORLDS_DIR = os.path.join(REPO_ROOT, "worlds")
CONFIG_FILE = os.path.join(REPO_ROOT, "config", "texture_config.yaml")
BBOX_FILE = os.path.join(REPO_ROOT, "config", "texture_bboxes.json")
META_FILE = os.path.join(DATASET_DIR, "collect_meta.json")
LAUNCH_FILE = os.path.join(REPO_ROOT, "launch", "collect.launch")

# Camera intrinsics (from URDF: HFOV=1.047, 640x480)
IMG_W, IMG_H = 640, 480
HFOV = 1.047
FX = FY = (IMG_W / 2.0) / math.tan(HFOV / 2.0)
CX, CY = IMG_W / 2.0, IMG_H / 2.0

# Camera offset from robot base (from URDF: xyz="-0.032 0 0.105" rpy="0 0 1.5708")
CAM_X, CAM_Y, CAM_Z = -0.032, 0.0, 0.105


def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def generate_poses(board_x=0.5, board_y=0.5, n=110, existing_angles=None):
    """Generate robot poses with weighted angle distribution.

    Angle bands (per texture, symmetric ±):
      ±0-30°  (0-0.524 rad): ~40 images, uniform
      ±30-50° (0.524-0.873 rad): ~40 images, dense
      ±50-65° (0.873-1.134 rad): ~20 images, edge
      ±65-75° (1.134-1.309 rad): ~5-10 images, extreme
    Total per texture: ~105-110
    """
    DISTANCES = [0.4, 0.5, 0.6, 0.7]

    # Angle bands: (abs_min, abs_max, target_per_side)
    BANDS = [
        (0.000, 0.524, 40),   # ±0-30°
        (0.524, 0.873, 40),   # ±30-50° (dense)
        (0.873, 1.134, 20),   # ±50-65° (edge)
        (1.134, 1.309, 7),    # ±65-75° (extreme)
    ]

    # bin_size for dedup: ~0.5° per bin for fine granularity
    BIN_SIZE = 0.009  # ~0.5°

    existing = existing_angles or set()

    def angle_to_bin(a):
        return int((a + 1.5) / BIN_SIZE)  # offset to make positive

    def dist_to_bin(d):
        for i, r in enumerate(DISTANCES):
            if abs(d - r) < 0.08:
                return i
        return len(DISTANCES) - 1

    candidates = []
    for amin, amax, target in BANDS:
        per_side = target
        # Generate ± pairs for each band
        for sign in [1, -1]:
            band_count = 0
            for _ in range(per_side * 2):  # overshoot, then trim
                if band_count >= per_side:
                    break
                angle = random.uniform(amin, amax) * sign
                dist = random.choice(DISTANCES)
                ab = angle_to_bin(angle)
                db = dist_to_bin(dist)
                if (ab, db) not in existing:
                    candidates.append((dist, angle, ab, db))
                    band_count += 1

    random.shuffle(candidates)

    poses = []
    used_bins = set()
    for dist, angle, ab, db in candidates:
        if len(poses) >= n:
            break
        if (ab, db) in used_bins:
            continue
        used_bins.add((ab, db))
        # Small random perturbation within bin
        angle_jitter = random.uniform(-BIN_SIZE / 2, BIN_SIZE / 2)
        angle = max(-1.309, min(1.309, angle + angle_jitter))
        x = dist * math.sin(angle) + random.uniform(-0.02, 0.02)
        y = board_y - dist * math.cos(angle) + random.uniform(-0.02, 0.02)
        yaw = math.atan2(board_y - y, -x) - math.pi / 2 + random.uniform(-0.03, 0.03)
        poses.append((x, y, 0.0, yaw, angle, dist))

    print(f"  生成 {len(poses)} 个新位姿 (跳过 {len(existing)} 个已有组合)")
    return poses


def generate_close_up_poses(board_x=0.5, board_y=0.5, n=80, existing_angles=None):
    """Close-up frontal poses for hard textures (low conf at near range).

    Distance: 0.40 - 0.55 (closer, denser than default 0.4-0.7)
    Angle:    ±20° (frontal-ish, where YOLO struggles for some textures)
    """
    DISTANCES = [0.40, 0.45, 0.50, 0.55]
    BANDS = [
        (0.000, 0.175, 30),  # ±0-10° (head-on)
        (0.175, 0.349, 30),  # ±10-20°
    ]
    BIN_SIZE = 0.009

    existing = existing_angles or set()
    angle_to_bin = lambda a: int((a + 1.5) / BIN_SIZE)
    def dist_to_bin(d):
        for i, r in enumerate(DISTANCES):
            if abs(d - r) < 0.04:
                return i
        return len(DISTANCES) - 1

    candidates = []
    for amin, amax, target in BANDS:
        for sign in [1, -1]:
            band_count = 0
            for _ in range(target * 2):
                if band_count >= target:
                    break
                angle = random.uniform(amin, amax) * sign
                dist = random.choice(DISTANCES)
                ab = angle_to_bin(angle)
                db = dist_to_bin(dist)
                if (ab, db) not in existing:
                    candidates.append((dist, angle, ab, db))
                    band_count += 1

    random.shuffle(candidates)
    poses = []
    used_bins = set()
    for dist, angle, ab, db in candidates:
        if len(poses) >= n:
            break
        if (ab, db) in used_bins:
            continue
        used_bins.add((ab, db))
        ajit = random.uniform(-BIN_SIZE / 2, BIN_SIZE / 2)
        angle = max(-0.349, min(0.349, angle + ajit))
        x = dist * math.sin(angle) + random.uniform(-0.015, 0.015)
        y = board_y - dist * math.cos(angle) + random.uniform(-0.015, 0.015)
        yaw = math.atan2(board_y - y, -x) - math.pi / 2 + random.uniform(-0.02, 0.02)
        poses.append((x, y, 0.0, yaw, angle, dist))

    print(f"  [close-up] 生成 {len(poses)} 近距离位姿 (跳过 {len(existing)})")
    return poses


def load_meta():
    """加载采集元数据。"""
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            return json.load(f)
    return {}


def save_meta(meta):
    """保存采集元数据。"""
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def project_board(robot_x, robot_y, robot_yaw, board_x, board_thick, board_wide, board_h):
    """Pinhole projection of board corners -> (yolo_label, pixel_coords) or None.
    Board at (0, board_y, 0) rotated yaw=-pi/2 (face toward +X).
    Camera faces LEFT of robot = (-sin(yaw), cos(yaw), 0)."""
    # Camera position from URDF: xyz="-0.032 0 0.105"
    cam_x = robot_x + CAM_X * math.cos(robot_yaw) - CAM_Y * math.sin(robot_yaw)
    cam_y = robot_y + CAM_X * math.sin(robot_yaw) + CAM_Y * math.cos(robot_yaw)
    cam_z = CAM_Z

    # Board corners (board at board_x=0, board_y=0.5, rotated pi/2)
    # Board local X→world -Y, local Y→world +X
    # Thin face (board_thick) along world Y, wide face (board_wide) along world X
    board_y = 0.5  # board Y position
    corners = [
        (-board_wide / 2, board_y - board_thick / 2, 0),
        ( board_wide / 2, board_y - board_thick / 2, 0),
        (-board_wide / 2, board_y - board_thick / 2, board_h),
        ( board_wide / 2, board_y - board_thick / 2, board_h),
    ]

    # Camera frame: forward = LEFT of robot = (-sin(yaw), cos(yaw), 0)
    fw_x = -math.sin(robot_yaw)
    fw_y = math.cos(robot_yaw)

    um, uM = float("inf"), float("-inf")
    vm, vM = float("inf"), float("-inf")

    for wx, wy, wz in corners:
        dx, dy, dz = wx - cam_x, wy - cam_y, wz - cam_z
        # Camera frame coordinates
        Xc = dx * fw_x + dy * fw_y   # forward (into wall)
        Yc = -dx * fw_y + dy * fw_x  # right
        Zc = dz                      # up
        if Xc <= 0.01:
            return None
        u = -FX * Yc / Xc + CX
        v = -FY * Zc / Xc + CY
        um, uM = min(um, u), max(uM, u)
        vm, vM = min(vm, v), max(vM, v)

    if uM < 0 or um >= IMG_W or vM < 0 or vm >= IMG_H:
        return None
    um, uM = max(0, um), min(IMG_W, uM)
    vm, vM = max(0, vm), min(IMG_H, vM)
    yolo = ((um + uM) / (2 * IMG_W), (vm + vM) / (2 * IMG_H),
            (uM - um) / IMG_W, (vM - vm) / IMG_H)
    return yolo, (um, uM, vm, vM)


def project_board_debug(robot_x, robot_y, robot_yaw, board_x, board_thick, board_wide, board_h):
    """Same as project_board but returns (result, debug_info) instead of just result."""
    cam_x = robot_x + CAM_X * math.cos(robot_yaw) - CAM_Y * math.sin(robot_yaw)
    cam_y = robot_y + CAM_X * math.sin(robot_yaw) + CAM_Y * math.cos(robot_yaw)
    cam_z = CAM_Z

    board_y = 0.5
    corners = [
        (-board_wide / 2, board_y - board_thick / 2, 0),
        ( board_wide / 2, board_y - board_thick / 2, 0),
        (-board_wide / 2, board_y - board_thick / 2, board_h),
        ( board_wide / 2, board_y - board_thick / 2, board_h),
    ]

    fw_x = -math.sin(robot_yaw)
    fw_y = math.cos(robot_yaw)

    um, uM = float("inf"), float("-inf")
    vm, vM = float("inf"), float("-inf")
    corner_info = []

    for wx, wy, wz in corners:
        dx, dy, dz = wx - cam_x, wy - cam_y, wz - cam_z
        Xc = dx * fw_x + dy * fw_y
        Yc = -dx * fw_y + dy * fw_x
        Zc = dz
        corner_info.append({
            "world": (wx, wy, wz), "cam": (Xc, Yc, Zc),
            "depth": Xc,
        })
        if Xc <= 0.01:
            debug = {"reason": "depth_behind", "cam_pos": (cam_x, cam_y, cam_z),
                     "robot_yaw": robot_yaw, "corners": corner_info}
            return None, debug
        u = -FX * Yc / Xc + CX
        v = -FY * Zc / Xc + CY
        um, uM = min(um, u), max(uM, u)
        vm, vM = min(vm, v), max(vM, v)

    if uM < 0 or um >= IMG_W or vM < 0 or vm >= IMG_H:
        debug = {"reason": "out_of_bounds", "cam_pos": (cam_x, cam_y, cam_z),
                 "robot_yaw": robot_yaw, "u_range": (um, uM), "v_range": (vm, vM),
                 "corners": corner_info}
        return None, debug

    um, uM = max(0, um), min(IMG_W, uM)
    vm, vM = max(0, vm), min(IMG_H, vM)
    yolo = ((um + uM) / (2 * IMG_W), (vm + vM) / (2 * IMG_H),
            (uM - um) / IMG_W, (vM - vm) / IMG_H)
    return yolo, (um, uM, vm, vM), {"reason": "ok", "u_range": (um, uM), "v_range": (vm, vM)}


def set_robot_pose(x, y, z, yaw):
    """Teleport robot via Gazebo service."""
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    # Use rospy directly for reliable service call
    try:
        import rospy
        from gazebo_msgs.srv import SetModelState
        from gazebo_msgs.msg import ModelState, ModelState
        if not hasattr(set_robot_pose, '_srv'):
            rospy.wait_for_service('/gazebo/set_model_state', timeout=5)
            set_robot_pose._srv = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
        state = ModelState()
        state.model_name = 'turtlebot3_burger'
        state.pose.position.x = x
        state.pose.position.y = y
        state.pose.position.z = z
        state.pose.orientation.z = qz
        state.pose.orientation.w = qw
        state.reference_frame = 'world'
        set_robot_pose._srv(state)
    except Exception as e:
        print(f"  WARN: set_model_state failed: {e}")


def kill_gazebo():
    subprocess.run(["killall", "-9", "gzserver", "gzclient"], capture_output=True)
    subprocess.run(["killall", "-9", "roslaunch"], capture_output=True)
    subprocess.run(["killall", "-9", "robot_state_publisher"], capture_output=True)
    time.sleep(2)


class ImageCapture:
    def __init__(self):
        self.img = None
        self.sub = None
        self.bridge = None

    def start(self):
        import rospy
        from sensor_msgs.msg import Image
        from cv_bridge import CvBridge
        self.bridge = CvBridge()
        rospy.init_node("gazebo_collector", anonymous=True)
        self.sub = rospy.Subscriber("/image_raw", Image, self._cb)
        t0 = time.time()
        while self.img is None and time.time() - t0 < 30:
            rospy.sleep(0.1)
        return self.img is not None

    def _cb(self, msg):
        try:
            self.img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception:
            pass

    def get(self):
        return self.img.copy() if self.img is not None else None

    def stop(self):
        if self.sub:
            self.sub.unregister()


def object_label_from_board(board_pixels, manual_yolo):
    """Convert board pixel coords + manual annotation to object YOLO label.
    manual_yolo = (x_center, y_center, width, height) as relative position
                  within the board (0=left/top, 1=right/bottom).
    board_pixels = (um, uM, vm, vM) in Gazebo image coords."""
    um, uM, vm, vM = board_pixels
    board_pw = uM - um
    board_ph = vM - vm

    mc_x, mc_y, mc_w, mc_h = manual_yolo
    # Map manual relative coords directly to board pixel region
    obj_u = um + mc_x * board_pw
    obj_v = vm + mc_y * board_ph
    obj_w = mc_w * board_pw
    obj_h = mc_h * board_ph

    return (obj_u / IMG_W, obj_v / IMG_H, obj_w / IMG_W, obj_h / IMG_H)


def collect_one_texture(texture_info, capture, start_idx, board_x=0.5, board_y=0.5, manual_yolo=None, test_n=None, pose_gen=None):
    """Collect images for one texture. Returns number of saved images.

    pose_gen: None (default ±75° wide) or 'close_up' (near + frontal).
    """
    import cv2

    name = texture_info["name"]
    material = texture_info["material"]
    class_id = texture_info["class_id"]
    board_w = texture_info.get("board_w", 0.001)

    # Generate world file
    from gen_world import gen_world
    world_file = gen_world(name, material, board_w)

    # Start Gazebo
    print(f"  Starting Gazebo for {name}...")
    launch_proc = subprocess.Popen(
        ["roslaunch", LAUNCH_FILE,
         f"world_file:={world_file}", "gui:=false"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(10)

    # Wait for camera
    if not capture.start():
        print(f"  ERROR: No camera images for {name}")
        launch_proc.terminate()
        kill_gazebo()
        return 0

    # Verify set_model_state service
    try:
        import rospy
        from gazebo_msgs.srv import SetModelState
        rospy.wait_for_service('/gazebo/set_model_state', timeout=10)
        print(f"  /gazebo/set_model_state service available")
    except Exception as e:
        print(f"  ERROR: set_model_state not available: {e}")
        capture.stop()
        launch_proc.terminate()
        kill_gazebo()
        return 0

    # Debug: save initial view (at spawn position)
    import cv2
    time.sleep(1.0)
    init_img = capture.get()
    if init_img is not None:
        debug_path = os.path.join(DATASET_DIR, f"debug_spawn_{name}.jpg")
        os.makedirs(os.path.dirname(debug_path), exist_ok=True)
        cv2.imwrite(debug_path, init_img)
        print(f"  Debug: spawn view saved to {debug_path}")

    # Collect images
    existing = meta.get(name, {}).get("collected_bins", [])
    existing_set = set(tuple(b) for b in existing) if existing else None
    if pose_gen == "close_up":
        poses = generate_close_up_poses(board_x, board_y, n=test_n or 80, existing_angles=existing_set)
    else:
        poses = generate_poses(board_x, board_y, n=test_n or 320, existing_angles=existing_set)
    img_dir = os.path.join(DATASET_DIR, "images", "train")
    lbl_dir = os.path.join(DATASET_DIR, "labels", "train")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(lbl_dir, exist_ok=True)

    saved = 0
    skipped_img = 0
    skipped_proj = 0
    collected_bins = list(existing) if existing else []
    for i, pose in enumerate(poses):
        x, y, z, yaw = pose[0], pose[1], pose[2], pose[3]
        angle_val = pose[4] if len(pose) > 4 else 0
        dist_val = pose[5] if len(pose) > 5 else 0
        set_robot_pose(x, y, z, yaw)
        time.sleep(1.5)  # wait for Gazebo to update render

        img = capture.get()
        if img is None:
            skipped_img += 1
            print(f"  SKIP[{i}] img=None  robot=({x:.3f},{y:.3f},yaw={math.degrees(yaw):.1f}°)")
            continue

        result = project_board_debug(x, y, yaw, board_x, 0.001, 0.165, 0.22)
        if result is None or (isinstance(result, tuple) and result[0] is None):
            skipped_proj += 1
            debug = result[1] if isinstance(result, tuple) else {}
            reason = debug.get("reason", "unknown")
            cam_pos = debug.get("cam_pos", (0,0,0))
            robot_yaw_deg = math.degrees(debug.get("robot_yaw", yaw))
            print(f"  SKIP[{i}] proj={reason}  robot=({x:.3f},{y:.3f},yaw={robot_yaw_deg:.1f}°) "
                  f"cam=({cam_pos[0]:.3f},{cam_pos[1]:.3f},{cam_pos[2]:.3f})")
            if "u_range" in debug:
                print(f"         u=[{debug['u_range'][0]:.1f},{debug['u_range'][1]:.1f}] "
                      f"v=[{debug['v_range'][0]:.1f},{debug['v_range'][1]:.1f}]")
            for ci, c in enumerate(debug.get("corners", [])):
                print(f"         corner{ci}: depth={c['depth']:.4f}  cam={c['cam']}")
            continue

        board_yolo, board_pixels = result[0], result[1]

        # Use manual annotation for precise object bbox
        if manual_yolo:
            label = object_label_from_board(board_pixels, manual_yolo)
        else:
            label = board_yolo

        # Log first image's details for debugging
        if saved == 0:
            print(f"  DEBUG: robot=({x:.3f},{y:.3f},yaw={yaw:.3f})")
            print(f"  DEBUG: board_px={[round(v,1) for v in board_pixels]}")
            print(f"  DEBUG: label={[round(v,4) for v in label]}")

        idx = start_idx + saved
        img_name = f"{name}_{idx:04d}.jpg"
        lbl_name = f"{name}_{idx:04d}.txt"

        cv2.imwrite(os.path.join(img_dir, img_name), img)
        with open(os.path.join(lbl_dir, lbl_name), "w") as f:
            f.write(f"{class_id} {label[0]:.6f} {label[1]:.6f} {label[2]:.6f} {label[3]:.6f}\n")

        saved += 1

        # 记录已采集的角度/距离组合 (BIN_SIZE=0.009, range ±1.309)
        BIN_SIZE = 0.009
        ab = int((angle_val + 1.5) / BIN_SIZE)
        DISTANCES = [0.4, 0.5, 0.6, 0.7]
        db = len(DISTANCES) - 1
        for di, r in enumerate(DISTANCES):
            if abs(dist_val - r) < 0.08:
                db = di
                break
        collected_bins.append([ab, db])

        if saved % 10 == 0:
            print(f"    {saved}/{len(poses)} saved")

    print(f"  统计: saved={saved}, skipped_img={skipped_img}, skipped_proj={skipped_proj}, total_poses={len(poses)}")

    # 保存该纹理的元数据
    if name not in meta:
        meta[name] = {}
    meta[name]["collected_bins"] = collected_bins
    meta[name]["total_images"] = len(collected_bins)
    save_meta(meta)

    capture.stop()
    launch_proc.terminate()
    kill_gazebo()
    return saved


def split_train_val(val_ratio=0.2):
    """Move val_ratio of train images to val set."""
    img_train = os.path.join(DATASET_DIR, "images", "train")
    lbl_train = os.path.join(DATASET_DIR, "labels", "train")
    img_val = os.path.join(DATASET_DIR, "images", "val")
    lbl_val = os.path.join(DATASET_DIR, "labels", "val")
    os.makedirs(img_val, exist_ok=True)
    os.makedirs(lbl_val, exist_ok=True)

    all_imgs = sorted(glob.glob(os.path.join(img_train, "*.jpg")))
    random.shuffle(all_imgs)
    n_val = int(len(all_imgs) * val_ratio)

    for path in all_imgs[:n_val]:
        fname = os.path.basename(path)
        lbl_name = fname.replace(".jpg", ".txt")
        shutil.move(path, os.path.join(img_val, fname))
        lbl_src = os.path.join(lbl_train, lbl_name)
        if os.path.exists(lbl_src):
            shutil.move(lbl_src, os.path.join(lbl_val, lbl_name))

    train_n = len(glob.glob(os.path.join(img_train, "*.jpg")))
    val_n = len(glob.glob(os.path.join(img_val, "*.jpg")))
    return train_n, val_n


def update_dataset_yaml(train_n, val_n, config):
    """Update dataset.yaml with new counts."""
    # Build class name map from config (class_id -> human readable name)
    class_names = []
    seen = set()
    for t in config["textures"]:
        cid = t["class_id"]
        if cid not in seen:
            seen.add(cid)
            # Derive name from material: "crowd/crowd_medical_1" -> "crowd_medical"
            mat = t["material"].split("/")[-1]
            # Remove trailing _N for numbered materials
            import re
            mat = re.sub(r'_\d+$', '', mat)
            class_names.append(mat)
        if len(class_names) <= cid:
            class_names.extend([""] * (cid + 1 - len(class_names)))
            class_names[cid] = mat

    data = {
        "path": DATASET_DIR,
        "train": "images/train",
        "val": "images/val",
        "nc": len(class_names),
        "names": class_names,
    }
    with open(os.path.join(DATASET_DIR, "dataset.yaml"), "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    print(f"dataset.yaml updated: {train_n} train, {val_n} val")


def main():
    close_up = "--close-up" in sys.argv
    append_mode = "--append" in sys.argv or close_up  # close-up 隐含 append

    if append_mode:
        seed = int(time.time()) % 10000
        random.seed(seed)
        np.random.seed(seed)
        print(f"增量模式种子: {seed}")
    else:
        random.seed(42)
        np.random.seed(42)

    # Parse --test N (only collect N poses for diagnostic)
    test_n = None
    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        if idx + 1 < len(sys.argv):
            test_n = int(sys.argv[idx + 1])
            print(f"测试模式: 只采集 {test_n} 个位姿")

    config = load_config()
    board_x = config["board_pos"][0]
    board_y = config["board_pos"][1]

    # Load manual bounding box annotations
    manual_bboxes = {}
    if os.path.exists(BBOX_FILE):
        with open(BBOX_FILE) as f:
            manual_bboxes = json.load(f)
        print(f"Loaded {len(manual_bboxes)} manual annotations from {BBOX_FILE}")
    else:
        print(f"WARNING: No manual annotations found at {BBOX_FILE}")

    # 目标纹理：--texture NAME 单个；--close-up 默认 crowd_05/06；否则全部
    target_names = None
    if "--texture" in sys.argv:
        idx = sys.argv.index("--texture")
        if idx + 1 < len(sys.argv):
            target_names = [sys.argv[idx + 1]]
    elif close_up:
        target_names = ["crowd_05", "crowd_06"]

    # Clean old dataset (unless append)
    if append_mode:
        existing = glob.glob(os.path.join(DATASET_DIR, "images", "train", "*.jpg"))
        start_count = len(existing)
        print(f"增量模式: 保留已有 {start_count} 张图片")
    else:
        for d in ["images/train", "images/val", "labels/train", "labels/val"]:
            p = os.path.join(DATASET_DIR, d)
            if os.path.exists(p):
                for f in os.listdir(p):
                    os.remove(os.path.join(p, f))
        start_count = 0

    os.environ["ROS_MASTER_URI"] = "http://localhost:11311"
    os.environ["TURTLEBOT3_MODEL"] = "burger"

    global meta
    meta = load_meta()
    if meta:
        print(f"已有采集元数据: {len(meta)} 个纹理")

    print("=" * 60)
    print("  Gazebo YOLO Dataset Collector")
    print("=" * 60)
    print(f"  Camera: pos=({CAM_X},{CAM_Y},{CAM_Z}) fw=(-sin(yaw),cos(yaw))  [faces LEFT]")
    print(f"  Intrinsics: FX=FY={FX:.1f} CX={CX} CY={CY} HFOV={math.degrees(HFOV):.1f}°")
    if close_up:
        print(f"  Close-up mode: dists=[0.40,0.45,0.50,0.55] angles±20° "
              f"target={target_names} n={test_n or 80}/tex")
    else:
        print(f"  Poses: {test_n or 320} per texture, angles±{math.degrees(0.698):.0f}°, dists=[0.4,0.5,0.6,0.7]")

    capture = ImageCapture()
    total = start_count
    textures = config["textures"]
    if target_names:
        textures = [t for t in textures if t["name"] in target_names]

    pose_gen = "close_up" if close_up else None

    for tex in textures:
        print(f"\n{'='*50}")
        print(f"  {tex['name']} (class {tex['class_id']})")
        print(f"{'='*50}")
        bbox_info = manual_bboxes.get(tex["name"])
        manual = bbox_info["yolo"] if bbox_info else None
        n = collect_one_texture(tex, capture, total, board_x, board_y, manual,
                                test_n=test_n, pose_gen=pose_gen)
        total += n
        print(f"  -> {n} images saved")

    if total > 0:
        print(f"\nSplitting train/val...")
        train_n, val_n = split_train_val()
        update_dataset_yaml(train_n, val_n, config)

    print(f"\n{'='*60}")
    print(f"  DONE: {total} total images")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        kill_gazebo()
        print("\nAborted.")
