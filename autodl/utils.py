"""
autodl/utils.py — 通用工具函数
"""

import datetime
import time


def log(msg: str):
    """带时间戳的日志输出"""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def safe_float(v) -> float:
    """安全类型转换，转换失败返回 0.0"""
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


class Timer:
    """
    简单的多步骤计时器，用于统计各步骤和总耗时。

    示例
    ----
    >>> timer = Timer()
    >>> timer.begin("上传代码")
    >>> # ... 执行操作 ...
    >>> timer.end("上传代码")
    >>> timer.summary()
    """

    def __init__(self):
        self._steps: list[tuple[str, float]] = []
        self._start: dict[str, float] = {}
        self._pipeline_start = time.time()

    def begin(self, name: str):
        """开始计时某步骤"""
        self._start[name] = time.time()

    def end(self, name: str) -> float:
        """结束计时，返回该步骤耗时（秒）"""
        elapsed = time.time() - self._start.pop(name, time.time())
        self._steps.append((name, elapsed))
        return elapsed

    def summary(self):
        """打印所有步骤的耗时汇总"""
        total = time.time() - self._pipeline_start
        print("\n" + "═" * 50)
        print("  ⏱  耗时统计")
        print("═" * 50)
        for name, secs in self._steps:
            mm, ss = divmod(int(secs), 60)
            print(f"  {name:<22} {mm:>3}m {ss:02d}s")
        print("  " + "─" * 36)
        mm, ss = divmod(int(total), 60)
        print(f"  {'总耗时':<22} {mm:>3}m {ss:02d}s")
        print("═" * 50)
