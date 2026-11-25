"""HelpScope 核心解析器：把任意 CLI 的 --help 文本解析为结构化 HelpModel。

采用「分段 + 逐行启发式」策略，兼容三类主流帮助格式：
1. argparse 风格（pip / python）：``positional arguments:`` / ``options:`` 段落；
2. GNU 风格（ls / grep）：``Usage:`` + 缩进选项列表（无段落标题）；
3. 子命令风格（docker / git / pip）：``Commands:`` 段落 + ``name  desc`` 行。

设计原则：纯函数、无副作用、不执行任何外部程序；确定性输出。
"""

from __future__ import annotations

import re
from typing import Optional

from .model import HelpModel, Option, Positional, SubCommand

__all__ = ["parse_help_text", "detect_format"]

# ---------------------------------------------------------------- 常量与正则

USAGE_RE = re.compile(r"^\s{0,6}(?:usage|用法)\s*:\s*(.*)$", re.IGNORECASE)
USAGE_ALT_RE = re.compile(r"^\s{0,6}(?:or|或)\s*:\s*(.*)$", re.IGNORECASE)

# 已知的「子命令段落」标题关键词
SUBCOMMAND_SECTION_WORDS = (
    "commands",
    "subcommands",
    "available commands",
    "common commands",
    "management commands",
)

# 已知的「选项段落」标题关键词
OPTION_SECTION_WORDS = (
    "options",
    "optional arguments",
    "optional",
    "general options",
    "named arguments",
    "flags",
)

# 位置参数段落
POSITIONAL_SECTION_WORDS = ("positional arguments", "arguments", "positional")

# 形如 -D / --debug / -o 的 flag token（允许 --opt=VALUE 形式与罕见的 . ? + 结尾）
FLAG_RE = re.compile(r"^-{1,2}[A-Za-z0-9][\w.?+-]*(?:=[^\s]+)?$|^-$")

# metavar 候选：<FILE> / FILE / SIZE... / [N]
METAVAR_RE = re.compile(r"^(?:<[^>]+>|\[?[A-Z][A-Z0-9_]*\.\.\.?]?)$")

GENERIC_USAGE_NAMES = ("options", "option", "flags")

HELP_STYLE_OPTIONS = ("--help", "-h", "-help", "help")


def detect_format(text: str) -> str:
    """粗略检测帮助文本风格，用于结果标注与规则体检。"""
    lowered = text.lower()
    if "usage:" in lowered or "用法:" in lowered:
        if "commands:" in lowered or "subcommands:" in lowered:
            return "subcommands"
        if "options:" in lowered or "optional arguments:" in lowered:
            return "argparse"
        return "gnu"
    return "unknown"


# ---------------------------------------------------------------- 小工具函数


def _split_left_desc(stripped: str) -> tuple[str, str]:
    """把一个条目行（已 strip）拆成 (左半段, 描述)。分隔符为第一个 >=2 连续空格。"""
    m = re.search(r"\s{2,}", stripped)
    if m and m.start() > 0:
        return stripped[: m.start()].strip(), stripped[m.end() :].strip()
    return stripped, ""


def _parse_left_tokens(left: str) -> tuple[list[str], Optional[str], bool]:
    """解析左半段 → (flags 列表, metavar, is_flag)。"""
    tokens = [t for t in re.split(r",\s*|\s+", left) if t]
    flags: list[str] = []
    metavar: Optional[str] = None
    for tok in tokens:
        if "=" in tok and FLAG_RE.match(tok.split("=", 1)[0]):
            flags.append(tok.split("=", 1)[0])
            metavar = tok.split("=", 1)[1].strip("<>[]") or tok.split("=", 1)[1]
        elif FLAG_RE.match(tok):
            flags.append(tok)
        else:
            cand = tok.strip("<>[]")
            if METAVAR_RE.match(tok) or tok.startswith("<"):
                metavar = cand if cand else tok
            elif metavar is None:
                metavar = tok
    is_flag = metavar is None and len(tokens) == len(flags)
    return flags, metavar, is_flag


def _looks_like_section_header(line: str) -> Optional[str]:
    """判断一行是否为段落标题，返回标题小写文本或 None。"""
    stripped = line.rstrip()
    if not stripped.endswith(":"):
        return None
    if len(stripped) > 72:
        return None
    # 标题行不含选项/占位符特征
    if re.search(r"(?<![\w.])-{1,2}[A-Za-z]|<|\.\.\.|\{", stripped):
        return None
    return stripped.rstrip(":").strip().lower()


def _classify_header(header: str) -> str:
    for w in POSITIONAL_SECTION_WORDS:
        if header == w or header.startswith(w):
            return "positionals"
    for w in SUBCOMMAND_SECTION_WORDS:
        if header == w or header.startswith(w):
            return "subcommands"
    for w in OPTION_SECTION_WORDS:
        if header == w or header.startswith(w):
            return "options"
    if header.endswith("options"):
        return "options"
    return "other"


