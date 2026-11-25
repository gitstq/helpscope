"""HelpScope 安全捕获引擎：运行 ``prog --help`` 并解析，全程无 shell、有超时。

安全边界：
- 永不经过 shell（``shell=False``），无注入面；
- 统一超时上限（默认 10s）并 kill 超时进程；
- 依次尝试 ``--help`` / ``-h`` / ``-help`` / ``help``，任一产出含 usage 特征的
  输出即视为成功；
- 支持纯离线模式：直接解析文本文件，不运行任何程序。
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional

from .model import HelpModel
from .parser import parse_help_text

__all__ = ["capture_help", "looks_like_help"]

HELP_ARG_CANDIDATES = ("--help", "-h", "-help", "help")
DEFAULT_TIMEOUT = 10.0

_USAGE_MARKERS = ("usage", "usage:", "options:", "commands:", "用法")


def looks_like_help(text: str) -> bool:
    """启发式判断一段输出是否像帮助文本。"""
    if not text or len(text.strip()) < 12:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in _USAGE_MARKERS) or (
        "-" in text and len(text.splitlines()) >= 4
    )


def capture_help(
    prog: str,
    timeout: float = DEFAULT_TIMEOUT,
    cwd: Optional[str] = None,
    source: str = "capture",
) -> tuple[HelpModel, str]:
    """运行 ``prog --help`` 并返回 (HelpModel, 使用的参数)。

    Raises:
        FileNotFoundError: 程序不在 PATH 中；
        RuntimeError: 所有候选参数均未能产出可用帮助文本。
    """
    resolved = shutil.which(prog)
    if resolved is None:
        raise FileNotFoundError(f"program not found in PATH: {prog!r}")

    best_text = ""
    best_arg = ""
    for arg in HELP_ARG_CANDIDATES:
        try:
            proc = subprocess.run(
                [resolved, arg],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            continue
        text = proc.stdout if looks_like_help(proc.stdout) else ""
        if not text and looks_like_help(proc.stderr):
            text = proc.stderr
        if text and (not best_text or len(text) > len(best_text)):
            best_text = text
            best_arg = arg
        if text and "usage" in text.lower():
            break

    if not best_text:
        raise RuntimeError(
            f"no usable help output captured from {prog!r} "
            f"(tried {', '.join(HELP_ARG_CANDIDATES)})"
        )
    model = parse_help_text(best_text, source=source)
    if not model.program:
        model.program = prog
    return model, best_arg


def capture_subcommands(
    prog: str,
    model: HelpModel,
    timeout: float = DEFAULT_TIMEOUT,
    cwd: Optional[str] = None,
    depth: int = 1,
) -> int:
    """递归捕获子命令的帮助文本并挂载到模型上，返回成功数量。"""
    if depth <= 0:
        return 0
    resolved = shutil.which(prog)
    if resolved is None:
        return 0
    ok = 0
    for sub in model.subcommands:
        best_text = ""
        for arg in HELP_ARG_CANDIDATES:
            try:
                proc = subprocess.run(
                    [resolved, sub.name, arg],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=cwd,
                    shell=False,
                    check=False,
                )
            except (subprocess.TimeoutExpired, OSError):
                continue
            text = proc.stdout if looks_like_help(proc.stdout) else ""
            if not text and looks_like_help(proc.stderr):
                text = proc.stderr
            if text and (not best_text or len(text) > len(best_text)):
                best_text = text
        if best_text:
            sub.model = parse_help_text(best_text, source="capture")
            if not sub.model.program:
                sub.model.program = f"{prog} {sub.name}"
            ok += 1
            if depth > 1:
                ok += capture_subcommands(
                    prog, sub.model, timeout=timeout, cwd=cwd, depth=depth - 1
                )
    return ok
