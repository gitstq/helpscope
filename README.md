<p align="center"><b>简体中文</b> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.en.md">English</a></p>

# 🎉 介绍

**HelpScope** 是一个零依赖、离线优先的 CLI 帮助文本解析引擎。它把任意命令行工具的 `--help` 输出变成三类开箱即用的产物：

1. **结构化 JSON 清单** —— 可 diff、可缓存、可进 CI；
2. **Agent 工具 Schema** —— LLM function-calling / tool-use 风格的参数定义，让任意 CLI 原生接入 AI Agent；
3. **Markdown 用法卡** —— 人类与 Agent 都易读的格式化文档。

纯 Python 标准库实现（Python 3.9+），零第三方依赖，核心解析器完全不执行外部命令，捕获引擎无 shell、带超时，可安全用于自动化流水线。

> 灵感来自 trending 项目 CLI-Anything「让所有软件原生 Agent 化」的产品理念——HelpScope 用确定性解析（而非 LLM 猜测）达成同一目标。

## ✨ 特性

- 🔌 **零依赖**：100% Python 标准库，无 pip 依赖地狱
- 🧠 **三种主流格式**：argparse（pip/python）、GNU（ls/grep）、子命令风格（docker/git）自动识别
- 🛡️ **安全捕获**：永不经过 shell（`shell=False`）、统一超时并 kill 超时进程、失败自动回退 `--help`/`-h`/`-help`/`help`
- 🤖 **Agent 原生**：一条命令生成 function-calling 工具 Schema，含枚举子命令槽位
- 📦 **三格式输出**：`json` 清单 / `schema` 工具定义 / `md` 用法卡
- 🧪 **规则体检**：6 条 `HS` 规则（缺 usage、重复 flag、缺描述等），非零退出码可做 CI 门禁
- 🌲 **递归子命令**：`--recurse` 逐层捕获子命令帮助并挂载到模型树
- ♻️ **确定性**：相同输入永远产出相同输出，结果可直接 diff 与缓存
- 🧰 **库 + CLI 双形态**：既可 `import helpscope` 嵌入你的项目，也可命令行直用

## 🚀 快速开始

```bash
# 无需安装，仓库即用
python3 -m helpscope capture git --format md      # 捕获并渲染 Markdown 用法卡
python3 -m helpscope capture docker --format schema > docker.tool.json   # 生成 Agent 工具 Schema

# 或安装为命令
pip install .
helpscope capture docker --format json
```

## 📖 使用指南

### 命令行

```bash
# 1) 捕获模式：运行 PROG --help（安全、无 shell、默认 10s 超时）
helpscope capture <prog> [--recurse] [--depth N] [--timeout 10]
                  --format json|schema|md   [-o out]

# 2) 离线解析：不运行任何程序，直接解析帮助文本文件
helpscope parse <file> --format json|schema|md [-o out]

# 3) 规则体检：HS 规则 lint，error 级发现导致退出码 1（CI 门禁）
helpscope report <file> [--json]
```

### Python 库集成示例

```python
from helpscope import parse_help_text, capture_help, render_tool_schema, lint_model

# 方式一：纯离线解析（推荐，零风险）
text = open("docker_help.txt", encoding="utf-8").read()
model = parse_help_text(text, source="file")

# 方式二：安全捕获（无 shell、带超时）
model, used_arg = capture_help("docker", timeout=10)

# 生成 Agent 工具 Schema（可直接放进 LLM tools 列表）
schema = render_tool_schema(model)

# 规则体检
findings = lint_model(model)
```

### 输出示例（docker 夹具）

```text
| 选项              | 参数     | 说明                             |
| ----------------- | -------- | -------------------------------- |
| `-D` `--debug`    | —        | Enable debug mode                |
| `-l` `--log-level`| `string` | Set the logging level (...)      |
| `--tlsverify`     | —        | Use TLS and verify the remote    |
```

## 💡 设计迭代

- **v1.0.0**：三格式解析引擎（argparse / GNU / 子命令）、安全捕获、三格式渲染、6 条 HS 规则、递归子命令。
- **规划中**：MCP tool 定义直出、SARIF 报告格式、更多框架风格（Go flag / Java CLI）解析支持。

## 📦 打包部署

```bash
# 一键构建（自测 + wheel + sdist）
bash scripts/build.sh

# 产物位于 dist/，可发布到任意私有 PyPI 或直接分发
pip install dist/helpscope-1.0.0-py3-none-any.whl
```

## 🤝 贡献

欢迎 Issue 与 PR！提交信息遵循 Angular 规范（`feat:` / `fix:` / `docs:` / `test:`），贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 并确保全量测试通过。硬性要求：纯标准库、Python 3.9+ 兼容、每个功能附带单元测试。

## 📄 协议

[MIT License](LICENSE) © 2026 HelpScope Contributors
