#!/usr/bin/env bash
# HelpScope 一键构建脚本：清理 → 自测 → 构建 wheel/sdist
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> [1/3] 运行单元测试"
python3 -m unittest discover -s tests -v

echo "==> [2/3] 清理旧构建产物"
rm -rf build dist *.egg-info

echo "==> [3/3] 构建 wheel 与 sdist"
python3 -m pip install --quiet build
python3 -m build

echo "✅ 构建完成，产物位于 dist/:"
ls -la dist/
