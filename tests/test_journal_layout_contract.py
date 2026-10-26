from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
STYLE = (ROOT / "static/assets/journal-style.css").read_text(encoding="utf-8")
BASE = (ROOT / "templates/base.html").read_text(encoding="utf-8")
POST = (ROOT / "templates/post.html").read_text(encoding="utf-8")
FOOTER = (ROOT / "templates/footer.html").read_text(encoding="utf-8")
POST_JS = (ROOT / "static/assets/journal-post.js").read_text(encoding="utf-8")

# ---- 小工具：让契约断言落在“值”上而不是字符串存在性，杜绝假绿 ----


def _css_var(css, name):
    """读取 :root 中设计令牌的定义值；不匹配后面 var(--name,..) 的引用。"""
    root = re.search(r":root\s*\{([^}]*)\}", css)
    assert root, ":root 块缺失，无法读取设计令牌"
    m = re.search(r"(?m)^\s*--" + re.escape(name) + r"\s*:\s*([^;]+?)\s*;", root.group(1))
    assert m, "设计令牌 --%s 未在 :root 定义" % name
    return m.group(1)


def _rule(css, selector):
    """提取首个与选择器匹配的 CSS 规则体（不含花括号）。约定文件内规则体不嵌套花括号。"""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert m, "CSS 规则 %s 缺失" % selector
    return m.group(1)


def _js_function_body(src, name):
    """提取 function <name>(...) { ... } 全文；跳过注释与字符串，正确处理嵌套花括号。"""
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)", src)
    if not m:
        return None
    brace = src.find("{", m.end())
    if brace < 0:
        return None
    depth, i, quote = 1, brace + 1, None
    line_c = block_c = False
    while i < len(src):
        ch = src[i]
        if line_c:
            if ch == "\n":
                line_c = False
            i += 1
            continue
        if block_c:
            if src[i:i + 2] == "*/":
                block_c = False
                i += 2
                continue
            i += 1
            continue
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if src[i:i + 2] == "//":
            line_c = True
            i += 2
            continue
        if src[i:i + 2] == "/*":
            block_c = True
            i += 2
            continue
        if ch in "'\"`":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():i + 1]
        i += 1
    return None


def _label_time_rules(template):
    """抽取某模板内所有 .LabelTime{...} 规则体（含 @media 内与分号变体）。

    规则体为空表示该模板没有任何针对 LabelTime 的显式规则（即默认不隐藏）。
    旧断言的教训：子串匹配会被分号差异绕过而假绿，这里按声明语义逐条校验。
    """
    return re.findall(r"\.LabelTime\s*\{([^}]*)\}", template)


# ---- 契约测试 ----


def test_design_tokens_define_paper_typography_and_colors():
    assert "--journal-paper" in STYLE
    assert "--journal-ink" in STYLE
    assert "--journal-accent" in STYLE
    # 正文密度令牌：存在不够，值必须是 16px / 1.72，且与 body.journal-site 兜底同步
    assert _css_var(STYLE, "journal-body-size") == "16px"
    assert _css_var(STYLE, "journal-body-leading") == "1.72"
    site = _rule(STYLE, "body.journal-site")
    assert "font-size:16px" in site.replace(" ", "")
    assert "line-height:1.72" in site.replace(" ", "")


def test_global_container_has_paper_layout_hook():
    assert "journal-site" in BASE


def test_mobile_home_keeps_article_date():
    plist = (ROOT / "templates/plist.html").read_text(encoding="utf-8")
    # 结构：日期标签的渲染类与数据字段必须存在
    assert "LabelTime" in plist and "createdDate" in plist
    # 语义：任何 .LabelTime{...} 规则都不允许含 display:none。
    # 旧实现用无分号子串 ".LabelTime{display:none}"，被 "display:none;" 漏检而假绿；
    # 现在按声明语义逐条校验，分号差异无法绕过。
    for body in _label_time_rules(plist):
        assert "display:none" not in body.replace(" ", "")


def test_post_uses_sixteen_pixel_body_and_no_hidden_page_overflow():
    # 正文 16px 由 .jpage.markdown-body 实际应用令牌保证，不是“文本里出现过 16px”就算
    md_body = _rule(STYLE, ".jpage.markdown-body").replace(" ", "")
    assert "font-size:var(--journal-body-size,16px)" in md_body
    assert "line-height:var(--journal-body-leading,1.72)" in md_body
    # 分页安全底线：共享 CSS 与文章页模板都不得以 hidden 裁剪正文
    assert "overflow:hidden" not in STYLE.replace(" ", "")
    assert "overflow:hidden" not in POST.replace(" ", "")


