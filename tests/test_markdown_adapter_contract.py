# -*- coding: utf-8 -*-
"""Markdown 浏览器适配器的静态契约测试。

适配器（static/assets/journal-markdown.js）负责把 GitHub Markdown API
输出的两类结构转成期刊可用形态：
1. ```mermaid 代码块 → <div class="mermaid">（交给 Mermaid 渲染）
2. 未渲染的 [!NOTE] 引用 → markdown-alert 结构
两者都必须在不支持时保留原始内容，不能让文章内容消失。
"""
from pathlib import Path

ROOT = Path(__file__).parents[1]
ADAPTER_PATH = ROOT / "static/assets/journal-markdown.js"
ADAPTER = ADAPTER_PATH.read_text(encoding="utf-8") if ADAPTER_PATH.exists() else ""
POST = (ROOT / "templates/post.html").read_text(encoding="utf-8")


def test_markdown_adapter_file_and_public_api_exist():
    """适配器必须存在并暴露 JournalMarkdownAdapter.init 接口。"""
    assert ADAPTER, "缺少 static/assets/journal-markdown.js"
    assert "JournalMarkdownAdapter" in ADAPTER
    assert "language-mermaid" in ADAPTER
    assert "markdown-alert" in ADAPTER


def test_adapter_keeps_original_content_when_mermaid_unavailable():
    """Mermaid 不可用时必须保留原始代码块，而不是删除内容。"""
    # 只有在 window.mermaid 存在时才替换，否则原样保留
    assert "window.mermaid" in ADAPTER.replace(" ", "")
    # 替换前先创建新节点再替换，失败不销毁原文
    assert "replaceChild" in ADAPTER


def test_post_loads_markdown_adapter_once():
    """文章页必须加载一次适配器脚本。"""
    assert POST.count("journal-markdown.js") == 1
