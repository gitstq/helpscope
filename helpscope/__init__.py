"""HelpScope — 零依赖 · 离线优先的 CLI 帮助文本解析引擎。

把任意命令行工具的 ``--help`` 输出变成：
- 结构化 JSON 清单（可 diff、可缓存）
- LLM/Agent function-calling 工具 Schema
- Markdown 用法卡

纯 Python 标准库实现，Python 3.9+，无任何第三方依赖。
"""

from .model import HelpModel, Option, Positional, SubCommand
from .parser import detect_format, parse_help_text
from .capture import capture_help, capture_subcommands, looks_like_help
from .render import render_manifest, render_markdown, render_tool_schema
from .rules import Finding, has_errors, lint_model

__version__ = "1.0.0"

__all__ = [
    "HelpModel",
    "Option",
    "Positional",
    "SubCommand",
    "parse_help_text",
    "detect_format",
    "capture_help",
    "capture_subcommands",
    "looks_like_help",
    "render_manifest",
    "render_markdown",
    "render_tool_schema",
    "Finding",
    "lint_model",
    "has_errors",
    "__version__",
]
