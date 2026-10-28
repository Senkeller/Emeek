from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
STYLE_PATH = ROOT / "static/assets/journal-style.css"
STYLE = STYLE_PATH.read_text(encoding="utf-8") if STYLE_PATH.exists() else ""
POST = (ROOT / "templates/post.html").read_text(encoding="utf-8")
GMEek = (ROOT / "Gmeek.py").read_text(encoding="utf-8")


def css_rule(selector):
    """提取首个与选择器匹配的 CSS 规则体；容忍选择器与 { 之间的空白。"""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", STYLE)
    assert m, f"缺少 CSS 规则：{selector}"
    return m.group(1)


def test_post_contains_template_article_regions_and_real_date_mapping():
    assert "journal-masthead" in POST
    assert "journal-title" in POST
    assert "journal-authors" in POST
    assert "journal-affil" in POST
    assert "journal-abstract" in POST
    assert "journal-keywords" in POST
    assert "journal-paper" in POST
    assert "journal-received" in POST
    assert "createdDate" in POST
    assert 'postBase["createdDate"]=issue.get("createdDate","")' in GMEek.replace(" ", "")


def test_template_uses_journal_meta_and_hides_optional_footer_rows():
    assert "journalMeta" in POST
    assert "journalMeta['author']" in POST or 'journalMeta["author"]' in POST
    assert "journalMeta['fund']" in POST or 'journalMeta["fund"]' in POST
    assert "journalMeta['authorBio']" in POST or 'journalMeta["authorBio"]' in POST
    assert "journalMeta['correspondingAuthor']" in POST or 'journalMeta["correspondingAuthor"]' in POST


def test_post_uses_semicolon_keywords_with_clickable_label_links():
    assert "jkeyword" in POST
    assert "tag.html#" in POST
    assert "；" in POST
    assert "background-color:" not in POST.split("journal-keywords", 1)[1].split("</div>", 1)[0]


def test_template_typography_matches_pdf_conversion():
    # 模板换算值由设计令牌承载（二号22pt→29px），断言令牌而非裸数值
    assert "29px" in css_rule(".journal-title")
    assert "var(--journal-title-size" in css_rule(".journal-title")
    assert "19px" in css_rule(".journal-authors")
    assert "12px" in css_rule(".journal-affil")
    # 摘要与关键词共用组合选择器（.journal-abstract,.journal-keywords），字号由
    # var(--journal-body-size, 15px) 令牌承载；此处断言组合规则体包含该令牌
    combo_m = re.search(r"\.journal-abstract\s*,\s*\.journal-keywords\s*\{([^}]*)\}", STYLE)
    assert combo_m, "缺少 .journal-abstract,.journal-keywords 组合 CSS 规则"
    assert "var(--journal-body-size,15px)" in combo_m.group(1).replace(" ", "")
    assert "15px" in css_rule(".jpage.markdown-body")
    assert "text-indent:2em" in STYLE.replace(" ", "")
    assert "column-count:2" in STYLE.replace(" ", "")


def test_pdf_specific_font_roles_are_explicit():
    assert "Kaiti SC" in STYLE
    assert "STKaiti" in STYLE
    assert "Songti SC" in STYLE
    assert "Times New Roman" in STYLE
    assert "font-family:var(--journal-kai" in STYLE.replace(" ", "")


def test_masthead_keeps_only_real_date_derived_issue_number():
    masthead = css_rule(".journal-masthead")
    assert "display:flex" in masthead.replace(" ", "")
    assert "journal-issue" in POST
    assert "No." in POST
    assert "Vol." not in POST
    assert "doi" not in POST.lower()


def test_body_supports_pdf_figure_table_and_formula_typography():
    assert ".jpage.markdown-body img" in STYLE
    assert ".jpage.markdown-body table" in STYLE
    assert ".jpage.markdown-body .katex-display" in STYLE
    assert "figure" in STYLE
    assert "figcaption" in STYLE


