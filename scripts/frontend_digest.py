#!/usr/bin/env python3
"""Render a Web frontend developer-focused digest from AI News Radar stories."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


TOOL_PATTERNS = {
    "Codex": ("codex", "openai coding agent"),
    "Cursor": ("cursor", "cursor agent"),
    "Claude Code": ("claude code", "anthropic code"),
}

MODEL_PATTERNS = (
    "gpt-", "gemini", "deepseek", "qwen",
    "llm", "model", "模型", "大模型", "api", "sdk", "inference", "reasoning",
)

FRONTEND_PATTERNS = (
    "agent", "coding", "code", "developer", "devtool", "ide", "vscode", "vs code",
    "copilot", "mcp", "plugin", "extension", "skill", "prompt", "context", "cache", "terminal",
    "debug", "refactor", "test", "typescript", "javascript", "react", "next.js", "nextjs",
    "vite", "webpack", "frontend", "front-end", "web", "browser", "api", "sdk",
    "工程", "前端", "代码", "编程", "调试", "重构", "插件", "技能", "上下文", "缓存",
    "测试", "接口", "工作流", "开发者",
)

NOISE_PATTERNS = (
    "image generation", "image generator", "ai art", "midjourney", "stable diffusion",
    "text to video", "text-to-video", "video generation", "短视频", "绘画", "生图", "视频生成",
    "speech", "transcription", "语音转录", "融资", "融资新闻", "celebrity", "vlog",
)

OFFICIAL_DOMAINS = (
    "openai.com", "anthropic.com", "cursor.com", "github.blog", "github.com",
    "developers.googleblog.com", "blog.google", "deepmind.google", "huggingface.co",
    "microsoft.com", "docs.anthropic.com", "code.claude.com",
)


def normalized_text(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("title") or ""),
        str(item.get("recommend_reason_zh") or ""),
        str(item.get("url") or ""),
    ]
    return " ".join(parts).lower()


def story_domain(story: dict[str, Any]) -> str:
    return urlparse(str(story.get("url") or story.get("primary_url") or "")).netloc.lower()


def contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        if re.fullmatch(r"[a-z0-9.+#-]+(?:\s+[a-z0-9.+#-]+)*", pattern):
            if re.search(rf"(?<![a-z0-9]){re.escape(pattern)}(?![a-z0-9])", text):
                return True
        elif pattern in text:
            return True
    return False


def matched_tool(story: dict[str, Any]) -> str | None:
    text = normalized_text(story)
    for tool, patterns in TOOL_PATTERNS.items():
        if contains_any(text, patterns):
            return tool
    return None


def is_official(story: dict[str, Any]) -> bool:
    domain = story_domain(story)
    return (
        story.get("category") == "official"
        or "official_source" in (story.get("reasons") or [])
        or any(domain == official or domain.endswith(f".{official}") for official in OFFICIAL_DOMAINS)
    )


def frontend_score(story: dict[str, Any]) -> float:
    text = normalized_text(story)
    if contains_any(text, NOISE_PATTERNS):
        return -1.0

    score = float(story.get("importance_score") or story.get("score") or 0)
    tool = matched_tool(story)
    has_frontend_signal = contains_any(text, FRONTEND_PATTERNS)
    has_model_signal = contains_any(text, MODEL_PATTERNS)
    is_official_model_update = is_official(story) and has_model_signal
    if not (tool or has_frontend_signal or is_official_model_update):
        return -1.0
    if tool:
        score += 1.2
    if has_frontend_signal:
        score += 0.7
    if has_model_signal:
        score += 0.3
    if is_official(story):
        score += 0.5
    if int(story.get("source_count") or 1) > 1:
        score += 0.15
    return round(score, 4)


def select_stories(stories: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    selected = []
    seen_urls = set()
    for story in sorted(stories, key=frontend_score, reverse=True):
        score = frontend_score(story)
        if score < 1.0:
            continue
        url = str(story.get("url") or story.get("primary_url") or "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        selected.append({**story, "frontend_score": score, "tool": matched_tool(story), "official": is_official(story)})
        if len(selected) >= limit:
            break
    return selected


def human_time(story: dict[str, Any]) -> str:
    raw = str(story.get("latest_at") or story.get("published_at") or "")
    return raw[:10] if raw else "时间待核对"


def core_point(story: dict[str, Any]) -> str:
    reason = str(story.get("recommend_reason_zh") or "").strip()
    if reason:
        return reason
    if story.get("official"):
        return "官方更新，建议查看原始发布说明确认兼容性、迁移成本和可用范围。"
    return "与 AI 编码或开发工作流相关，建议先阅读原文判断是否适合当前项目。"


def markdown_link(title: str, url: str) -> str:
    safe_title = re.sub(r"\s+", " ", title).strip()
    return f"[{safe_title}]({url})"


def render_markdown(stories: list[dict[str, Any]], generated_at: str) -> str:
    models = [
        story
        for story in stories
        if not story["tool"] and story["official"] and contains_any(normalized_text(story), MODEL_PATTERNS)
    ]
    tools = [story for story in stories if story["tool"]]
    workflow = [story for story in stories if story not in models and story not in tools]

    lines = [
        "# 今日AI开发资讯汇总",
        "",
        f"> 生成时间：{generated_at}｜筛选规则：Web 前端开发、AI 编码工具、官方源优先。",
        "",
        "## 大模型&行业重大更新",
        "",
    ]
    if models:
        for story in models[:4]:
            source = story.get("source") or story.get("source_name") or "来源待核对"
            lines.extend([
                f"- 标题：{markdown_link(str(story.get('title') or '未命名更新'), str(story.get('url') or ''))}｜{source}/{human_time(story)}",
                f"  核心要点：{core_point(story)}",
            ])
    else:
        lines.append("- 今日无高价值更新。")

    lines.extend(["", "## 工具更新（Codex / Cursor / Claude Code）", "", "> 新版本、官方功能变动", ""])
    if tools:
        for story in tools[:5]:
            lines.append(f"- {story['tool']}：{markdown_link(str(story.get('title') or '未命名更新'), str(story.get('url') or ''))}。{core_point(story)}")
    else:
        lines.append("- 今日无高价值更新。")

    lines.extend(["", "## 插件｜组件｜自定义技能｜提效玩法（高活跃）", "", "> 第三方插件、脚本、Agent、提示词方案、配套组件，社区热度较高的", ""])
    if workflow:
        for story in workflow[:4]:
            source = story.get("source") or story.get("source_name") or "来源待核对"
            lines.append(f"- {markdown_link(str(story.get('title') or '未命名条目'), str(story.get('url') or ''))}：{source}｜{core_point(story)}")
    else:
        lines.append("- 今日无高价值更新。")

    lines.extend(["", "## 个人行动参考", ""])
    official = [story for story in stories if story["official"]]
    if official:
        lines.append(f"- 优先阅读官方条目：{markdown_link(str(official[0].get('title') or '官方更新'), str(official[0].get('url') or ''))}，确认是否影响当前工具链。")
    if tools:
        lines.append(f"- 工具更新先在非关键项目验证：{tools[0]['tool']} 的兼容性、权限和上下文行为，再扩大使用范围。")
    if workflow:
        lines.append("- 对第三方技能和插件先检查维护活跃度、权限范围和是否会读取项目源码，再接入日常工作流。")
    if not stories:
        lines.append("- 今日无高价值更新，保持关注官方 changelog 即可。")
    lines.append("- 不将营销软文、未证实社区传闻或纯娱乐 AI 内容纳入开发决策。")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a frontend developer AI digest from daily-brief.json")
    parser.add_argument("--input", default="data/daily-brief.json")
    parser.add_argument("--output-json", default="data/frontend-dev-digest.json")
    parser.add_argument("--output-markdown", default="data/frontend-dev-digest.md")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    generated_at = str(payload.get("generated_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    stories = select_stories(list(payload.get("items") or []))
    output = {
        "generated_at": generated_at,
        "source_file": args.input,
        "total_candidates": len(payload.get("items") or []),
        "total_selected": len(stories),
        "items": stories,
    }
    Path(args.output_json).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.output_markdown).write_text(render_markdown(stories, generated_at), encoding="utf-8")
    print(f"Wrote: {args.output_json} ({len(stories)} selected)")
    print(f"Wrote: {args.output_markdown}")


if __name__ == "__main__":
    main()
