"""
autodl-sdk — AutoDL GPU 云平台 Python 自动化 SDK

快速开始
--------
>>> from autodl import AutoDLClient, InstanceManager, SSHManager
>>> from autodl import IMAGE_TYPE_BASE, IMAGE_TYPE_COMMUNITY, IMAGE_TYPE_PRIVATE

>>> client = AutoDLClient(token="your_autodl_token")
>>> mgr    = InstanceManager(client)

>>> # 查余额
>>> print(mgr.get_balance())

>>> # 查实例列表
>>> instances = mgr.list_instances()
"""

from .client import AutoDLClient
from .instance import InstanceManager, IMAGE_TYPE_BASE, IMAGE_TYPE_COMMUNITY, IMAGE_TYPE_PRIVATE
from .ssh import SSHManager
from .utils import log, Timer

__version__ = "1.0.0"
__author__  = "autodl-sdk contributors"

__all__ = [
    "AutoDLClient",
    "InstanceManager",
    "SSHManager",
    "IMAGE_TYPE_BASE",
    "IMAGE_TYPE_COMMUNITY",
    "IMAGE_TYPE_PRIVATE",
    "log",
    "Timer",
]
