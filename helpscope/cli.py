"""HelpScope 命令行入口。

三个子命令：
- ``capture``：运行 ``PROG --help`` 捕获并解析（可选递归子命令）；
- ``parse``：纯离线解析帮助文本文件；
- ``report``：对解析结果做规则体检（CI 门禁）。

输出格式：``json``（清单）/ ``schema``（Agent 工具定义）/ ``md``（用法卡）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .capture import DEFAULT_TIMEOUT, capture_help, capture_subcommands
from .parser import parse_help_text
from .render import render_manifest, render_markdown, render_tool_schema
from .rules import Finding, lint_model

__all__ = ["main", "build_parser"]


def _emit(content: str, out_path: str | None) -> int:
    if out_path:
        Path(out_path).write_text(content, encoding="utf-8")
        print(f"✅ written: {out_path}", file=sys.stderr)
    else:
        sys.stdout.write(content.rstrip() + "\n")
    return 0


def _report(findings: list[Finding], out_path: str | None, fmt: str) -> int:
    import json

    lines: list[str] = []
    if fmt == "json":
        payload = json.dumps(
            [f.to_dict() for f in findings], ensure_ascii=False, indent=2
        )
        lines.append(payload)
    else:
        for f in findings:
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[f.severity]
            scope = f" [{f.scope}]" if f.scope else ""
            lines.append(f"{icon} {f.rule_id}{scope} {f.severity}: {f.message}")
        errors = sum(1 for f in findings if f.severity == "error")
        warnings = sum(1 for f in findings if f.severity == "warning")
        infos = sum(1 for f in findings if f.severity == "info")
        lines.append("")
        lines.append(f"共 {len(findings)} 条发现：❌ {errors} · ⚠️ {warnings} · ℹ️ {infos}")
    text = "\n".join(lines)
    return _emit(text, out_path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="helpscope",
        description=(
            "HelpScope — 零依赖·离线优先的 CLI 帮助文本解析引擎："
            "把 --help 变成 JSON 清单、Agent 工具 Schema 与 Markdown 用法卡"
        ),
    )
    p.add_argument("--version", action="version", version=f"helpscope {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # capture
    cap = sub.add_parser(
        "capture", help="运行 PROG --help 捕获并解析（安全、无 shell、带超时）"
    )
    cap.add_argument("prog", help="目标程序名（须在 PATH 中）")
    cap.add_argument(
        "--recurse", action="store_true", help="递归捕获一层子命令的帮助文本"
    )
    cap.add_argument("--depth", type=int, default=1, help="递归深度（默认 1）")
    cap.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT, help="单次捕获超时秒数"
    )
    _add_output_args(cap)

    # parse
    par = sub.add_parser("parse", help="纯离线解析帮助文本文件（不运行任何程序）")
    par.add_argument("file", help="包含帮助文本的文件路径（UTF-8）")
    _add_output_args(par)

    # report
    rep = sub.add_parser("report", help="对帮助文本做规则体检（HS 规则，CI 门禁）")
    rep.add_argument("file", help="包含帮助文本的文件路径（UTF-8）")
    rep.add_argument(
        "--json", action="store_true", help="以 JSON 格式输出发现列表"
    )
    rep.add_argument("-o", "--out", default=None, help="写入文件而非 stdout")
    return p


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("json", "schema", "md"),
        default="json",
        help="输出格式：json 清单 / schema 工具定义 / md 用法卡（默认 json）",
    )
    parser.add_argument("-o", "--out", default=None, help="写入文件而非 stdout")
    parser.add_argument(
        "--no-recurse-render", action="store_true", help="md/json 输出不附带子命令详情"
    )


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    recursive_render = not ns.__dict__.get("no_recurse_render", False)

    if ns.command == "capture":
        try:
            model, used = capture_help(ns.prog, timeout=ns.timeout)
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"❌ {exc}", file=sys.stderr)
            return 2
        if ns.recurse:
            n = capture_subcommands(ns.prog, model, timeout=ns.timeout, depth=ns.depth)
            print(f"ℹ️ 递归捕获子命令: {n} 个（触发参数: {used}）", file=sys.stderr)
        else:
            print(f"ℹ️ 触发参数: {used}", file=sys.stderr)

        if ns.format == "json":
            return _emit(render_manifest(model, recursive=recursive_render), ns.out)
        if ns.format == "schema":
            import json

            return _emit(
                json.dumps(render_tool_schema(model), ensure_ascii=False, indent=2),
                ns.out,
            )
        return _emit(render_markdown(model, recursive=recursive_render), ns.out)

    if ns.command == "parse":
        path = Path(ns.file)
        if not path.exists():
            print(f"❌ 文件不存在: {ns.file}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")
        model = parse_help_text(text, source="file")
        if ns.format == "json":
            return _emit(render_manifest(model, recursive=recursive_render), ns.out)
        if ns.format == "schema":
            import json

            return _emit(
                json.dumps(render_tool_schema(model), ensure_ascii=False, indent=2),
                ns.out,
            )
        return _emit(render_markdown(model, recursive=recursive_render), ns.out)

    if ns.command == "report":
        path = Path(ns.file)
        if not path.exists():
            print(f"❌ 文件不存在: {ns.file}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")
        model = parse_help_text(text, source="file")
        findings = lint_model(model)
        exit_code = 1 if any(f.severity == "error" for f in findings) else 0
        _report(findings, ns.out, "json" if ns.json else "text")
        return exit_code

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