def _extract_program(first_usage: str) -> str:
    first = first_usage.strip().split()
    if first:
        return first[0].strip("[]()")
    return ""


def _extract_positionals_from_usage(usage_lines: list[str]) -> list[Positional]:
    """从 usage 行提取位置参数（不重复、保持顺序）。"""
    seen: list[Positional] = []
    for line in usage_lines:
        parts = line.strip().split(" ", 1)
        rest = parts[1] if len(parts) > 1 else ""
        for tok in re.split(r"\s+", rest):
            tok = tok.strip()
            if not tok or tok.startswith("-"):
                continue
            name = re.sub(r"[\[\]()<>]", "", tok).rstrip(".")
            if not name:
                continue
            if name.lower() in GENERIC_USAGE_NAMES:
                continue
            if not re.match(r"^[A-Za-z][\w.-]*$", name):
                continue
            optional = tok.startswith("[")
            if not any(p.name == name for p in seen):
                seen.append(Positional(name=name, help="", required=not optional))
    return seen


# ---------------------------------------------------------------- 主解析函数


def parse_help_text(text: str, source: str = "text") -> HelpModel:
    """把帮助文本解析为 :class:`HelpModel`。不执行任何外部命令。"""
    model = HelpModel(source=source, format_kind=detect_format(text))
    lines = text.splitlines()

    section = "pre"  # pre / usage / post / options / positionals / subcommands / other
    current_item: Optional[object] = None
    current_indent = 0
    pre_desc: list[str] = []   # usage 之前的描述正文
    post_desc: list[str] = []  # usage 之后、第一个条目之前的描述正文
    seen_item = False

    for raw in lines:
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())

        # ---- usage 行 ----
        m = USAGE_RE.match(raw)
        if m:
            model.usage_lines.append(m.group(1).strip())
            model.program = model.program or _extract_program(m.group(1))
            section = "usage"
            current_item = None
            continue
        if section == "usage":
            m2 = USAGE_ALT_RE.match(raw)
            if m2:
                model.usage_lines.append(m2.group(1).strip())
                continue
            section = "post"  # usage 之后的第一条非 usage 行

        # ---- 段落标题 ----
        header = _looks_like_section_header(raw)
        if header is not None:
            section = _classify_header(header)
            current_item = None
            continue

        # ---- 空行 ----
        if not stripped:
            current_item = None
            continue

        # ---- 条目行解析 ----
        left, desc = _split_left_desc(stripped)
        parts = left.split()
        first_tok = parts[0].rstrip(",") if parts else ""
        is_option_line = first_tok.startswith("-") and bool(FLAG_RE.match(first_tok))
        word_item = (
            not first_tok.startswith("-")
            and 1 <= len(parts) <= 4
            and desc != ""
        )

        handled = False
        # 已知段落内允许 0 缩进条目（如 python -h）；未知段落要求缩进 ≥1
        if indent >= 1 or section in ("options", "subcommands", "positionals"):
            if is_option_line and section in ("pre", "post", "options"):
                flags, metavar, is_flag = _parse_left_tokens(left)
                if flags:
                    opt = Option(flags=flags, metavar=metavar, help=desc, is_flag=is_flag)
                    model.options.append(opt)
                    current_item, current_indent, seen_item = opt, indent, True
                    handled = True
            elif section == "subcommands" and word_item:
                sub = SubCommand(name=first_tok, help=desc)
                model.subcommands.append(sub)
                current_item, current_indent, seen_item = sub, indent, True
                handled = True
            elif section == "positionals" and word_item and not first_tok.startswith("-"):
                pos = Positional(
                    name=first_tok, help=desc, required=not left.startswith("[")
                )
                model.positionals.append(pos)
                current_item, current_indent, seen_item = pos, indent, True
                handled = True

        if handled:
            continue

        # ---- 续行：缩进更深且不是新条目 → 追加到上一条目的描述 ----
        if (
            current_item is not None
            and indent > current_indent
            and not is_option_line
            and not word_item
        ):
            extra = desc if desc else stripped
            current_item.help = (current_item.help + " " + extra).strip()  # type: ignore[attr-defined]
            continue

        # ---- 描述正文 ----
        if section == "pre":
            pre_desc.append(stripped)
        elif section == "post" and not seen_item and not is_option_line:
            post_desc.append(stripped)
        # 其余（条目之后的零散文本）忽略，保证输出确定性

    model.description = " ".join(pre_desc).strip() or " ".join(post_desc).strip()
    if not model.positionals:
        model.positionals = _extract_positionals_from_usage(model.usage_lines)
    return model