def test_jpage_uses_visible_safe_rules_desktop():
    base = _rule(STYLE, ".jpage").replace(" ", "")
    assert "overflow:visible" in base            # 安全网：宁可溢出显示也不裁剪
    assert "overflow:hidden" not in base
    assert "height:var(--journal-page-height" in base  # 桌面固定高来自令牌
    assert "min-width:0" in base                 # grid 子项允许收窄不撑破布局


def test_pagination_mobile_flow_restores_body_and_stops_paginating():
    # 移动断点与 CSS 共用 720px，防两处漂移
    is_mobile = _js_function_body(POST_JS, "isMobileFlow")
    assert is_mobile and "matchMedia" in is_mobile and "720" in is_mobile
    assert "@media(max-width:720px)" in STYLE.replace(" ", "")

    # paginate 必须先还原正文，再对移动流式早退（不生成任何新纸页）
    paginate = _js_function_body(POST_JS, "paginate")
    assert paginate
    restore_at = paginate.index("restoreBodyContent();")
    mobile_at = paginate.index("if (isMobileFlow()) return [];")
    open_at = paginate.index("openNextPage();")
    assert restore_at < mobile_at < open_at

    # 还原正文必须把内容真正放回 #postBody
    restore = _js_function_body(POST_JS, "restoreBodyContent")
    assert restore and "appendChild" in restore and "postBody" in restore


def test_engine_inline_limits_released_on_restore_preserving_author_styles():
    # 给超高块施加内联限制前，必须先快照原始内联值（含 maxHeight/overflow）
    apply_fn = _js_function_body(POST_JS, "constrainOversizedBlock")
    assert apply_fn, "缺少 constrainOversizedBlock()"
    assert "maxHeight" in apply_fn and "overflow" in apply_fn
    assert "set" in apply_fn and "maxHeight:" in apply_fn and "overflow:" in apply_fn

    # 还原正文路径必须逐元素释放引擎注入的内联限制，移动流式才不被行内样式打断
    restore = _js_function_body(POST_JS, "restoreBodyContent")
    assert restore and "releaseEngineConstraints(" in restore

    cleanup = _js_function_body(POST_JS, "releaseEngineConstraints")
    assert cleanup, "缺少 releaseEngineConstraints()"
    assert "maxHeight" in cleanup and "overflow" in cleanup
    assert "engineConstraintSnapshot" in cleanup


# ---- Task 3：统一首页/标签页/页脚纸刊视觉 ----


def test_all_site_templates_use_shared_journal_hooks():
    """首页/标签/文章三页都必须同时挂载共享纸刊类并实际加载共享 CSS。

    只挂 class 而不加载样式等于没有视觉，因此“类钩子”与“样式引用”两条
    断言并列，任缺其一即失败。
    """
    for name in ("plist.html", "tag.html", "post.html"):
        content = (ROOT / "templates" / name).read_text(encoding="utf-8")
        assert "journal-" in content, "%s 缺少共享纸刊类钩子" % name
        assert "journal-style.css" in content, "%s 未加载共享纸刊样式" % name


def test_home_does_not_hide_date_on_small_screens():
    content = (ROOT / "templates/plist.html").read_text(encoding="utf-8")
    # 数据契约：目录行循环 / 分页 URL / 日期字段必须原样保留，样式重构不得破坏
    assert "postListJson" in content
    assert "prevUrl" in content and "nextUrl" in content
    assert "createdDate" in content
    # 移动断点统一 720px：掉回旧的 600px 单独定义会说明局部规则复活
    assert "@media(max-width:720px)" in STYLE.replace(" ", "")
    # 语义检查放在共享样式表全文上：任何位置的 .LabelTime 规则（含 media 内、含分号变体）
    # 都不得隐藏日期。media 块含嵌套花括号，_rule 的正则无法可靠解析，故全文扫描，
    # 其结果严格强于"只查 720 断点"——任意局部规则复活都会被拦截。
    for body in _label_time_rules(STYLE):
        assert "display:none" not in body.replace(" ", "")


