"""
示例 05 — 社区镜像创建实例

使用其他用户分享的社区镜像创建实例。
社区镜像通常已预装常用框架和依赖，适合快速复现他人环境。

如何找到社区镜像的 UUID
-----------------------
1. 登录 AutoDL 控制台
2. 进入"创建实例" → 选择"社区镜像"
3. 找到目标镜像，点击详情
4. 复制页面 URL 中的 UUID 部分，或从"复制镜像"按钮获取

运行方式
--------
    export AUTODL_TOKEN="your_token_here"
    python examples/05_create_community_image.py
"""

import os
from autodl import AutoDLClient, InstanceManager, IMAGE_TYPE_COMMUNITY

TOKEN = os.environ.get("AUTODL_TOKEN", "your_token_here")

# ── 配置 ─────────────────────────────────────────────────────
COMMUNITY_UUID = "your-community-image-uuid"   # ← 填写社区镜像的 reproduction_uuid

GPU_TYPES = ["RTX 4090", "RTX 4090D", "RTX 3090"]
GPU_NUM   = 1
MIN_CUDA  = 0.0   # 社区镜像通常已固定 CUDA 版本，可设为 0 不限制

# ── 主程序 ───────────────────────────────────────────────────
client = AutoDLClient(token=TOKEN)
mgr    = InstanceManager(client)

print("🔍 查询可用主机...")
machines = mgr.list_machines(gpu_types=GPU_TYPES, gpu_num=GPU_NUM, min_cuda=MIN_CUDA)
if not machines:
    print("❌ 当前无可用主机")
    exit(1)

best = machines[0]
print(f"✅ 最优主机：{best['gpu_name']}  ¥{best['payg_price']/1000:.3f}/时")

print("\n🚀 创建实例（社区镜像）...")
uuid = mgr.create(
    machine_id=best["machine_id"],
    image_type=IMAGE_TYPE_COMMUNITY,
    community_uuid=COMMUNITY_UUID,
    gpu_num=GPU_NUM,
    wait=True,
)

ins = mgr.get_instance(uuid)
print(f"\n✅ 实例已就绪！")
print(f"   UUID : {uuid}")
print(f"   SSH  : ssh root@{ins['proxy_host']} -p {ins['ssh_port']}")
print(f"   密码 : {ins['root_password']}")