def test_mobile_article_becomes_single_column_without_clipping():
    assert "@media(max-width:720px)" in STYLE.replace(" ", "")
    mobile_start = STYLE.replace(" ", "").find("@media(max-width:720px)")
    mobile = STYLE.replace(" ", "")[mobile_start:]
    assert "column-count:1" in mobile
    # 桌面：分页引擎把内容按固定页高切分，每页 overflow:hidden 截断溢出块，
    # 由 JS 保证不丢内容（试排-回溯）；移动端单栏不分页，禁止 overflow:hidden 隐藏内容。
    assert "overflow:hidden" not in mobile
    assert "overflow:hidden" not in POST.replace(" ", "")


def test_post_render_forwards_issue_labels_as_post_labels():
    """post.html 用 postLabels 渲染关键词块，Gmeek.py 必须把它传给模板。

    模板中的关键分支是 `{% if postLabels|length>0 %}`；若构建脚本未传递
    postLabels，Jinja2 会将未定义变量当作 Undefined（length 为 0），
    关键词块被整体跳过——本地预览有关键词、线上却消失，根因在此。
    """
    # 后端渲染 post.html 时显式传入 postLabels（来自 issue 的 labels）
    assert "postLabels=issue.get(\"labels\",[])" in GMEek.replace(" ", "")
    # renderHtml 的渲染上下文包含 postLabels，且必须作为模板变量传入
    assert "postLabels=postLabels" in GMEek.replace(" ", "")


def test_paginated_pages_look_like_individual_paper_sheets():
    """分页后的每页必须是独立「纸页」视觉：白底、细边框、投影、页距，
    而不是共享一块纸、只用分隔线区分（用户反馈：只见分页线不见纸页）。"""
    jpage_rule = css_rule(".jpages .jpage")
    assert "background:" in jpage_rule or "background-color:" in jpage_rule
    assert "border:" in jpage_rule
    assert "box-shadow" in jpage_rule
    # margin 简写或 margin-bottom 都算页距
    assert "margin:" in jpage_rule or "margin-bottom" in jpage_rule
    # 页码伪元素（页脚居中页码）
    after_rule = css_rule(".jpages .jpage::after")
    assert "counter" in after_rule
    assert "position:absolute" in after_rule.replace(" ", "")
    assert "text-align:center" in after_rule.replace(" ", "")


def test_markdown_body_elements_are_typographically_paper_adapted():
    """markdown 正文元素在期刊排版里应有论文化适配，而非默认 markdown 风格：
    代码块跨栏/不挤压、标题间距收紧、引用/列表与正文密度一致。"""
    # 代码块跨栏（column-span:all），避免在双栏里被压窄
    pre_rule = css_rule(".jpage.markdown-body pre")
    assert "column-span:all" in pre_rule.replace(" ", "")
    # 行内代码用宋体/灰底，区别于默认粗体块
    assert "code" in STYLE
    # 引用块左侧竖线、灰褐文字（论文引文风格）
    blockquote_rule = css_rule(".jpage.markdown-body blockquote")
    assert "border-left" in blockquote_rule.replace(" ", "")
    assert "margin:" in blockquote_rule.replace(" ", "")
    # 列表紧排版
    li_rule = css_rule(".jpage.markdown-body li")
    assert "margin:" in li_rule.replace(" ", "")
    # 分隔线细线
    hr_rule = css_rule(".jpage.markdown-body hr")
    assert "background" in hr_rule.replace(" ", "") or "border" in hr_rule.replace(" ", "")
def test_markdown_adapter_elements_are_cross_column_and_page_safe():
    """Callout 与 Mermaid 必须跨双栏且不跨页拆分。"""
    assert ".jpage.markdown-body .markdown-alert" in STYLE
    assert ".jpage.markdown-body .mermaid" in STYLE
    assert "break-inside:avoid" in STYLE.replace(" ", "")


def test_optional_journal_footer_has_small_print_style():
    """文章元信息页脚使用小五号字与细分隔线。"""
    assert ".journal-meta-foot" in STYLE
    rule = css_rule(".journal-meta-foot")
    assert "font-size" in rule
    assert "border-top" in rule
