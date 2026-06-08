"""
示例 02 — 实例开机 & 关机

运行方式
--------
    export AUTODL_TOKEN="your_token_here"
    python examples/02_power_on_off.py
"""

import os
from autodl import AutoDLClient, InstanceManager

TOKEN         = os.environ.get("AUTODL_TOKEN", "your_token_here")
INSTANCE_UUID = "your-instance-uuid"   # ← 填写你的实例 UUID

client = AutoDLClient(token=TOKEN)
mgr    = InstanceManager(client)

# ── 开机 ─────────────────────────────────────────────────────
print(f"🔋 对实例 {INSTANCE_UUID} 执行开机...")
success = mgr.power_on(INSTANCE_UUID, wait=True)
if success:
    ins = mgr.get_instance(INSTANCE_UUID)
    print(f"✅ 开机成功！SSH: root@{ins['proxy_host']} -p {ins['ssh_port']}")
else:
    print("❌ 开机超时，请登录控制台查看")

# ── 关机 ─────────────────────────────────────────────────────
# print(f"🔌 对实例 {INSTANCE_UUID} 执行关机...")
# success = mgr.power_off(INSTANCE_UUID, wait=True)
# print("✅ 已关机" if success else "❌ 关机超时")
