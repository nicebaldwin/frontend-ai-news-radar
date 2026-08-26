from __future__ import annotations

from scripts.frontend_digest import frontend_score, render_markdown, select_stories


def story(title: str, *, url: str = "https://example.com/post", category: str = "community", score: float = 0.8) -> dict:
    return {
        "title": title,
        "url": url,
        "source": "Test source",
        "category": category,
        "importance_score": score,
        "source_count": 1,
        "reasons": ["official_source"] if category == "official" else [],
        "latest_at": "2026-08-26T01:00:00Z",
    }


def test_coding_tool_story_outranks_general_model_story():
    coding = story("Cursor adds MCP debugging support", url="https://cursor.com/changelog", category="official")
    general = story("A new LLM benchmark is published")

    assert frontend_score(coding) > frontend_score(general)


def test_noise_story_is_excluded_even_when_its_base_score_is_high():
    noise = story("Stable Diffusion image generation showcase", score=0.99)

    assert select_stories([noise]) == []


def test_generic_consumer_ai_story_is_excluded_without_developer_signal():
    consumer_story = story("Claude memory works everywhere")

    assert select_stories([consumer_story]) == []


def test_markdown_uses_requested_sections_and_empty_state():
    markdown = render_markdown([], "2026-08-26T01:00:00Z")

    assert "# 今日AI开发资讯汇总" in markdown
    assert "## 工具更新（Codex / Cursor / Claude Code）" in markdown
    assert markdown.count("今日无高价值更新。") == 3


def test_selected_tool_story_is_rendered_in_tools_section():
    selected = select_stories([story("Claude Code adds plugin support", url="https://code.claude.com/docs/en/changelog", category="official")])
    markdown = render_markdown(selected, "2026-08-26T01:00:00Z")

    assert len(selected) == 1
    assert selected[0]["tool"] == "Claude Code"
    assert "- Claude Code：" in markdown
