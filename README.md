# autodl-sdk

> AutoDL GPU 云平台 Python 自动化 SDK，用几行代码完成实例管理、代码上传、远程执行全流程。

---

## 功能列表

| 功能 | 方法 | 说明 |
|------|------|------|
| 获取实例列表 | `mgr.list_instances()` | 支持按状态过滤 |
| 查看单个实例 | `mgr.get_instance(uuid)` | 返回 SSH 连接信息 |
| 实例开机 | `mgr.power_on(uuid)` | 等待 running 后返回 |
| 实例关机 | `mgr.power_off(uuid)` | 等待 shutdown 后返回 |
| 释放实例 | `mgr.release(uuid)` | 支持 force 先关机再释放 |
| 创建实例（基础镜像） | `mgr.create(..., image_type="base")` | 官方 CUDA/PyTorch 镜像 |
| 创建实例（社区镜像） | `mgr.create(..., image_type="community")` | 他人分享的镜像 |
| 创建实例（我的镜像） | `mgr.create(..., image_type="private")` | 自己保存的镜像 |
| 查询余额 | `mgr.get_balance()` | 按量计费余额 |
| 查询可用主机 | `mgr.list_machines()` | 支持 GPU 型号/CUDA/数量过滤 |
| 获取我的镜像 | `mgr.list_images()` | 查看私有镜像 UUID |
| SSH 执行命令 | `ssh.run_command(cmd)` | 实时输出，支持超时 |
| 上传文件 | `ssh.upload_file(local, remote)` | 单文件上传 |
| 上传目录 | `ssh.upload_dir(local, remote)` | 递归上传，支持排除列表 |
| 下载目录 | `ssh.download_dir(remote, local)` | 批量下载输出文件 |
| 下载文件 | `ssh.download_file(remote, local)` | 单文件下载 |

---

## 安装

```bash
pip install autodl-sdk
```

或从源码安装：

```bash
git clone https://github.com/your-username/autodl-sdk.git
cd autodl-sdk
pip install -e .
```

**依赖**：`requests >= 2.28`，`paramiko >= 3.0`，Python >= 3.10

---

## 快速开始

### 第一步：获取 AutoDL Token

