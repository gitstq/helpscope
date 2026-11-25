"""parser 模块单元测试：三种主流帮助格式的解析正确性。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helpscope.parser import parse_help_text, detect_format

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestPipStyle(unittest.TestCase):
    def setUp(self) -> None:
        self.model = parse_help_text(_load("pip_style.txt"), source="file")

    def test_program(self):
        assert self.model.program == "pip"

    def test_format_detected(self):
        assert self.model.format_kind == "subcommands"

    def test_usage(self):
        assert self.model.usage_lines == ["pip <command> [options]"]

    def test_subcommands(self):
        names = [s.name for s in self.model.subcommands]
        assert {"install", "download", "uninstall", "freeze", "list"} <= set(names)
        install = next(s for s in self.model.subcommands if s.name == "install")
        assert "Install packages" in install.help

    def test_options(self):
        help_opt = self.model.find_option("--help")
        assert help_opt is not None
        assert help_opt.is_flag is True
        verbose = self.model.find_option("--verbose")
        assert verbose is not None
        assert verbose.help != ""
        log_opt = self.model.find_option("--log")
        assert log_opt is not None
        assert log_opt.metavar == "path"
        assert log_opt.is_flag is False

    def test_multi_flags(self):
        verbose = self.model.find_option("--verbose")
        assert set(verbose.flags) == {"-v", "--verbose"}


class TestDockerStyle(unittest.TestCase):
    def setUp(self) -> None:
        self.model = parse_help_text(_load("docker_style.txt"), source="file")

    def test_program(self):
        assert self.model.program == "docker"

    def test_description(self):
        assert "self-sufficient runtime" in self.model.description

    def test_options(self):
        debug = self.model.find_option("--debug")
        assert debug is not None
        assert set(debug.flags) == {"-D", "--debug"}
        log_level = self.model.find_option("--log-level")
        assert log_level is not None
        assert log_level.metavar == "string"
        assert log_level.is_flag is False

    def test_subcommands(self):
        names = [s.name for s in self.model.subcommands]
        assert {"container", "image", "network", "volume", "run", "build"} <= set(names)
        run = next(s for s in self.model.subcommands if s.name == "run")
        assert "Create and run" in run.help


class TestGnuStyle(unittest.TestCase):
    def setUp(self) -> None:
        self.model = parse_help_text(_load("gnu_style.txt"), source="file")

    def test_program(self):
        assert self.model.program == "ls"

    def test_usage_positionals(self):
        names = [p.name for p in self.model.positionals]
        assert "FILE" in names

    def test_options(self):
        assert self.model.find_option("--all") is not None
        block_size = self.model.find_option("--block-size")
        assert block_size is not None
        assert block_size.is_flag is False
        human = self.model.find_option("--human-readable")
        assert human is not None
        assert "human readable" in human.help

    def test_option_without_short(self):
        author = self.model.find_option("--author")
        assert author is not None
        assert author.flags == ["--author"]


class TestHelpers(unittest.TestCase):
    def test_detect_format(self):
        assert detect_format(_load("pip_style.txt")) == "subcommands"
        assert detect_format(_load("gnu_style.txt")) == "gnu"

    def test_empty_input(self):
        model = parse_help_text("")
        assert model.program == ""
        assert model.options == []

    def test_stats(self):
        model = parse_help_text(_load("docker_style.txt"))
        stats = model.stats()
        assert stats["subcommands"] >= 8
        assert stats["options"] >= 5

    def test_model_roundtrip_dict(self):
        import json

        model = parse_help_text(_load("pip_style.txt"))
        data = model.to_dict(recursive=True)
        dumped = json.dumps(data, ensure_ascii=False)
        assert json.loads(dumped)["program"] == "pip"