def test_tag_keeps_search_and_filter_fields():
    content = (ROOT / "templates/tag.html").read_text(encoding="utf-8")
    # 搜索/筛选/定位行为的承载结构不能被样式重构删掉
    assert "subnav-search-input" in content
    assert "searchShow" in content and "updateShowTag" in content
    assert "window.location.hash" in content
    assert 'getElementsByClassName("SideNav")' in content
    assert "LabelTime" in content
    for body in _label_time_rules(content):
        assert "display:none" not in body.replace(" ", "")


def test_site_heading_drops_monaco_uses_shared_stack():
    """纸刊标题字体统一来自共享 CSS 的衬线栈，任何页面或样式都不许残留 Monaco。"""
    for name in ("plist.html", "tag.html", "post.html"):
        content = (ROOT / "templates" / name).read_text(encoding="utf-8")
        assert "Monaco" not in content, "%s 仍残留 Monaco 标题字体" % name
    assert "Monaco" not in STYLE
    # 全站衬线兜底由 body.journal-site 保证（Task 2 已断言），此处确认无回归
    assert re.search(r"body\.journal-site\s*\{", STYLE)


def test_base_wires_journal_semantic_regions():
    """base 骨架给出 header/content/footer 三段语义类，主题脚本保持原样。"""
    assert 'class="journal-header"' in BASE
    assert 'class="journal-content"' in BASE
    assert 'class="journal-footer"' in BASE
    # 主题切换与图标脚本不得被结构重构破坏
    assert "themeSwitch" in BASE and "modeSwitch" in BASE
    assert "IconList" in BASE


def test_footer_values_and_copyright_script_preserved():
    """页脚备案号/运行天数/版权年份与生成脚本必须完整保留（由 base include footer.html）。"""
    assert "filingNum" in FOOTER
    assert "runday" in FOOTER
    assert "copyrightYear" in FOOTER
    assert "Powered by" in FOOTER
    assert "beian.miit.gov.cn" in FOOTER


def test_shared_css_owns_unified_site_layout():
    """Task 3 把首页/标签页的骨架、目录行、元数据、标签、搜索、分页统一收进共享 CSS。"""
    for sel in (".journal-list", ".journal-row", ".journal-meta",
                ".journal-tags", ".journal-search", ".journal-pagination",
                ".journal-page-title", ".journal-brand", ".journal-subtitle"):
        assert re.search(re.escape(sel) + r"\s*\{", STYLE), "共享 CSS 缺少 %s" % sel
def test_dir_row_title_column_is_shrinkable_for_ellipsis():
    """目录行标题列必须可收缩，长标题才触发省略号而不撑破布局。

    根因复盘：`.journal-dir-icon{flex:none}` 等价于 flex:0 0 auto，
    把标题列（.journal-row 的 flex 子项）钉死为不可收缩；列内含标题的
    flex 子项 `.listTitle` 又缺 min-width:0。两者叠加导致列宽恒为内容宽，
    `.listTitle` 的 overflow 省略号永不生效，窄屏下长标题横向溢出。
    契约：列本身允许收缩（min-width:0 且不残留 flex:none），
    列内标题子项可收缩（min-width:0;flex:1 1 auto），图标保持固定（flex:none）。
    """
    # 标题列不允许再被 flex:none 钉死，且要有 min-width:0 才能收缩
    col = _rule(STYLE, ".journal-dir-icon").replace(" ", "")
    assert "flex:none" not in col, ".journal-dir-icon 仍被 flex:none 钉死，标题列无法收缩"
    assert "min-width:0" in col, ".journal-dir-icon 缺少 min-width:0，长标题无法省略"
    # 列内标题子项可收缩：min-width:0 + flex:1 1 auto，省略号才会在剩余空间生效
    # 注意：这里用原文断言（不去空格），flex:1 1 auto 是含空格的简写
    title = _rule(STYLE, ".journal-dir-icon .listTitle")
    assert "min-width:0" in title, "标题子项 .listTitle 缺少 min-width:0"
    assert "flex:1 1 auto" in title, "标题子项 .listTitle 缺少 flex:1 1 auto"
    # 图标保持固定尺寸，不随列收窄被压缩
    icon = _rule(STYLE, ".journal-dir-icon .SideNav-icon").replace(" ", "")
    assert "flex:none" in icon, "目录行图标未保持固定（应有 flex:none）"

