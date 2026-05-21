# gazebo-yolo-collector

基于 Gazebo 仿真的 YOLO 目标检测数据集自动生成工具 — **无需人工标注**。

在 Gazebo 中，搭载摄像头的 TurtleBot3 被瞬移到纹理板前的上百个位姿，拍摄图像并通过针孔相机投影计算 YOLO 格式的 GT 标注框。最终输出一个可直接用于 YOLO 训练的标注数据集。

## 特性

- **Gazebo + ROS** — 基于标准机器人仿真工具，不依赖商业引擎
- **自动标注** — 利用已知 3D 板位置，通过针孔投影计算 YOLO 格式标注框
- **多视角采集** — 加权角度/距离采样，覆盖正面到极端角度（75°）
- **增量采集** — 支持断点续采，自动跳过已采集的位姿组合
- **精确标注修正** — 可选手动标注文件（texture_bboxes.json），将整板框修正为板内物体的精确框
- **自动划分** — 80/20 训练/验证集划分，自动生成 dataset.yaml

## 快速开始

```bash
# 1. 环境配置
bash setup.sh

# 2. 测试单个纹理（5 张诊断图）
bash scripts/run_collect.sh --texture crowd_01 --test 5

# 3. 全量采集（所有纹理）
bash scripts/run_collect.sh

# 4. 训练 YOLO
yolo detect train data=dataset/dataset.yaml model=yolov8n.pt epochs=100 imgsz=640
```

## 环境要求

- Ubuntu 20.04 + ROS Noetic
- Gazebo 11
- TurtleBot3 仿真包 (`turtlebot3_gazebo`, `turtlebot3_description`)
- Python 3.8+, PyTorch, ultralytics
- 训练推荐 NVIDIA GPU（仅采集时 CPU 即可）

## 工作原理

1. **生成世界文件** — `gen_world.py` 为每个纹理生成一个最小化的 Gazebo 世界（一面墙 + 一块纹理板）
2. **瞬移机器人** — `gazebo_collect.py` 无头启动 Gazebo，放置 TurtleBot3，通过 `/gazebo/set_model_state` 服务瞬移到 ~110 个位姿
3. **采集图像** — 每个位姿捕获摄像头图像（640×480，HFOV=1.047 rad）
4. **投影标注** — 已知 3D 板角点坐标，通过针孔相机模型投影到 2D 像素坐标，生成 YOLO 格式标注
5. **组装数据集** — 图像和标注存入 `dataset/`，按 80/20 划分，生成 `dataset.yaml`

## 项目结构

```
├── gazebo_collect.py        # 核心采集 pipeline
├── gen_world.py             # 逐纹理世界文件生成器
├── setup.sh                 # 一键环境配置
├── config/
│   ├── texture_config.yaml  # 纹理定义（class ID、材质名）
│   └── texture_bboxes.json  # 手动 bounding box 标注
├── launch/
│   └── collect.launch       # 无头 Gazebo ROS 启动文件
├── urdf/
│   └── turtlebot3_burger_cam.urdf.xacro
├── materials/scripts/       # OGRE 材质文件（20 个纹理）
├── textures/                # 放你的纹理图片
├── scripts/
│   ├── run_collect.sh       # 一键启动脚本
│   └── vis_labels.py        # 标注可视化工具
└── docs/                    # 详细文档
```

## 文档

- [环境配置](docs/setup.md) — 安装依赖和配置
- [使用指南](docs/usage.md) — CLI 参数和常用流程
- [纹理准备](docs/texture_prep.md) — 如何准备自己的纹理
- [Pipeline 详解](docs/pipeline.md) — 从采集到训练的完整流程

## 使用你自己的纹理

```bash
# 把图片放到 textures/
cp my_object.jpg textures/

# 创建材质文件 materials/scripts/my_object.material
# 在 config/texture_config.yaml 中添加配置

# 测试
python3 gazebo_collect.py --texture my_object --test 5

# 全量采集
python3 gazebo_collect.py
```

## 许可证

MIT — 详见 [LICENSE](LICENSE)

## 引用

如果你在研究中使用了本工具，请引用：

```bibtex
@software{gazebo_yolo_collector,
  author = {player0729},
  title = {gazebo-yolo-collector: Auto-generate YOLO datasets from Gazebo},
  year = {2026},
  url = {https://github.com/player0729/gazebo-yolo-collector}
}
```
