"""
autodl/client.py — AutoDL HTTP 客户端基础封装

所有 API 请求统一走这里，负责：
- 请求头注入（Authorization / AppVersion）
- 统一错误处理
- GET / POST 封装
"""

import requests


BASE_URL = "https://www.autodl.com/api/v1"
_DEFAULT_APP_VERSION = "v6.32.0"
_DEFAULT_TIMEOUT = 20


class AutoDLClient:
    """
    AutoDL API 客户端。

    参数
    ----
    token : str
        从浏览器抓包获取的 JWT Token（请求头 Authorization 字段的值）。
    timeout : int
        HTTP 请求超时秒数，默认 20。

    示例
    ----
    >>> from autodl.client import AutoDLClient
    >>> client = AutoDLClient(token="your_token_here")
    """

    def __init__(self, token: str, timeout: int = _DEFAULT_TIMEOUT):
        if not token:
            raise ValueError("token 不能为空，请从浏览器抓包获取 Authorization 字段的值")
        self.token = token
        self.timeout = timeout
        self._headers = {
            "Authorization": token,
            "AppVersion": _DEFAULT_APP_VERSION,
            "Content-Type": "application/json;charset=utf-8",
        }

    def post(self, path: str, body: dict) -> dict:
        """
        发送 POST 请求并返回 data 字段内容。

        参数
        ----
        path : str
            API 路径，如 "/instance"。
        body : dict
            请求体。

        返回
        ----
        dict
            API 响应中的 data 字段。

        异常
        ----
        RuntimeError
            当 API 返回 code != "Success" 时抛出，包含错误信息。
        """
        url = f"{BASE_URL}{path}"
        resp = requests.post(url, headers=self._headers, json=body, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(path, resp.json())

    def get(self, path: str, params: dict = None) -> dict:
        """
        发送 GET 请求并返回 data 字段内容。

        参数
        ----
        path : str
            API 路径。
        params : dict, optional
            Query 参数。

        返回
        ----
        dict
            API 响应中的 data 字段。
        """
        url = f"{BASE_URL}{path}"
        resp = requests.get(url, headers=self._headers, params=params or {}, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(path, resp.json())

    @staticmethod
    def _parse(path: str, data: dict) -> dict:
        if data.get("code") != "Success":
            raise RuntimeError(f"API {path} 返回错误：{data.get('msg') or data}")
        return data.get("data", {})
