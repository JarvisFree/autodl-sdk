"""
示例 06 — 我的镜像创建实例

使用自己保存的私有镜像（"我的镜像"）创建实例。
适合：已跑通环境后保存镜像，下次直接复用，无需重装依赖。

如何找到私有镜像 UUID
--------------------
方式一：运行本示例后打印所有镜像列表
方式二：登录 AutoDL 控制台 → 镜像管理 → 我的镜像 → 点击详情

运行方式
--------
    export AUTODL_TOKEN="your_token_here"
    python examples/06_create_my_image.py
"""

import os
from autodl import AutoDLClient, InstanceManager, IMAGE_TYPE_PRIVATE

TOKEN = os.environ.get("AUTODL_TOKEN", "your_token_here")

# ── 配置 ─────────────────────────────────────────────────────
PRIVATE_IMAGE_UUID = "image-47c93bf9ce"   # ← 你的镜像 UUID，如 image-47c93bf9ce
PRIVATE_IMAGE_URL  = "hub.kce.ksyun.com/autodl-image/torch:cuda12.4-cudnn-devel-ubuntu22.04-py312-torch2.5.1"
# ↑ 镜像对应的基础镜像 URL，在镜像详情页可以看到

GPU_TYPES = ["RTX 4090", "RTX 4090D", "RTX 3090"]
GPU_NUM   = 1
MIN_CUDA  = 12.4

# ── 查询我的镜像列表 ─────────────────────────────────────────
client = AutoDLClient(token=TOKEN)
mgr    = InstanceManager(client)

print("📦 我的镜像列表：")
images = mgr.list_images()
for img in images:
    print(f"  UUID : {img.get('image_uuid')}  名称 : {img.get('image_name')}")
print()

# ── 查询可用主机 ─────────────────────────────────────────────
print("🔍 查询可用主机...")
machines = mgr.list_machines(gpu_types=GPU_TYPES, gpu_num=GPU_NUM, min_cuda=MIN_CUDA)
if not machines:
    print("❌ 当前无可用主机")
    exit(1)

best = machines[0]
print(f"✅ 最优主机：{best['gpu_name']}  ¥{best['payg_price']/1000:.3f}/时")

# ── 创建实例 ─────────────────────────────────────────────────
print("\n🚀 创建实例（我的镜像）...")
uuid = mgr.create(
    machine_id=best["machine_id"],
    image_type=IMAGE_TYPE_PRIVATE,
    private_image_uuid=PRIVATE_IMAGE_UUID,
    private_image_url=PRIVATE_IMAGE_URL,
    gpu_num=GPU_NUM,
    wait=True,
)

ins = mgr.get_instance(uuid)
print(f"\n✅ 实例已就绪！")
print(f"   UUID : {uuid}")
print(f"   SSH  : ssh root@{ins['proxy_host']} -p {ins['ssh_port']}")
print(f"   密码 : {ins['root_password']}")
