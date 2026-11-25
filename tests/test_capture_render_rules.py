"""capture / render / rules 模块单元测试。"""

import json
import subprocess
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helpscope.capture import capture_help, looks_like_help
from helpscope.render import render_manifest, render_markdown, render_tool_schema
from helpscope.parser import parse_help_text
from helpscope.rules import Finding, lint_model, has_errors

FIXTURES = Path(__file__).parent / "fixtures"


class TestCapture(unittest.TestCase):
    def test_capture_python_help(self):
        # 用 python 自身做安全捕获测试目标（无 shell、带超时）
        model, used = capture_help(sys.executable, timeout=20)
        assert model.program != ""
        assert model.usage_lines
        assert model.options, "python -h 应解析出选项"
        assert used in ("--help", "-h", "-help", "help")

    def test_capture_missing_prog(self):
        with self.assertRaises(FileNotFoundError):
            capture_help("definitely-not-a-real-program-xyz")

    def test_looks_like_help(self):
        assert looks_like_help("usage: prog [options]\n  -a  all")
        assert not looks_like_help("")
        assert not looks_like_help("ok")


class TestRender(unittest.TestCase):
    def setUp(self) -> None:
        self.model = parse_help_text(
            (FIXTURES / "docker_style.txt").read_text(encoding="utf-8"), source="file"
        )

    def test_manifest_json(self):
        raw = render_manifest(self.model, recursive=False)
        data = json.loads(raw)
        assert data["program"] == "docker"
        assert len(data["options"]) >= 5
        # 确定性：两次渲染结果一致
        assert raw == render_manifest(self.model, recursive=False)

    def test_tool_schema(self):
        schema = render_tool_schema(self.model)
        assert schema["name"] == "docker"
        props = schema["parameters"]["properties"]
        assert "--debug" in props
        assert props["--debug"]["type"] == "boolean"
        assert "--log-level" in props
        assert props["--log-level"]["type"] == "string"
        assert "run" in schema["subcommands"]

    def test_markdown(self):
        md = render_markdown(self.model)
        assert "# 📦 `docker` 用法卡" in md
        assert "## ⚙️ 选项" in md
        assert "## 🧭 子命令" in md
        assert "`run`" in md


class TestRules(unittest.TestCase):
    def test_clean_fixture_few_errors(self):
        model = parse_help_text(
            (FIXTURES / "pip_style.txt").read_text(encoding="utf-8"), source="file"
        )
        findings = lint_model(model)
        # pip 夹具应有 usage 行且大部分条目有描述 → 不应出现 HS001
        assert not any(f.rule_id == "HS001" for f in findings)

    def test_missing_usage_is_error(self):
        model = parse_help_text("just some text\nwithout usage line", source="file")
        findings = lint_model(model)
        assert has_errors(findings)
        assert any(f.rule_id == "HS001" for f in findings)

    def test_duplicate_flag(self):
        text = (
            "usage: prog [options]\n"
            "Options:\n"
            "  -v, --verbose    Verbose mode.\n"
            "  -v, --vocal      Also verbose.\n"
        )
        model = parse_help_text(text, source="file")
        findings = lint_model(model)
        assert any(f.rule_id == "HS003" for f in findings)

    def test_finding_dict(self):
        f = Finding("HS001", "error", "msg", "scope")
        assert f.to_dict() == {
            "rule_id": "HS001",
            "severity": "error",
            "message": "msg",
            "scope": "scope",
        }
