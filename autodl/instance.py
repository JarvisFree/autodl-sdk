"""
autodl/instance.py — 实例管理

功能列表
--------
1. list_instances()         获取实例列表
2. power_on()               实例开机
3. power_off()              实例关机
4. release()                释放实例
5. create()                 创建并开机（支持三种镜像类型）
6. get_balance()            查询账户余额
7. list_machines()          查找可用主机（支持过滤）
8. list_images()            获取我的镜像列表
9. wait_until_running()     等待实例变为运行状态（轮询）
"""

import time
from typing import Optional

from .client import AutoDLClient
from .utils import log, safe_float


# ── 镜像类型常量 ──────────────────────────────────────────────
IMAGE_TYPE_BASE      = "base"       # 官方基础镜像
IMAGE_TYPE_COMMUNITY = "community"  # 社区镜像
IMAGE_TYPE_PRIVATE   = "private"    # 我的镜像（自定义保存的镜像）

_POLL_INTERVAL = 5    # 轮询间隔（秒）
_POLL_TIMEOUT  = 180  # 最长等待时间（秒）


class InstanceManager:
    """
    AutoDL 实例管理器。

    参数
    ----
    client : AutoDLClient
        已初始化的 HTTP 客户端。

    示例
    ----
    >>> from autodl.client import AutoDLClient
    >>> from autodl.instance import InstanceManager
    >>> client = AutoDLClient(token="your_token")
    >>> mgr = InstanceManager(client)
    """

    def __init__(self, client: AutoDLClient):
        self._c = client

    # ══════════════════════════════════════════════════════════
    # 1. 获取实例列表
    # ══════════════════════════════════════════════════════════

    def list_instances(
        self,
        status: list[str] = None,
        page_index: int = 1,
        page_size: int = 50,
    ) -> list[dict]:
        """
        获取当前账户的实例列表。

        参数
        ----
        status : list[str], optional
            按状态过滤，可选值：
            "running"（运行中）、"shutdown"（已关机）、
            "creating"（创建中）、"abnormal"（异常）。
            默认为空，即返回所有状态的实例。
        page_index : int
            页码，默认 1。
        page_size : int
            每页数量，默认 50。

        返回
        ----
        list[dict]
            实例列表，每个实例包含以下关键字段：
            - uuid          : 实例唯一标识
            - instance_name : 实例名称
            - status        : 运行状态
            - gpu_name      : GPU 型号
            - payg_price    : 按量计费单价（单位：毫元/时）
            - proxy_host    : SSH 代理主机
            - ssh_port      : SSH 端口
            - root_password : root 密码

        示例
        ----
        >>> instances = mgr.list_instances()
        >>> for ins in instances:
        ...     print(ins["uuid"], ins["status"])

        >>> running = mgr.list_instances(status=["running"])
        """
        data = self._c.post("/instance", {
            "page_index": page_index,
            "page_size": page_size,
            "status": status or [],
            "charge_type": [],
            "sub_name": "",
            "unbind_sub_user": False,
        })
        return data.get("list", [])

    def get_instance(self, uuid: str) -> Optional[dict]:
        """
        获取单个实例的详细信息。

        参数
        ----
        uuid : str
            实例 UUID。

        返回
        ----
        dict 或 None
            实例详情字典，未找到时返回 None。
        """
        instances = self.list_instances()
        for ins in instances:
            if ins.get("uuid") == uuid:
                return ins
        return None

    # ══════════════════════════════════════════════════════════
    # 2. 实例开机
    # ══════════════════════════════════════════════════════════

    def power_on(self, uuid: str, wait: bool = True) -> bool:
        """
        对已关机的实例执行开机操作。

        参数
        ----
        uuid : str
            实例 UUID。
        wait : bool
            是否等待实例变为 running 状态后再返回，默认 True。

        返回
        ----
        bool
            wait=True 时：实例成功启动返回 True，超时返回 False。
            wait=False 时：请求发送成功即返回 True。

        示例
        ----
        >>> success = mgr.power_on("your-instance-uuid")
        >>> print("开机成功" if success else "开机超时")
        """
        self._c.post("/instance/power_on", {"instance_uuid": uuid})
        log(f"已发送开机指令：{uuid}")
        if wait:
            result = self.wait_until_running(uuid)
            return result == "running"
        return True

    # ══════════════════════════════════════════════════════════
    # 3. 实例关机
    # ══════════════════════════════════════════════════════════

    def power_off(self, uuid: str, wait: bool = True) -> bool:
        """
        对运行中的实例执行关机操作。

        参数
        ----
        uuid : str
            实例 UUID。
        wait : bool
            是否等待实例变为 shutdown 状态后再返回，默认 True。

        返回
        ----
        bool
            成功关机返回 True，超时返回 False。

        示例
        ----
        >>> mgr.power_off("your-instance-uuid")
        """
        self._c.post("/instance/power_off", {"instance_uuid": uuid})
        log(f"已发送关机指令：{uuid}")
        if not wait:
            return True
        deadline = time.time() + 120
        while time.time() < deadline:
            ins = self.get_instance(uuid)
            if ins and ins.get("status") == "shutdown":
                log("实例已关机")
                return True
            time.sleep(_POLL_INTERVAL)
        log("⚠️  等待关机超时")
        return False

    # ══════════════════════════════════════════════════════════
    # 4. 释放实例
    # ══════════════════════════════════════════════════════════

    def release(self, uuid: str, force: bool = False):
        """
        释放实例（彻底删除，不可恢复）。

        参数
        ----
        uuid : str
            实例 UUID。
        force : bool
            若实例当前为运行状态，是否先自动关机再释放。
            默认 False，运行中实例会抛出异常。

        异常
        ----
        RuntimeError
            force=False 且实例处于运行状态时抛出。

        示例
        ----
        >>> mgr.release("your-instance-uuid")              # 仅对已关机实例释放
        >>> mgr.release("your-instance-uuid", force=True)  # 强制先关机再释放
        """
        if force:
            ins = self.get_instance(uuid)
            if ins and ins.get("status") == "running":
                log("实例运行中，先执行关机...")
                self.power_off(uuid, wait=True)

        self._c.post("/instance/release", {"instance_uuid": uuid})
        log(f"✅ 实例已释放：{uuid}")

    # ══════════════════════════════════════════════════════════
    # 5. 创建新实例（创建并开机）
    # ══════════════════════════════════════════════════════════

    def create(
        self,
        machine_id: str,
        image_type: str,
        *,
        # 基础镜像参数
        base_image_url: str = "",
        # 社区镜像参数
        community_uuid: str = "",
        # 我的镜像参数
        private_image_uuid: str = "",
        private_image_url: str = "",
        # 通用参数
        gpu_num: int = 1,
        instance_name: str = "",
        expand_data_disk: int = 0,
        wait: bool = True,
    ) -> str:
        """
        创建新实例并开机。支持三种镜像类型。

        参数
        ----
        machine_id : str
            目标主机 ID（从 list_machines() 结果中获取）。
        image_type : str
            镜像类型，使用模块内常量：
            - IMAGE_TYPE_BASE      = "base"       官方基础镜像
            - IMAGE_TYPE_COMMUNITY = "community"  社区镜像
            - IMAGE_TYPE_PRIVATE   = "private"    我的镜像

        基础镜像专用参数
        ---------------
        base_image_url : str
            官方镜像完整 URL，例：
            "hub.kce.ksyun.com/autodl-image/torch:cuda12.4-cudnn-devel-ubuntu22.04-py312-torch2.5.1"

        社区镜像专用参数
        ---------------
        community_uuid : str
            社区镜像的 reproduction_uuid，在镜像详情页可找到。

        我的镜像专用参数
        ---------------
        private_image_uuid : str
            自定义镜像 UUID，例："image-47c93bf9ce"。
        private_image_url : str
            自定义镜像对应的基础镜像 URL（在镜像详情页可看到）。

        通用参数
        --------
        gpu_num : int
            申请的 GPU 数量，默认 1。
        instance_name : str
            实例名称，默认为空（AutoDL 自动命名）。
        expand_data_disk : int
            扩展数据盘大小（GB），默认 0 不扩展。
        wait : bool
            是否等待实例 running 后返回，默认 True。

        返回
        ----
        str
            新建实例的 UUID。

        异常
        ----
        ValueError
            镜像类型不合法或必填参数缺失时抛出。
        RuntimeError
            实例创建失败或启动超时时抛出。

        示例
        ----
        # 基础镜像
        >>> uuid = mgr.create(
        ...     machine_id="machine-xxx",
        ...     image_type=IMAGE_TYPE_BASE,
        ...     base_image_url="hub.kce.ksyun.com/autodl-image/torch:cuda12.4-...",
        ... )

        # 社区镜像
        >>> uuid = mgr.create(
        ...     machine_id="machine-xxx",
        ...     image_type=IMAGE_TYPE_COMMUNITY,
        ...     community_uuid="repro-uuid-xxx",
        ... )

        # 我的镜像
        >>> uuid = mgr.create(
        ...     machine_id="machine-xxx",
        ...     image_type=IMAGE_TYPE_PRIVATE,
        ...     private_image_uuid="image-47c93bf9ce",
        ...     private_image_url="hub.kce.ksyun.com/autodl-image/torch:...",
        ... )
        """
        image_url, private_uuid, repro_uuid = self._resolve_image(
            image_type, base_image_url, community_uuid,
            private_image_uuid, private_image_url,
        )

        uuid = self._c.post("/order/instance/create/payg", {
            "instance_info": {
                "machine_id": machine_id,
                "charge_type": "payg",
                "req_gpu_amount": gpu_num,
                "image": image_url,
                "private_image_uuid": private_uuid,
                "reproduction_uuid": repro_uuid,
                "cg_application_uuid": "",
                "cg_application_info": {
                    "app_name": "", "current_version_id": 0,
                    "current_version": "", "image_id": 0,
                },
                "instance_name": instance_name,
                "expand_data_disk": expand_data_disk,
                "reproduction_id": 0,
            },
            "price_info": {
                "coupon_id_list": [],
                "machine_id": machine_id,
                "charge_type": "payg",
                "duration": 1,
                "num": gpu_num,
                "expand_data_disk": expand_data_disk,
            },
        })

        log(f"实例创建成功，UUID：{uuid}")

        if wait:
            result = self.wait_until_running(uuid)
            if result != "running":
                raise RuntimeError(f"实例启动异常，状态：{result}，请登录控制台查看")

        return uuid

    @staticmethod
    def _resolve_image(
        image_type, base_image_url, community_uuid,
        private_image_uuid, private_image_url,
    ) -> tuple[str, str, str]:
        """解析三种镜像类型，返回 (image_url, private_uuid, repro_uuid)"""
        if image_type == IMAGE_TYPE_BASE:
            if not base_image_url:
                raise ValueError("image_type='base' 时必须传入 base_image_url")
            return base_image_url, "", ""

        elif image_type == IMAGE_TYPE_COMMUNITY:
            if not community_uuid:
                raise ValueError("image_type='community' 时必须传入 community_uuid")
            return "", "", community_uuid

        elif image_type == IMAGE_TYPE_PRIVATE:
            if not private_image_uuid:
                raise ValueError("image_type='private' 时必须传入 private_image_uuid")
            return private_image_url, private_image_uuid, ""

        else:
            raise ValueError(
                f"不支持的 image_type：'{image_type}'，"
                f"请使用 IMAGE_TYPE_BASE / IMAGE_TYPE_COMMUNITY / IMAGE_TYPE_PRIVATE"
            )

    # ══════════════════════════════════════════════════════════
    # 6. 查询余额
    # ══════════════════════════════════════════════════════════

    def get_balance(self) -> float:
        """
        查询按量计费账户余额（单位：元）。

        返回
        ----
        float
            当前余额，例：12.34。

        示例
        ----
        >>> balance = mgr.get_balance()
        >>> print(f"当前余额：¥{balance:.2f}")
        """
        data = self._c.get("/wallet/balance", {"charge_type": "payg"})
        return data.get("assets", 0) / 1000

    # ══════════════════════════════════════════════════════════
    # 7. 查找可用主机
    # ══════════════════════════════════════════════════════════

    def list_machines(
        self,
        gpu_types: list[str] = None,
        gpu_num: int = 1,
        min_cuda: float = 0.0,
        sort_by_price: bool = True,
    ) -> list[dict]:
        """
        查询当前有空闲 GPU 的主机列表。

        参数
        ----
        gpu_types : list[str], optional
            GPU 型号白名单，例：["RTX 4090", "RTX 4090D", "RTX 3090"]。
            默认为空，即不限型号。
        gpu_num : int
            所需 GPU 数量，默认 1。
        min_cuda : float
            最低 CUDA 版本要求，例：12.4。默认 0.0 不限制。
        sort_by_price : bool
            是否按价格从低到高排序，默认 True。

        返回
        ----
        list[dict]
            可用主机列表，每个主机包含：
            - machine_id      : 主机 ID
            - machine_alias   : 主机别名
            - region_name     : 地区
            - gpu_name        : GPU 型号
            - gpu_idle_num    : 当前空闲 GPU 数
            - payg_price      : 按量单价（毫元/时）
            - highest_cuda_version : 最高支持的 CUDA 版本

        示例
        ----
        >>> machines = mgr.list_machines(
        ...     gpu_types=["RTX 4090", "RTX 3090"],
        ...     min_cuda=12.4,
        ... )
        >>> for m in machines:
        ...     print(m["gpu_name"], f"¥{m['payg_price']/1000:.3f}/h")
        """
        data = self._c.post("/user/machine/list", {
            "charge_type": "payg",
            "region_sign": "",
            "gpu_type_name": gpu_types or [],
            "machine_tag_name": [],
            "gpu_idle_num": gpu_num,
            "mount_net_disk": False,
            "instance_disk_size_order": "",
            "date_range": "",
            "date_from": "",
            "date_to": "",
            "page_index": 1,
            "page_size": 100,
            "pay_price_order": "",
            "gpu_idle_type": "",
            "default_order": True,
            "region_sign_list": [],
            "cpu_arch": [],
            "chip_corp": [],
            "machine_id": "",
        })
        machines = data.get("list", [])

        # 过滤：空闲 GPU 数量 & CUDA 版本
        result = [
            m for m in machines
            if m.get("gpu_idle_num", 0) >= gpu_num
            and safe_float(m.get("highest_cuda_version", "0")) >= min_cuda
        ]

        if sort_by_price:
            result.sort(key=lambda m: m.get("payg_price", 999999))

        return result

    # ══════════════════════════════════════════════════════════
    # 8. 获取我的镜像列表
    # ══════════════════════════════════════════════════════════

    def list_images(self) -> list[dict]:
        """
        获取当前账户保存的私有镜像列表（即"我的镜像"）。

        返回
        ----
        list[dict]
            镜像列表，每个镜像包含：
            - image_uuid  : 镜像唯一标识（创建实例时传入 private_image_uuid）
            - image_name  : 镜像名称
            - create_time : 创建时间

        示例
        ----
        >>> images = mgr.list_images()
        >>> for img in images:
        ...     print(img["image_uuid"], img["image_name"])
        """
        return self._c.post("/image/private/get", {"cpu_arch": [], "chip_corp": []})

    # ══════════════════════════════════════════════════════════
    # 9. 等待实例变为 running（轮询）
    # ══════════════════════════════════════════════════════════

    def wait_until_running(
        self,
        uuid: str,
        timeout: int = _POLL_TIMEOUT,
        interval: int = _POLL_INTERVAL,
    ) -> str:
        """
        轮询等待实例状态变为 running。

        参数
        ----
        uuid : str
            实例 UUID。
        timeout : int
            最长等待秒数，默认 180。
        interval : int
            轮询间隔秒数，默认 5。

        返回
        ----
        str
            最终状态字符串：
            - "running"  : 启动成功
            - "abnormal" : 出现 error/failed 异常状态
            - "timeout"  : 等待超时

        示例
        ----
        >>> result = mgr.wait_until_running("your-instance-uuid")
        >>> if result != "running":
        ...     print(f"启动失败，状态：{result}")
        """
        deadline = time.time() + timeout
        last_status = ""

        while time.time() < deadline:
            ins = self.get_instance(uuid)
            if not ins:
                time.sleep(interval)
                continue

            status = ins.get("status", "")
            sub    = ins.get("sub_status", "")
            cur    = f"{status}/{sub}" if sub else status

            if cur != last_status:
                log(f"实例状态：{cur}")
                last_status = cur

            if status == "running":
                return "running"
            if any(kw in cur.lower() for kw in ("error", "failed", "abnormal")):
                return "abnormal"

            time.sleep(interval)

        return "timeout"
