<p align="center"><a href="README.md">简体中文</a> | <a href="README.zh-TW.md">繁體中文</a> | <b>English</b></p>

# 🎉 Introduction

**HelpScope** is a zero-dependency, offline-first CLI help-text parsing engine. It turns any command-line tool's `--help` output into three ready-to-use artifacts:

1. **Structured JSON manifest** — diffable, cacheable, CI-friendly;
2. **Agent tool schema** — LLM function-calling / tool-use style parameter definitions that let any CLI plug natively into AI agents;
3. **Markdown usage card** — formatted documentation readable by humans and agents alike.

Pure Python standard library (Python 3.9+), zero third-party dependencies. The core parser never executes external commands; the capture engine runs without a shell and with a hard timeout, making it safe for automation pipelines.

> Inspired by the product philosophy of the trending project CLI-Anything ("make all software natively agent-ready") — HelpScope achieves the same goal with deterministic parsing instead of LLM guesswork.

## ✨ Features

- 🔌 **Zero dependencies**: 100% Python standard library, no pip dependency hell
- 🧠 **Three mainstream formats**: argparse (pip/python), GNU (ls/grep), and subcommand style (docker/git), auto-detected
- 🛡️ **Safe capture**: never goes through a shell (`shell=False`), unified timeout with process kill, automatic fallback across `--help`/`-h`/`-help`/`help`
- 🤖 **Agent-native**: one command generates a function-calling tool schema, including enumerated subcommand slots
- 📦 **Three output formats**: `json` manifest / `schema` tool definition / `md` usage card
- 🧪 **Rule linting**: 6 `HS` rules (missing usage, duplicate flags, missing descriptions, …); non-zero exit code works as a CI gate
- 🌲 **Recursive subcommands**: `--recurse` captures subcommand help layer by layer into the model tree
- ♻️ **Deterministic**: identical input always yields identical output — results are diffable and cacheable
- 🧰 **Library + CLI**: embed via `import helpscope` or use directly from the command line

## 🚀 Quick Start

```bash
# No installation needed — use straight from the repo
python3 -m helpscope capture git --format md      # capture & render a Markdown usage card
python3 -m helpscope capture docker --format schema > docker.tool.json   # generate an Agent tool schema

# Or install as a command
pip install .
helpscope capture docker --format json
```

## 📖 Usage Guide

### Command line

```bash
# 1) Capture mode: runs PROG --help (safe, no shell, default 10s timeout)
helpscope capture <prog> [--recurse] [--depth N] [--timeout 10]
                  --format json|schema|md   [-o out]

# 2) Offline parsing: runs nothing — parses a help-text file directly
helpscope parse <file> --format json|schema|md [-o out]

# 3) Rule linting: HS-rule lint; error-level findings exit with code 1 (CI gate)
helpscope report <file> [--json]
```

### Python library integration example

```python
from helpscope import parse_help_text, capture_help, render_tool_schema, lint_model

# Option 1: pure offline parsing (recommended, zero risk)
text = open("docker_help.txt", encoding="utf-8").read()
model = parse_help_text(text, source="file")

# Option 2: safe capture (no shell, with timeout)
model, used_arg = capture_help("docker", timeout=10)

# Generate an Agent tool schema (drop it straight into your LLM tools list)
schema = render_tool_schema(model)

# Rule linting
findings = lint_model(model)
```

### Sample output (docker fixture)

```text
| Option             | Argument | Description                      |
| ------------------ | -------- | -------------------------------- |
| `-D` `--debug`     | —        | Enable debug mode                |
| `-l` `--log-level` | `string` | Set the logging level (...)      |
| `--tlsverify`      | —        | Use TLS and verify the remote    |
```

## 💡 Design Iterations

- **v1.0.0**: three-format parsing engine (argparse / GNU / subcommands), safe capture, three renderers, 6 HS rules, recursive subcommands.
- **Planned**: direct MCP tool definition output, SARIF report format, support for more framework styles (Go flag / Java CLI).

## 📦 Packaging & Deployment

```bash
# One-click build (self-test + wheel + sdist)
bash scripts/build.sh

# Artifacts land in dist/ — publish to any private PyPI or distribute directly
pip install dist/helpscope-1.0.0-py3-none-any.whl
```

## 🤝 Contributing

Issues and PRs are welcome! Commit messages follow the Angular convention (`feat:` / `fix:` / `docs:` / `test:`). Please read [CONTRIBUTING.md](CONTRIBUTING.md) and make sure the full test suite passes before contributing. Hard requirements: standard library only, Python 3.9+ compatible, unit tests for every feature.

## 📄 License

[MIT License](LICENSE) © 2026 HelpScope Contributors
