"""
示例 07 — 上传代码至实例并执行

演示完整工作流：
  1. 查询可用主机
  2. 创建实例（我的镜像）
  3. 上传本地项目目录
  4. 安装依赖
  5. 执行训练/推理命令
  6. 下载输出结果
  7. 关机释放

运行方式
--------
    export AUTODL_TOKEN="your_token_here"
    python examples/07_upload_and_run.py
"""

import os
from autodl import AutoDLClient, InstanceManager, SSHManager, IMAGE_TYPE_PRIVATE, Timer

TOKEN = os.environ.get("AUTODL_TOKEN", "your_token_here")

# ── 配置 ─────────────────────────────────────────────────────
PRIVATE_IMAGE_UUID = "image-47c93bf9ce"
PRIVATE_IMAGE_URL  = "hub.kce.ksyun.com/autodl-image/torch:cuda12.4-cudnn-devel-ubuntu22.04-py312-torch2.5.1"

GPU_TYPES  = ["RTX 4090", "RTX 4090D", "RTX 3090"]
GPU_NUM    = 1
MIN_CUDA   = 12.4

LOCAL_PROJECT_DIR  = "./my_project"          # 本地项目目录
REMOTE_PROJECT_DIR = "/root/my_project"      # 上传到实例的路径
REMOTE_OUTPUT_DIR  = "/root/my_project/output"
LOCAL_OUTPUT_DIR   = "./output"

RUN_COMMAND = f"cd {REMOTE_PROJECT_DIR} && python main.py"

# ── 主程序 ───────────────────────────────────────────────────
client = AutoDLClient(token=TOKEN)
mgr    = InstanceManager(client)
timer  = Timer()

balance = mgr.get_balance()
print(f"💰 当前余额：¥{balance:.2f}")
if balance < 1:
    print("❌ 余额不足 ¥1，请先充值")
    exit(1)

uuid = None
try:
    # Step 1：选机 + 创建实例
    print("\n── Step 1/4  选机 & 创建实例 ──")
    timer.begin("创建实例")
    machines = mgr.list_machines(gpu_types=GPU_TYPES, gpu_num=GPU_NUM, min_cuda=MIN_CUDA)
    if not machines:
        raise RuntimeError("无可用主机")

    best = machines[0]
    print(f"选中主机：{best['gpu_name']}  ¥{best['payg_price']/1000:.3f}/时")

    uuid = mgr.create(
        machine_id=best["machine_id"],
        image_type=IMAGE_TYPE_PRIVATE,
        private_image_uuid=PRIVATE_IMAGE_UUID,
        private_image_url=PRIVATE_IMAGE_URL,
        gpu_num=GPU_NUM,
        wait=True,
    )
    timer.end("创建实例")

    ins = mgr.get_instance(uuid)
    ssh = SSHManager.from_instance(ins)

    # Step 2：上传代码
    print("\n── Step 2/4  上传代码 ──")
    timer.begin("上传代码")
    ssh.upload_dir(
        local_dir=LOCAL_PROJECT_DIR,
        remote_dir=REMOTE_PROJECT_DIR,
        exclude=["__pycache__", ".git", "output", "*.pyc", ".env"],
    )
    timer.end("上传代码")

    # Step 3：执行命令
    print("\n── Step 3/4  执行命令 ──")
    timer.begin("执行任务")
    # 先安装依赖（如果有 requirements.txt）
    ssh.run_command(f"cd {REMOTE_PROJECT_DIR} && pip install -r requirements.txt -q", timeout=300)
    # 执行主程序
    ssh.run_command(RUN_COMMAND, timeout=3600)
    timer.end("执行任务")

    # Step 4：下载结果
    print("\n── Step 4/4  下载结果 ──")
    timer.begin("下载结果")
    ssh.download_dir(REMOTE_OUTPUT_DIR, LOCAL_OUTPUT_DIR)
    timer.end("下载结果")

except Exception as e:
    print(f"\n❌ 流程异常：{e}")
    import traceback; traceback.print_exc()

finally:
    if uuid:
        print("\n🔌 关机并释放实例...")
        mgr.power_off(uuid, wait=True)
        mgr.release(uuid)
        print(f"✅ 实例 {uuid} 已释放")

    timer.summary()
    after = mgr.get_balance()
    print(f"\n💰 余额变化：¥{balance:.2f} → ¥{after:.2f}  (消耗 ¥{balance-after:.4f})")
