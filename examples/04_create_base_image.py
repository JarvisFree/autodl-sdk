"""
示例 04 — 基础镜像创建实例

使用官方提供的基础镜像（如 PyTorch + CUDA 环境）创建新实例。
适合：第一次使用，或希望从干净环境开始。

运行方式
--------
    export AUTODL_TOKEN="your_token_here"
    python examples/04_create_base_image.py
"""

import os
from autodl import AutoDLClient, InstanceManager, IMAGE_TYPE_BASE

TOKEN = os.environ.get("AUTODL_TOKEN", "your_token_here")

# ── 配置 ─────────────────────────────────────────────────────
# 官方基础镜像 URL，在 AutoDL 创建实例页面的"基础镜像"列表中复制
BASE_IMAGE_URL = "hub.kce.ksyun.com/autodl-image/torch:cuda12.4-cudnn-devel-ubuntu22.04-py312-torch2.5.1"

GPU_TYPES  = ["RTX 4090", "RTX 4090D", "RTX 3090"]  # 可接受的 GPU 型号
GPU_NUM    = 1
MIN_CUDA   = 12.4

# ── 主程序 ───────────────────────────────────────────────────
client = AutoDLClient(token=TOKEN)
mgr    = InstanceManager(client)

# 先查询可用主机
print("🔍 查询可用主机...")
machines = mgr.list_machines(gpu_types=GPU_TYPES, gpu_num=GPU_NUM, min_cuda=MIN_CUDA)
if not machines:
    print("❌ 当前无符合条件的可用主机，请稍后重试或调整 GPU 型号要求")
    exit(1)

best = machines[0]
print(f"✅ 最优主机：{best['gpu_name']} @ {best.get('region_name','')}  ¥{best['payg_price']/1000:.3f}/时")

# 创建实例
print("\n🚀 创建实例（基础镜像）...")
uuid = mgr.create(
    machine_id=best["machine_id"],
    image_type=IMAGE_TYPE_BASE,
    base_image_url=BASE_IMAGE_URL,
    gpu_num=GPU_NUM,
    wait=True,   # 等待实例 running 后返回
)

ins = mgr.get_instance(uuid)
print(f"\n✅ 实例已就绪！")
print(f"   UUID : {uuid}")
print(f"   SSH  : ssh root@{ins['proxy_host']} -p {ins['ssh_port']}")
print(f"   密码 : {ins['root_password']}")
