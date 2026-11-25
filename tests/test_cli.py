"""CLI 端到端测试：capture / parse / report 三命令、三种输出格式。"""

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from helpscope.cli import main

FIXTURES = ROOT / "tests" / "fixtures"


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    """运行 CLI，返回 (exit_code, stdout, stderr)。"""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


class TestParseCommand(unittest.TestCase):
    def test_parse_json_stdout(self):
        rc, out, _ = _run_cli(["parse", str(FIXTURES / "docker_style.txt"), "--format", "json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["program"], "docker")

    def test_parse_md(self):
        rc, out, _ = _run_cli(["parse", str(FIXTURES / "pip_style.txt"), "--format", "md"])
        self.assertEqual(rc, 0)
        self.assertIn("用法卡", out)
        self.assertIn("`install`", out)

    def test_parse_schema_to_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "schema.json"
            rc, _, _ = _run_cli(
                ["parse", str(FIXTURES / "gnu_style.txt"), "--format", "schema", "-o", str(out_file)]
            )
            self.assertEqual(rc, 0)
            schema = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(schema["name"], "ls")
            self.assertIn("--all", schema["parameters"]["properties"])

    def test_parse_missing_file(self):
        rc, _, err = _run_cli(["parse", "/no/such/file.txt"])
        self.assertEqual(rc, 2)


class TestReportCommand(unittest.TestCase):
    def test_report_ok(self):
        rc, out, _ = _run_cli(["report", str(FIXTURES / "pip_style.txt")])
        self.assertEqual(rc, 0)
        self.assertIn("共", out)

    def test_report_json_exit_code(self):
        bad = FIXTURES / "no_usage.txt"
        bad.write_text("random text\nno usage here\n", encoding="utf-8")
        rc, out, _ = _run_cli(["report", str(bad), "--json"])
        self.assertEqual(rc, 1)
        findings = json.loads(out)
        self.assertTrue(any(f["rule_id"] == "HS001" for f in findings))
        bad.unlink()


class TestCaptureCommand(unittest.TestCase):
    def test_capture_self(self):
        """捕获 python 自身的帮助（离线安全、无 shell）。"""
        rc, out, _ = _run_cli(["capture", sys.executable, "--format", "json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["options"])

    def test_capture_missing(self):
        rc, _, _ = _run_cli(["capture", "definitely-not-a-real-program-xyz"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
