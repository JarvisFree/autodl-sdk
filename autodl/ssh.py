"""
autodl/ssh.py — SSH 连接、文件上传与命令执行

功能
----
- upload_dir()   将本地目录上传至实例（通过 SFTP）
- upload_file()  将单个文件上传至实例
- run_command()  在实例上执行 shell 命令（输出实时打印）
- download_dir() 下载实例上的目录到本地
"""

import os
import re
import time

import paramiko

from .utils import log


_CONDA_INIT = "source /root/miniconda3/etc/profile.d/conda.sh && conda activate base"


class SSHManager:
    """
    AutoDL 实例 SSH 操作管理器。

    参数
    ----
    host : str
        代理主机地址（即实例 proxy_host 字段）。
    port : int
        SSH 端口（即实例 ssh_port 字段）。
    password : str
        root 密码（即实例 root_password 字段）。
    connect_timeout : int
        SSH 连接超时秒数，默认 30。

    快速初始化
    ----------
    可以直接从实例详情字典中构建：

    >>> ssh = SSHManager.from_instance(instance_dict)

    示例
    ----
    >>> ssh = SSHManager(host="proxy.autodl.com", port=12345, password="xxx")
    >>> ssh.run_command("nvidia-smi")
    """

    def __init__(self, host: str, port: int, password: str, connect_timeout: int = 30):
        self.host = host
        self.port = port
        self.password = password
        self.connect_timeout = connect_timeout

    @classmethod
    def from_instance(cls, instance: dict, **kwargs) -> "SSHManager":
        """
        从 list_instances() / get_instance() 返回的实例字典直接构建。

        参数
        ----
        instance : dict
            实例详情字典，需包含 proxy_host / ssh_port / root_password 字段。

        示例
        ----
        >>> ssh = SSHManager.from_instance(instance)
        """
        return cls(
            host=instance["proxy_host"],
            port=instance["ssh_port"],
            password=instance["root_password"],
            **kwargs,
        )

    def _connect(self) -> paramiko.SSHClient:
        """建立并返回 SSH 连接"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        log(f"SSH 连接 → {self.host}:{self.port}")
        client.connect(
            hostname=self.host,
            port=self.port,
            username="root",
            password=self.password,
            timeout=self.connect_timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        log("SSH 连接成功")
        return client

    # ══════════════════════════════════════════════════════════
    # 执行命令
    # ══════════════════════════════════════════════════════════

    def run_command(
        self,
        command: str,
        timeout: int = 600,
        use_conda: bool = True,
        raise_on_error: bool = True,
    ) -> int:
        """
        在实例上执行 shell 命令，输出实时打印到本地终端。

        参数
        ----
        command : str
            要执行的 shell 命令，支持多行（用 && 或换行分隔）。
        timeout : int
            命令执行超时秒数，默认 600（10分钟）。
        use_conda : bool
            是否在执行前激活 conda base 环境，默认 True。
            若你的项目使用其他 Python 环境，可设为 False 后手动在命令里 source。
        raise_on_error : bool
            命令返回非零退出码时是否抛出异常，默认 True。

        返回
        ----
        int
            命令退出码，0 表示成功。

        异常
        ----
        RuntimeError
            raise_on_error=True 且退出码非零时抛出。

        示例
        ----
        >>> ssh.run_command("nvidia-smi")
        >>> ssh.run_command("cd /root/project && python train.py")
        >>> ssh.run_command("pip install -r requirements.txt", timeout=300)
        """
        client = self._connect()
        try:
            full_cmd = f"{_CONDA_INIT} && {command}" if use_conda else command
            log(f"执行命令：{command}")

            _, stdout, stderr = client.exec_command(full_cmd, timeout=timeout, get_pty=True)

            for line in stdout:
                clean = re.sub(r'\x1b\[[0-9;]*[mKHJABCDEFGsu]', '', line)
                if clean.strip():
                    print(f"  {clean}", end="", flush=True)

            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                err = stderr.read().decode(errors="ignore").strip()
                msg = f"命令退出码 {exit_code}" + (f"：{err}" if err else "")
                log(f"⚠️  {msg}")
                if raise_on_error:
                    raise RuntimeError(msg)

            return exit_code
        finally:
            client.close()

    # ══════════════════════════════════════════════════════════
    # 上传文件
    # ══════════════════════════════════════════════════════════

    def upload_file(self, local_path: str, remote_path: str):
        """
        上传单个文件到实例。

        参数
        ----
        local_path : str
            本地文件路径。
        remote_path : str
            远程目标路径（含文件名），例："/root/project/main.py"。

        示例
        ----
        >>> ssh.upload_file("./main.py", "/root/project/main.py")
        """
        client = self._connect()
        try:
            sftp = client.open_sftp()
            _sftp_mkdir_p(sftp, os.path.dirname(remote_path))
            sftp.put(local_path, remote_path)
            log(f"✅ 上传：{local_path} → {remote_path}")
            sftp.close()
        finally:
            client.close()

    def upload_dir(
        self,
        local_dir: str,
        remote_dir: str,
        exclude: list[str] = None,
    ):
        """
        将本地目录递归上传到实例。

        参数
        ----
        local_dir : str
            本地目录路径。
        remote_dir : str
            远程目标目录路径，不存在时自动创建。
        exclude : list[str], optional
            要排除的文件/目录名列表，例：["__pycache__", ".git", "*.pyc", "output"]。
            支持精确名称匹配（不支持通配符路径）。

        示例
        ----
        >>> ssh.upload_dir(
        ...     local_dir="./my_project",
        ...     remote_dir="/root/my_project",
        ...     exclude=["__pycache__", ".git", "output", "*.pyc"],
        ... )
        """
        exclude_set = set(exclude or [])
        client = self._connect()
        try:
            sftp = client.open_sftp()
            _sftp_mkdir_p(sftp, remote_dir)

            total, uploaded = 0, 0
            for root, dirs, files in os.walk(local_dir):
                # 过滤排除目录
                dirs[:] = [d for d in dirs if d not in exclude_set]

                rel_root = os.path.relpath(root, local_dir)
                remote_root = remote_dir if rel_root == "." else f"{remote_dir}/{rel_root}"
                _sftp_mkdir_p(sftp, remote_root)

                for fname in files:
                    if fname in exclude_set or any(fname.endswith(e.lstrip("*")) for e in exclude_set if e.startswith("*")):
                        continue
                    local_file  = os.path.join(root, fname)
                    remote_file = f"{remote_root}/{fname}"
                    sftp.put(local_file, remote_file)
                    uploaded += 1
                    log(f"  ↑ {remote_file}")
                total += len(files)

            sftp.close()
            log(f"✅ 目录上传完成：{uploaded} 个文件 → {remote_dir}")
        finally:
            client.close()

    # ══════════════════════════════════════════════════════════
    # 下载文件
    # ══════════════════════════════════════════════════════════

    def download_dir(self, remote_dir: str, local_dir: str):
        """
        将实例上的目录下载到本地（仅下载直接子文件，不递归）。

        参数
        ----
        remote_dir : str
            远程目录路径。
        local_dir : str
            本地保存目录，不存在时自动创建。

        示例
        ----
        >>> ssh.download_dir("/root/project/output", "./output")
        """
        os.makedirs(local_dir, exist_ok=True)
        client = self._connect()
        try:
            sftp = client.open_sftp()
            files = sftp.listdir(remote_dir)
            log(f"发现 {len(files)} 个文件，开始下载...")
            for fname in files:
                remote_path = f"{remote_dir}/{fname}"
                local_path  = os.path.join(local_dir, fname)
                sftp.get(remote_path, local_path)
                log(f"  ✅ {local_path}")
            sftp.close()
        finally:
            client.close()

    def download_file(self, remote_path: str, local_path: str):
        """
        下载单个文件到本地。

        参数
        ----
        remote_path : str
            远程文件路径。
        local_path : str
            本地保存路径。

        示例
        ----
        >>> ssh.download_file("/root/output/result.json", "./result.json")
        """
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        client = self._connect()
        try:
            sftp = client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            log(f"✅ 下载：{remote_path} → {local_path}")
        finally:
            client.close()


# ══════════════════════════════════════════════════════════
# 内部辅助函数
# ══════════════════════════════════════════════════════════

def _sftp_mkdir_p(sftp: paramiko.SFTPClient, remote_dir: str):
    """递归创建远程目录（类似 mkdir -p）"""
    parts = remote_dir.rstrip("/").split("/")
    path = ""
    for part in parts:
        if not part:
            path = "/"
            continue
        path = f"{path}/{part}" if path != "/" else f"/{part}"
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)
