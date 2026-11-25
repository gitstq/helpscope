"""HelpScope data model: structured representation of CLI help text.

所有核心实体均为纯数据类（dataclass），可无损序列化为 JSON，
保证解析结果确定、可 diff、可缓存。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["Option", "Positional", "SubCommand", "HelpModel"]


@dataclass
class Option:
    """一个命令行选项，如 ``-o, --output FILE``。"""

    flags: list[str] = field(default_factory=list)
    metavar: Optional[str] = None
    help: str = ""
    is_flag: bool = True  # True 表示不接收参数

    def to_dict(self) -> dict[str, Any]:
        return {
            "flags": list(self.flags),
            "metavar": self.metavar,
            "help": self.help,
            "is_flag": self.is_flag,
        }


@dataclass
class Positional:
    """一个位置参数，如 ``usage: prog FILE...`` 中的 ``FILE...``。"""

    name: str = ""
    help: str = ""
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "help": self.help, "required": self.required}


@dataclass
class SubCommand:
    """一个子命令；递归解析后附带其自身的 HelpModel。"""

    name: str = ""
    help: str = ""
    model: Optional["HelpModel"] = None

    def to_dict(self, recursive: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "help": self.help}
        if recursive and self.model is not None:
            out["model"] = self.model.to_dict()
        return out


@dataclass
class HelpModel:
    """一份 CLI 帮助文本的完整结构化模型。"""

    program: str = ""
    usage_lines: list[str] = field(default_factory=list)
    description: str = ""
    options: list[Option] = field(default_factory=list)
    positionals: list[Positional] = field(default_factory=list)
    subcommands: list[SubCommand] = field(default_factory=list)
    source: str = ""  # "capture" / "file" / "text"
    format_kind: str = "unknown"  # 检测到的帮助格式：argparse / gnu / subcommands / unknown

    def to_dict(self, recursive: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "program": self.program,
            "usage": list(self.usage_lines),
            "description": self.description,
            "options": [o.to_dict() for o in self.options],
            "positionals": [p.to_dict() for p in self.positionals],
            "subcommands": [s.to_dict(recursive=False) for s in self.subcommands],
            "source": self.source,
            "format_kind": self.format_kind,
        }
        if recursive:
            out["subcommands"] = [
                s.to_dict(recursive=True) for s in self.subcommands
            ]
        return out

    def find_option(self, flag: str) -> Optional[Option]:
        """按 flag（含短选项）查找选项定义。"""
        for opt in self.options:
            if flag in opt.flags:
                return opt
        return None

    def stats(self) -> dict[str, int]:
        return {
            "options": len(self.options),
            "positionals": len(self.positionals),
            "subcommands": len(self.subcommands),
        }
