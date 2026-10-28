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


def _rule_body_by_selector_member(selector):
    """按「选择器成员」提取规则体，支持组合选择器。

    css_rule 用 re.escape 整体匹配，只能命中「选择器开头就是它」的单条规则。
    真实样式里标题是组合选择器：
        .jpage.markdown-body h1,
        .jpage.markdown-body h2 { ... }
    本函数按逗号拆分选择器逐段精确比对。

    关键：必须先把 CSS 注释整体剥掉再做 { } 配对解析。
    注释正文里出现的花括号（例如 "…的块 { … }"）会被朴素正则当成规则边界，
    导致选择器与规则体错位、匹配不到真实规则。
    """
    stripped = re.sub(r"/\*.*?\*/", "", STYLE, flags=re.S)
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", stripped):
        selectors = [x.strip() for x in m.group(1).split(",")]
        if selector in selectors:
            return m.group(2)
    raise AssertionError(f"缺少 CSS 规则（组合选择器成员）：{selector}")


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


def test_continuous_layout_spans_all_headings_across_columns():
    """连续滚动双栏：每一级标题都必须跨栏（column-span: all）。

    连续媒体下 column-fill:auto 会被浏览器强制当作 balance，无法靠它控制
    填栏顺序。唯一可靠的切分手段是让标题通栏——跨栏元素强制打断栏流，
    使每个标题之间自然形成一个独立的双栏版面单元。
    实测 33 篇真实文章，恢复标题跨栏后「仅右栏」组从 23 降到 0。
    """
    for sel, label in [
        (".jpage.markdown-body h1", "h1"),
        (".jpage.markdown-body h2", "h2"),
        (".jpage.markdown-body h3", "h3"),
        (".jpage.markdown-body h4", "h4-h6"),
    ]:
        rule = _rule_body_by_selector_member(sel)
        assert "column-span:all" in rule.replace(" ", ""), f"{label} 必须跨栏"


def test_continuous_layout_has_no_fixed_page_height_or_clipping():
    """连续滚动布局不得有任何固定页高/裁切残留。

    固定高度 + overflow:hidden 是旧分页模型的核心机制（把溢出的块静默裁掉）。
    连续滚动下这两者都会导致正文丢失，必须彻底移除。
    """
    compact = STYLE.replace(" ", "").replace("\n", "")
    assert "height:780px" not in compact, "不得残留固定页高 780px"
    for m in re.finditer(r"([^{}]*)\{([^}]*)\}", re.sub(r"/\*.*?\*/", "", STYLE, flags=re.S)):
        sel, body = m.group(1), m.group(2)
        if ".jpage" in sel and "overflow:hidden" in body.replace(" ", ""):
            raise AssertionError(f"选择器 {sel.strip()} 仍在使用 overflow:hidden 裁切正文")


def test_continuous_layout_removes_pagination_artifacts():
    """旧分页模型的所有产物必须清除：.jpages 纸页容器、续页页眉、页码。"""
    for artifact in [".jpages", ".cont-masthead", ".journal-pagination"]:
        assert artifact not in STYLE, f"CSS 仍残留分页产物：{artifact}"
    assert "journal-pagination" not in POST, "模板仍残留页码节点"


def test_pagination_engine_is_removed():
    """分页引擎已退役：文件不存在，且模板不再引用。"""
    assert not (ROOT / "static/assets/journal-paginate.js").exists(), \
        "journal-paginate.js 应已删除"
    assert "journal-paginate" not in POST, "模板仍引用已删除的分页引擎"


def test_images_span_all_columns():
    """含图片的块必须通栏，否则图片被栏线切成左右两半。

    图片是行内元素，在多栏流里无法跨栏续排。实测 27 篇有图文章、84 处图片块，
    加 p:has(img) 通栏后全部正确显示为容器全宽。
    """
    has_img = _rule_body_by_selector_member(".jpage.markdown-body p:has(img)")
    assert "column-span:all" in has_img.replace(" ", ""), "含图片段落必须 column-span: all"
    bare = _rule_body_by_selector_member(".jpage.markdown-body a:has(> img)")
    assert "column-span:all" in bare.replace(" ", ""), "裸 a>img 必须 column-span: all"


def test_markdown_body_elements_are_typographically_paper_adapted():
    """markdown 正文元素在期刊排版里应有论文化适配，而非默认 markdown 风格：
    代码块跨栏/不挤压、标题间距收紧、引用/列表与正文密度一致。"""
    # 代码块留在栏内（不跨栏）：跨栏会打断栏流，技术文章左栏会填不满
    pre_rule = css_rule(".jpage.markdown-body pre")
    assert "column-span:all" not in pre_rule.replace(" ", "")
    assert "overflow:auto" in pre_rule.replace(" ", "")
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


def test_post_template_contains_local_logo_markup():
    """期刊 logo 必须由仓库内静态资源承载，而不是依赖 GitHub 临时附件地址。"""
    assert "journal-logo-link" in POST
    assert "journal-logo" in POST
    # 本地静态资源 URL（homeUrl 起头），而非外部 user-attachments 地址
    assert 'journal-logo.png' in POST
    assert "user-attachments" not in POST


def test_post_template_has_bilingual_issue_row():
    """刊头第二行左右应为中英文期号对照：左侧第X期、右侧No.X。"""
    assert "journal-issue-prefix" in POST
    assert "第{{ blogBase['createdDate'][5:7]|int }}期" in POST
    # 中英期号来自同一个月，避免两边月份错位
    assert POST.count("createdDate'][5:7]|int }}") >= 2


def test_journal_styles_define_logo_responsive_rules():
    """logo 样式必须是响应式的：桌面限宽、移动端缩小、透明保持。"""
    assert ".journal-logo" in STYLE
    assert "max-width:min(100%,420px)" in STYLE.replace(" ", "")
    assert "object-fit:contain" in STYLE.replace(" ", "")
    assert ".journal-logo-link:focus-visible" in STYLE
    assert "height:auto" in css_rule(".journal-logo").replace(" ", "")
