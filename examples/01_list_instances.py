"""
示例 01 — 获取实例列表 & 查询余额

运行方式
--------
    export AUTODL_TOKEN="your_token_here"
    python examples/01_list_instances.py
"""

import os
from autodl import AutoDLClient, InstanceManager

# ── 配置 ─────────────────────────────────────────────────────
TOKEN = os.environ.get("AUTODL_TOKEN", "your_token_here")

# ── 主程序 ───────────────────────────────────────────────────
client = AutoDLClient(token=TOKEN)
mgr    = InstanceManager(client)

# 查询余额
balance = mgr.get_balance()
print(f"💰 当前余额：¥{balance:.2f}\n")

# 获取全部实例
instances = mgr.list_instances()
print(f"📋 共 {len(instances)} 个实例：\n")

for ins in instances:
    price = ins.get("payg_price", 0) / 1000
    print(
        f"  UUID   : {ins['uuid']}\n"
        f"  名称   : {ins.get('instance_name', '(未命名)')}\n"
        f"  状态   : {ins['status']}\n"
        f"  GPU    : {ins.get('gpu_name', '?')}\n"
        f"  单价   : ¥{price:.3f}/时\n"
        f"  SSH    : root@{ins.get('proxy_host', '?')} -p {ins.get('ssh_port', '?')}\n"
        + "  " + "─" * 44
    )

# 单独查询某个实例详情（需填写 UUID）
# uuid = "your-instance-uuid"
# detail = mgr.get_instance(uuid)
# print(detail)