1. 打开浏览器，登录 [autodl.com](https://www.autodl.com)
2. 按 **F12** 打开开发者工具 → Network 标签
3. 随便点一个页面操作（如刷新实例列表）
4. 在请求列表中找任意一个 `api/v1/` 开头的请求
5. 查看请求头（Headers），复制 **Authorization** 字段的值
6. 这就是你的 Token，形如 `Bearer eyJhbGci...`

> ⚠️ Token 包含账户权限，请勿泄露、勿提交到 Git

### 第二步：配置 Token

推荐通过环境变量传入，避免硬编码：

```bash
# macOS / Linux
export AUTODL_TOKEN="Bearer eyJhbGci..."

# Windows PowerShell
$env:AUTODL_TOKEN = "Bearer eyJhbGci..."
```

### 第三步：运行示例

```bash
# 查看实例列表和余额
python examples/01_list_instances.py

# 开机
python examples/02_power_on_off.py

# 创建实例（基础镜像）
python examples/04_create_base_image.py

# 上传代码并执行（完整工作流）
python examples/07_upload_and_run.py
```

---

## 代码示例

### 查询余额和实例列表

```python
from autodl import AutoDLClient, InstanceManager

client = AutoDLClient(token="Bearer eyJhbGci...")
mgr    = InstanceManager(client)

print(f"余额：¥{mgr.get_balance():.2f}")

for ins in mgr.list_instances():
    print(ins["uuid"], ins["status"], ins.get("gpu_name"))
```

### 开机 / 关机

```python
mgr.power_on("your-instance-uuid")   # 开机，等待 running
mgr.power_off("your-instance-uuid")  # 关机，等待 shutdown
```

### 释放实例

```python
mgr.release("your-instance-uuid")              # 已关机才能释放
mgr.release("your-instance-uuid", force=True)  # 自动先关机再释放
```

### 创建实例

```python
from autodl import IMAGE_TYPE_BASE, IMAGE_TYPE_COMMUNITY, IMAGE_TYPE_PRIVATE

# 查询最便宜的可用 4090
machines = mgr.list_machines(gpu_types=["RTX 4090", "RTX 3090"], min_cuda=12.4)
machine_id = machines[0]["machine_id"]

# 方式一：基础镜像
uuid = mgr.create(
    machine_id=machine_id,
    image_type=IMAGE_TYPE_BASE,
    base_image_url="hub.kce.ksyun.com/autodl-image/torch:cuda12.4-cudnn-devel-ubuntu22.04-py312-torch2.5.1",
)

# 方式二：社区镜像
uuid = mgr.create(
    machine_id=machine_id,
    image_type=IMAGE_TYPE_COMMUNITY,
    community_uuid="your-community-image-uuid",
)

# 方式三：我的镜像
uuid = mgr.create(
    machine_id=machine_id,
    image_type=IMAGE_TYPE_PRIVATE,
    private_image_uuid="image-47c93bf9ce",
    private_image_url="hub.kce.ksyun.com/autodl-image/torch:cuda12.4-...",
)
```

### 上传代码并执行

```python
from autodl import SSHManager

# 获取实例 SSH 信息
ins = mgr.get_instance(uuid)
ssh = SSHManager.from_instance(ins)

# 上传项目目录
ssh.upload_dir(
    local_dir="./my_project",
    remote_dir="/root/my_project",
    exclude=["__pycache__", ".git", "output"],
)

# 安装依赖
ssh.run_command("cd /root/my_project && pip install -r requirements.txt -q", timeout=300)

# 执行主程序
ssh.run_command("cd /root/my_project && python main.py", timeout=3600)

# 下载输出结果
ssh.download_dir("/root/my_project/output", "./output")
```

### 完整自动化流程（带计时和余额统计）

```python
from autodl import AutoDLClient, InstanceManager, SSHManager, IMAGE_TYPE_PRIVATE, Timer

client = AutoDLClient(token="Bearer ...")
mgr    = InstanceManager(client)
timer  = Timer()

balance_before = mgr.get_balance()
uuid = None

try:
    timer.begin("创建实例")
    machines = mgr.list_machines(gpu_types=["RTX 4090"], min_cuda=12.4)
    uuid = mgr.create(
        machine_id=machines[0]["machine_id"],
        image_type=IMAGE_TYPE_PRIVATE,
        private_image_uuid="image-xxx",
        private_image_url="hub.kce.ksyun.com/...",
    )
    timer.end("创建实例")

    ins = mgr.get_instance(uuid)
    ssh = SSHManager.from_instance(ins)

    timer.begin("上传 & 运行")
    ssh.upload_dir("./project", "/root/project")
    ssh.run_command("cd /root/project && python main.py")
    timer.end("上传 & 运行")

    ssh.download_dir("/root/project/output", "./output")

finally:
    if uuid:
        mgr.power_off(uuid)
        mgr.release(uuid)

    timer.summary()
    print(f"消耗：¥{balance_before - mgr.get_balance():.4f}")
```

---

## 参数说明

### `AutoDLClient`

| 参数 | 类型 | 说明 |
|------|------|------|
| `token` | str | AutoDL JWT Token（必填） |
| `timeout` | int | HTTP 超时秒数，默认 20 |

### `InstanceManager.create()`

| 参数 | 类型 | 说明 |
|------|------|------|
| `machine_id` | str | 主机 ID（来自 `list_machines()`） |
| `image_type` | str | `"base"` / `"community"` / `"private"` |
| `base_image_url` | str | 基础镜像 URL（image_type="base" 时必填） |
| `community_uuid` | str | 社区镜像 UUID（image_type="community" 时必填） |
| `private_image_uuid` | str | 私有镜像 UUID（image_type="private" 时必填） |
| `private_image_url` | str | 私有镜像对应基础镜像 URL |
| `gpu_num` | int | GPU 数量，默认 1 |
| `wait` | bool | 是否等待实例 running，默认 True |

### `SSHManager.run_command()`

| 参数 | 类型 | 说明 |
|------|------|------|
| `command` | str | 要执行的 shell 命令 |
| `timeout` | int | 超时秒数，默认 600 |
| `use_conda` | bool | 是否先激活 conda base 环境，默认 True |
| `raise_on_error` | bool | 非零退出码时是否抛异常，默认 True |

---

## 常见问题

**Q：Token 从哪里获取？**  
A：浏览器登录 autodl.com → F12 → Network → 任意 `api/v1/` 请求 → Headers → Authorization 字段。

**Q：Token 有效期多久？**  
A：AutoDL 的 Token 通常较长，但如果遇到 401 错误请重新抓取。

**Q：社区镜像的 UUID 怎么找？**  
A：控制台 → 创建实例 → 选社区镜像 → 查看镜像详情页 URL 中的 UUID。

**Q：`wait=True` 等待多久超时？**  
A：默认 180 秒。可调用 `wait_until_running(uuid, timeout=300)` 手动指定。

**Q：上传大项目很慢怎么办？**  
A：用 `exclude` 参数排除不需要上传的目录（如 `node_modules`、`__pycache__`、大数据文件），或提前将依赖打包进镜像。

---

## 目录结构

```
autodl-sdk/
├── autodl/
│   ├── __init__.py     # 统一入口，导出所有公共 API
│   ├── client.py       # HTTP 客户端基础封装
│   ├── instance.py     # 实例管理（增删改查 + 创建三种镜像）
│   ├── ssh.py          # SSH 连接、文件上传/下载、命令执行
│   └── utils.py        # 日志、计时器等工具函数
├── examples/
│   ├── 01_list_instances.py      # 查询实例列表和余额
│   ├── 02_power_on_off.py        # 开机 / 关机
│   ├── 03_release.py             # 释放实例
│   ├── 04_create_base_image.py   # 基础镜像创建实例
│   ├── 05_create_community_image.py  # 社区镜像创建实例
│   ├── 06_create_my_image.py     # 我的镜像创建实例
│   └── 07_upload_and_run.py      # 完整工作流：上传代码并执行
├── pyproject.toml
└── README.md
```

---

## License

MIT — 自由使用，欢迎 Star & Fork。
