# 贡献指南

感谢关注 HelpScope！欢迎以 Issue / PR 的形式参与贡献。

## 开发环境

```bash
git clone https://github.com/gitstq/helpscope.git
cd helpscope
python3 -m unittest discover -s tests -v
```

## 提交规范

遵循 Angular 提交规范：

- `feat:` 新功能
- `fix:` 缺陷修复
- `docs:` 文档
- `test:` 测试
- `refactor:` 重构
- `chore:` 构建/工具链

## 贡献方向

- 新的帮助格式解析支持（如 Go flag、Java CLI 框架风格）
- 新的 lint 规则（保持确定性、零依赖）
- 更多输出格式（SARIF、MCP tool 定义等）

## 硬性要求

- 纯 Python 标准库，禁止引入第三方运行时依赖
- Python 3.9+ 兼容
- 每个功能必须附带单元测试
- 提交前请确保全量测试通过
