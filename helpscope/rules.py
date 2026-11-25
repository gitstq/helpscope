"""HelpScope 规则体检：对解析结果做 lint，输出确定性发现列表（CI 门禁就绪）。

规则编号前缀 ``HS``，严重级：``error`` / ``warning`` / ``info``。
任何 ``error`` 级发现都会让 CLI 以非零码退出，可直接用于 CI 卡口。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .model import HelpModel

__all__ = ["Finding", "lint_model", "has_errors"]

TOTAL_RULES = 6  # 当前内置规则数量


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str  # "error" | "warning" | "info"
    message: str
    scope: str = ""  # 命令路径，如 "docker run"

    def to_dict(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "scope": self.scope,
        }


def _lint_single(model: HelpModel, scope: str) -> list[Finding]:
    findings: list[Finding] = []

    # HS001: 缺少 usage 行（error）
    if not model.usage_lines:
        findings.append(
            Finding(
                "HS001",
                "error",
                "帮助文本中未找到 usage 行，Agent 无法确定调用形态",
                scope,
            )
        )

    # HS002: 选项缺少说明（warning）
    for opt in model.options:
        if not opt.help.strip():
            findings.append(
                Finding(
                    "HS002",
                    "warning",
                    f"选项 {'/'.join(opt.flags)} 缺少说明",
                    scope,
                )
            )

    # HS003: 重复 flag 定义（error）
    seen: dict[str, str] = {}
    for opt in model.options:
        for flag in opt.flags:
            if flag in seen:
                findings.append(
                    Finding(
                        "HS003",
                        "error",
                        f"flag {flag} 被重复定义（{seen[flag]} 与 {'/'.join(opt.flags)}）",
                        scope,
                    )
                )
            else:
                seen[flag] = "/".join(opt.flags)

    # HS004: 子命令缺少说明（warning）
    for sub in model.subcommands:
        if not sub.help.strip():
            findings.append(
                Finding("HS004", "warning", f"子命令 {sub.name} 缺少说明", scope)
            )

    # HS005: 未解析到任何选项（info）
    if not model.options:
        findings.append(
            Finding(
                "HS005",
                "info",
                "未解析到任何选项，帮助文本可能为非标准格式",
                scope,
            )
        )

    # HS006: 位置参数缺少说明（info）
    for pos in model.positionals:
        if not pos.help.strip() and pos.name.lower() not in ("command", "options"):
            findings.append(
                Finding("HS006", "info", f"位置参数 {pos.name} 缺少说明", scope)
            )

    return findings


def _path_contains_variants(path: str) -> bool:
    return bool(re.search(r"\{[^}]*\}", path))


def lint_model(model: HelpModel) -> list[Finding]:
    """递归体检整个模型树（含子命令），按规则 ID 排序保证确定性。"""
    all_findings: list[Finding] = []
    _walk(model, scope=model.program, findings=all_findings)
    all_findings.sort(key=lambda f: (f.rule_id, f.scope))
    return all_findings


def _walk(model: HelpModel, scope: str, findings: list[Finding], depth: int = 0) -> None:
    if depth > 3:
        return
    findings.extend(_lint_single(model, scope))
    for sub in model.subcommands:
        if sub.model is not None:
            _walk(sub.model, f"{scope} {sub.name}".strip(), findings, depth + 1)


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity == "error" for f in findings)
