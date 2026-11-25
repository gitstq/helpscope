"""HelpScope 渲染层：把 HelpModel 渲染为三类产物。

1. JSON 清单（manifest）：机器可读、可 diff、可缓存；
2. Agent 工具 Schema：LLM function-calling / tool-use 风格的参数定义；
3. Markdown 用法卡：人类与 Agent 都易读的格式化文档。
"""

from __future__ import annotations

import json
from typing import Any

from .model import HelpModel, Option, Positional, SubCommand

__all__ = ["render_manifest", "render_tool_schema", "render_markdown"]


# ---------------------------------------------------------------- JSON 清单


def render_manifest(model: HelpModel, recursive: bool = True) -> str:
    """渲染 JSON 清单字符串（ensure_ascii=False，按键排序保证确定性）。"""
    data = model.to_dict(recursive=recursive)
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


# ---------------------------------------------------------------- 工具 Schema


def _option_type(opt: Option) -> str:
    if opt.is_flag:
        return "boolean"
    if opt.metavar and opt.metavar.strip("<>[]").lower() in ("n", "num", "count", "level", "int"):
        return "integer"
    return "string"


def render_tool_schema(model: HelpModel) -> dict[str, Any]:
    """生成 function-calling 风格的工具 Schema，可直接投喂给 LLM/Agent。"""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for opt in model.options:
        key = next((f for f in opt.flags if f.startswith("--")), opt.flags[0])
        prop: dict[str, Any] = {
            "type": _option_type(opt),
            "description": opt.help or f"option {key}",
        }
        if opt.metavar:
            prop["arg"] = opt.metavar
        if not opt.is_flag:
            prop["type"] = "string"
        properties[key] = prop

    for pos in model.positionals:
        if pos.name.lower() in ("options", "command"):
            # COMMAND 等泛型位置参数改由 subcommand 枚举表达
            if model.subcommands and pos.name.lower() == "command":
                properties[pos.name] = {
                    "type": "string",
                    "enum": [s.name for s in model.subcommands],
                    "description": pos.help or "subcommand to run",
                }
                if pos.required:
                    required.append(pos.name)
            continue
        properties[pos.name] = {
            "type": "string",
            "description": pos.help or f"positional argument {pos.name}",
        }
        if pos.required:
            required.append(pos.name)

    schema: dict[str, Any] = {
        "name": model.program or "unknown",
        "description": model.description or f"CLI tool {model.program}",
        "parameters": {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        },
    }
    if required:
        schema["parameters"]["required"] = required
    if model.subcommands:
        schema["subcommands"] = {
            s.name: (render_tool_schema(s.model) if s.model else {"description": s.help})
            for s in model.subcommands
        }
    return schema


# ---------------------------------------------------------------- Markdown 用法卡


def _options_table(options: list[Option]) -> str:
    if not options:
        return "_（未解析到选项）_\n"
    rows = ["| 选项 | 参数 | 说明 |", "| --- | --- | --- |"]
    for opt in options:
        flags = " ".join(f"`{f}`" for f in opt.flags)
        arg = f"`{opt.metavar}`" if opt.metavar else "—"
        desc = opt.help or "—"
        rows.append(f"| {flags} | {arg} | {desc} |")
    return "\n".join(rows) + "\n"


def _subcommands_table(subs: list[SubCommand]) -> str:
    if not subs:
        return ""
    rows = ["| 子命令 | 说明 |", "| --- | --- |"]
    for sub in subs:
        extra = " ✅ 已递归解析" if sub.model else ""
        rows.append(f"| `{sub.name}` | {sub.help or '—'}{extra} |")
    return "\n".join(rows) + "\n"


def _positionals_table(positionals: list[Positional]) -> str:
    if not positionals:
        return ""
    rows = ["| 位置参数 | 必填 | 说明 |", "| --- | --- | --- |"]
    for pos in positionals:
        rows.append(
            f"| `{pos.name}` | {'是' if pos.required else '否'} | {pos.help or '—'} |"
        )
    return "\n".join(rows) + "\n"


def render_markdown(model: HelpModel, recursive: bool = False) -> str:
    """渲染 Markdown 用法卡。recursive=True 时附带子命令详情。"""
    out: list[str] = []
    title = model.program or "unknown"
    out.append(f"# 📦 `{title}` 用法卡\n")
    if model.description:
        out.append(f"> {model.description}\n")
    if model.usage_lines:
        out.append("## 🚀 用法\n```text")
        for u in model.usage_lines:
            out.append(f"{title} {u}" if not u.startswith(title) else u)
        out.append("```\n")

    if model.positionals:
        out.append("## 📥 位置参数\n")
        out.append(_positionals_table(model.positionals))
    if model.options:
        out.append("## ⚙️ 选项\n")
        out.append(_options_table(model.options))
    if model.subcommands:
        out.append("## 🧭 子命令\n")
        out.append(_subcommands_table(model.subcommands))
        if recursive:
            for sub in model.subcommands:
                if sub.model:
                    out.append(f"\n### `{sub.name}`\n")
                    out.append(render_markdown(sub.model))
    return "\n".join(out)
