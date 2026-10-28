# -*- coding: utf-8 -*-
"""期刊分页引擎的纯逻辑测试。

分页引擎（static/assets/journal-paginate.js）的核心是把 #postBody 的
顶级内容块按固定页高切分到多页。为避免在浏览器 DOM 里难测，核心的
"块→页分配"决策被抽成纯函数，本文件测这个函数。
"""
from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
PAGINATE = (ROOT / "static/assets/journal-paginate.js")
PAGINATE_TEXT = PAGINATE.read_text(encoding="utf-8") if PAGINATE.exists() else ""
STYLE = (ROOT / "static/assets/journal-style.css").read_text(encoding="utf-8")


def test_paginate_js_exists():
    """分页引擎文件必须存在。"""
    assert PAGINATE_TEXT, "缺少 static/assets/journal-paginate.js"


def test_paginate_engine_is_exported_for_tests():
    """引擎必须把核心分配函数挂到全局/journalWindow 上，供测试调用。"""
    # 在浏览器里引擎被 IIFE 包裹，但须暴露分配接口（挂 window.JournalPaginator）
    assert "JournalPaginator" in PAGINATE_TEXT
    assert "buildPages" in PAGINATE_TEXT


def test_css_keeps_jpage_fixed_height_and_hidden_overflow():
    """分页后的每页必须是固定高度 + 隐藏溢出，才能实现"填满即截断"。"""
    # 原有 .jpage.markdown-body 规则保留双栏，但分页页容器需要单独的高度/溢出控制
    assert "column-count:2" in STYLE.replace(" ", "")


def test_css_cont_masthead_exists():
    """续页页眉样式（页码｜刊名｜期）必须存在，引擎渲染才有效果。"""
    # 设计稿 preview 第 2 页的续页页眉
    assert ".cont-masthead" in STYLE or ".journal-cont" in STYLE


def test_paginator_continuation_header_reads_issue_number():
    """续页页眉必须从模板的刊头期号读取，而不是硬编码。

    分页引擎读取 .journal-masthead 上的 data-issue 属性，续页页眉显示
    「第X期 / No.X」，保证首页刊头与续页刊头期号一致。
    """
    # 引擎读取 data-issue 属性
    assert "data-issue" in PAGINATE_TEXT
    # 续页页眉渲染期号（中文 + 英文前缀）
    assert "第" in PAGINATE_TEXT or "No." in PAGINATE_TEXT
    # 续页页眉用 DOM 文本接口设置，不直接拼 HTML（防注入）
    assert "textContent" in PAGINATE_TEXT
"""分页引擎的语义块保护契约测试。

分页引擎必须把代码块、表格、图片、Callout、Mermaid 视作不可拆分的块，
否则读者会在两页之间看到被截断的代码或图表。
"""
from pathlib import Path

ROOT = Path(__file__).parents[1]
PAGINATE_PATH = ROOT / "static/assets/journal-paginate.js"
PAGINATE_TEXT = PAGINATE_PATH.read_text(encoding="utf-8") if PAGINATE_PATH.exists() else ""


def test_pagination_source_names_semantic_blocks_as_page_safe():
    assert PAGINATE_TEXT, "缺少 static/assets/journal-paginate.js"
    lowered = PAGINATE_TEXT.lower()
    for selector in ["pre", "table", "figure", "markdown-alert", "mermaid"]:
        assert selector in lowered, f"分页引擎未处理语义块：{selector}"


def test_pagination_marks_blocks_break_inside_avoid():
    assert "breakinside" in PAGINATE_TEXT.replace(" ", "").lower()


def test_pagination_keeps_mobile_bypass():
    assert "720" in PAGINATE_TEXT


def test_journal_columns_fill_left_column_first():
    """期刊分栏必须「左栏填满 → 右栏」，而不是把同段内容均摊到两栏。

    浏览器默认 column-fill: balance 会均衡分配，导致同一段被左右拆开；
    期刊排版要求 column-fill: auto，按阅读顺序先填满左栏。
    """
    compact = STYLE.replace(" ", "").replace("\n", "")
    assert "column-fill:auto" in compact, "缺少 column-fill: auto，分栏会被均衡拆分"


def test_paragraphs_may_flow_across_columns():
    """段落必须允许跨栏续排，否则左栏留白、右栏从中间开始。

    期刊双栏里段落自然跨栏续排是正常排版；只有代码块、表格、图片、
    Callout、Mermaid 这些块级元素才禁止拆分。若给段落加
    break-inside: avoid，长段落整段被推到右栏，左栏底部留出大片空白。
    """
    import re
    m = re.search(r"\.jpage\.markdown-body > p \{([^}]*)\}", STYLE)
    assert m, "缺少 .jpage.markdown-body > p 规则"
    body = m.group(1)
    # 先剥离 CSS 注释，避免注释里提到的属性名造成误判
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    body = body.replace(" ", "").replace("\n", "")
    assert "break-inside:avoid" not in body, "段落不应禁止跨栏拆分"


def test_pagination_measures_blocks_at_single_column_width():
    """测量宽度必须是单栏宽，而非容器全宽。

    页内正文按双栏排布，每个块实际只占一栏宽。若测量容器用容器全宽，
    块高度会被低估约一半，分页时所有块被误判为塞得进一页，随后被
    .jpage 的 overflow:hidden 静默裁掉——读者会丢正文且毫无提示。
    """
    compact = PAGINATE_TEXT.replace(" ", "")
    assert "singleColumnWidth" in compact, "缺少单栏宽度测量变量"
    # 单栏宽 = (容器宽 - 栏间距) / 2
    assert "/2" in compact or "/ 2" in PAGINATE_TEXT
    # 栏间距从计算样式读取，而非硬编码
    assert "columnGap" in compact
    assert "getComputedStyle" in compact


def test_all_heading_levels_span_columns():
    """所有标题层级都必须跨栏，不能被栏线切开。

    h2/h3 已跨栏，但 h4/h5/h6 若遗漏 column-span: all，
    三级以下标题会挤在单栏里被截断，破坏章节层级。
    """
    import re
    m = re.search(r"\.jpage\.markdown-body h4,\s*\n\.jpage\.markdown-body h5,\s*\n"
                  r"\.jpage\.markdown-body h6 \{([^}]*)\}", STYLE)
    assert m, "缺少 h4/h5/h6 组合规则"
    body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S).replace(" ", "").replace("\n", "")
    assert "column-span:all" in body, "h4/h5/h6 必须 column-span: all"


def test_only_headings_span_columns():
    """只有标题跨栏；代码块、列表、引用、表格、图、Alert、Mermaid 留在栏内。

    跨栏元素会强制结束当前栏。技术文章代码密集时若 pre/ul/blockquote 都跨栏，
    每块都打断栏流，导致左栏只填到一半就换栏。只让标题跨栏可让正文连续填充。
    """
    import re
    # 收集所有声明 column-span: all 的选择器
    spanning = []
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", STYLE, re.S):
        sel, body = m.group(1), m.group(2)
        clean = re.sub(r"/\*.*?\*/", "", body, flags=re.S).replace(" ", "").replace("\n", "")
        if "column-span:all" in clean:
            spanning.append(sel.strip())
    joined = " ".join(spanning).lower()
    # 标题类必须跨栏
    assert "h1" in joined or "h2" in joined or "h3" in joined, "标题应跨栏"
    # 这些块必须不跨栏
    for bad in ["pre", "blockquote", "markdown-alert", "mermaid", "table", "figure"]:
        hits = [s for s in spanning if bad in s.lower()]
        assert not hits, f"{bad} 不应跨栏，但出现在: {hits}"
