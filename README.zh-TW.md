<p align="center"><a href="README.md">简体中文</a> | <b>繁體中文</b> | <a href="README.en.md">English</a></p>

# 🎉 介紹

**HelpScope** 是一個零依賴、離線優先的 CLI 說明文字解析引擎。它把任意命令列工具的 `--help` 輸出變成三類開箱即用的產物：

1. **結構化 JSON 清單** —— 可 diff、可快取、可進 CI；
2. **Agent 工具 Schema** —— LLM function-calling / tool-use 風格的參數定義，讓任意 CLI 原生接入 AI Agent；
3. **Markdown 用法卡** —— 人類與 Agent 都易讀的格式化文件。

純 Python 標準庫實現（Python 3.9+），零第三方依賴，核心解析器完全不執行外部命令，捕獲引擎無 shell、帶逾時，可安全用於自動化流水線。

> 靈感來自 trending 專案 CLI-Anything「讓所有軟體原生 Agent 化」的產品理念——HelpScope 用確定性解析（而非 LLM 猜測）達成同一目標。

## ✨ 特性

- 🔌 **零依賴**：100% Python 標準庫，無 pip 依賴地獄
- 🧠 **三種主流格式**：argparse（pip/python）、GNU（ls/grep）、子命令風格（docker/git）自動識別
- 🛡️ **安全捕獲**：永不經過 shell（`shell=False`）、統一逾時並終止逾時程序、失敗自動回退 `--help`/`-h`/`-help`/`help`
- 🤖 **Agent 原生**：一條命令生成 function-calling 工具 Schema，含列舉子命令槽位
- 📦 **三格式輸出**：`json` 清單 / `schema` 工具定義 / `md` 用法卡
- 🧪 **規則體檢**：6 條 `HS` 規則（缺 usage、重複 flag、缺描述等），非零結束碼可做 CI 門檻
- 🌲 **遞迴子命令**：`--recurse` 逐層捕獲子命令說明並掛載到模型樹
- ♻️ **確定性**：相同輸入永遠產出相同輸出，結果可直接 diff 與快取
- 🧰 **庫 + CLI 雙形態**：既可 `import helpscope` 嵌入你的專案，也可命令列直用

## 🚀 快速開始

```bash
# 無需安裝，倉庫即用
python3 -m helpscope capture git --format md      # 捕獲並渲染 Markdown 用法卡
python3 -m helpscope capture docker --format schema > docker.tool.json   # 生成 Agent 工具 Schema

# 或安裝為命令
pip install .
helpscope capture docker --format json
```

## 📖 使用指南

### 命令列

```bash
# 1) 捕獲模式：執行 PROG --help（安全、無 shell、預設 10 秒逾時）
helpscope capture <prog> [--recurse] [--depth N] [--timeout 10]
                  --format json|schema|md   [-o out]

# 2) 離線解析：不執行任何程式，直接解析說明文字檔案
helpscope parse <file> --format json|schema|md [-o out]

# 3) 規則體檢：HS 規則 lint，error 級發現導致結束碼 1（CI 門檻）
helpscope report <file> [--json]
```

### Python 庫整合範例

```python
from helpscope import parse_help_text, capture_help, render_tool_schema, lint_model

# 方式一：純離線解析（推薦，零風險）
text = open("docker_help.txt", encoding="utf-8").read()
model = parse_help_text(text, source="file")

# 方式二：安全捕獲（無 shell、帶逾時）
model, used_arg = capture_help("docker", timeout=10)

# 生成 Agent 工具 Schema（可直接放進 LLM tools 清單）
schema = render_tool_schema(model)

# 規則體檢
findings = lint_model(model)
```

### 輸出範例（docker 夾具）

```text
| 選項               | 參數     | 說明                             |
| ------------------ | -------- | -------------------------------- |
| `-D` `--debug`     | —        | Enable debug mode                |
| `-l` `--log-level` | `string` | Set the logging level (...)      |
| `--tlsverify`      | —        | Use TLS and verify the remote    |
```

## 💡 設計迭代

- **v1.0.0**：三格式解析引擎（argparse / GNU / 子命令）、安全捕獲、三格式渲染、6 條 HS 規則、遞迴子命令。
- **規劃中**：MCP tool 定義直出、SARIF 報告格式、更多框架風格（Go flag / Java CLI）解析支援。

## 📦 打包部署

```bash
# 一鍵構建（自測 + wheel + sdist）
bash scripts/build.sh

# 產物位於 dist/，可發布到任意私有 PyPI 或直接分發
pip install dist/helpscope-1.0.0-py3-none-any.whl
```

## 🤝 貢獻

歡迎 Issue 與 PR！提交資訊遵循 Angular 規範（`feat:` / `fix:` / `docs:` / `test:`），貢獻前請閱讀 [CONTRIBUTING.md](CONTRIBUTING.md) 並確保全量測試通過。硬性要求：純標準庫、Python 3.9+ 相容、每個功能附帶單元測試。

## 📄 協議

[MIT License](LICENSE) © 2026 HelpScope Contributors
