# 前端 AI 开发日报

此 fork 在上游的采集、去重和故事合并之后，额外生成面向 Web 前端工程师的日报：`data/frontend-dev-digest.json` 与 `data/frontend-dev-digest.md`。

筛选优先级是 Codex、Cursor、Claude Code、MCP、IDE、代码调试、重构、测试、上下文、缓存、前端工程工具和官方模型/API 更新。图片、视频、营销软文和未验证传闻会被排除。官方来源、工具直接命中和多源事件会获得更高权重。

工作流每天北京时间 09:00 运行，也可从 GitHub Actions 手动触发。默认使用 `feeds/frontend-dev.example.opml`；需要加入个人 RSS 时，将 OPML 文件做 base64 编码后设置为仓库 Secret `FRONTEND_DEV_OPML_B64`。不要提交私有 OPML、token、Cookie 或付费社交源密钥。

本地运行：

```bash
python scripts/frontend_digest.py \
  --input data/daily-brief.json \
  --output-json data/frontend-dev-digest.json \
  --output-markdown data/frontend-dev-digest.md
```

测试：

```bash
python -m pytest -q tests/test_frontend_digest.py
```
