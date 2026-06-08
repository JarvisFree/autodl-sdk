"""
示例 03 — 释放实例

⚠️  警告：释放操作不可恢复！实例及其数据盘将被彻底删除。
    请确认已下载所有需要保留的数据后再执行。

运行方式
--------
    export AUTODL_TOKEN="your_token_here"
    python examples/03_release.py
"""

import os
from autodl import AutoDLClient, InstanceManager

TOKEN         = os.environ.get("AUTODL_TOKEN", "your_token_here")
INSTANCE_UUID = "your-instance-uuid"   # ← 填写你的实例 UUID

client = AutoDLClient(token=TOKEN)
mgr    = InstanceManager(client)

# 确认提示，防止误操作
ins = mgr.get_instance(INSTANCE_UUID)
if not ins:
    print(f"❌ 未找到实例：{INSTANCE_UUID}")
    exit(1)

print(f"⚠️  即将释放实例：{ins.get('instance_name', INSTANCE_UUID)}")
print(f"   GPU   : {ins.get('gpu_name', '?')}")
print(f"   状态  : {ins['status']}")
confirm = input("确认释放？输入 yes 继续：")

if confirm.strip().lower() != "yes":
    print("已取消")
    exit(0)

# force=True：若实例运行中，自动先关机再释放
mgr.release(INSTANCE_UUID, force=True)
print("✅ 实例已释放")
