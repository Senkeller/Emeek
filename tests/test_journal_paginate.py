# -*- coding: utf-8 -*-
"""期刊分页引擎契约测试。

分页引擎（static/assets/journal-paginate.js）把 #postBody 的顶层内容块
按固定页高切分成多页纸页，实现 PDF 式的视觉分页。

核心算法是「DOM 顺序分页」：
    把块逐个 append 进当前页 → 检查是否有块底边超过页面内容底边
    → 溢出就把该块挪到下一页开头

与已被删除的旧引擎（按块高贪心分配）的本质区别：
旧引擎预先计算总页数并分配块到页，块高测量误差会累积；
新引擎边排边测，浏览器负责断行，JS 只判断「这块放得下吗」，
且单块超过一页时强制保留，保证绝不丢内容。
"""
from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
PAGINATE_PATH = ROOT / "static/assets/journal-paginate.js"
PAGINATE_TEXT = PAGINATE_PATH.read_text(encoding="utf-8") if PAGINATE_PATH.exists() else ""
STYLE = (ROOT / "static/assets/journal-style.css").read_text(encoding="utf-8")
POST = (ROOT / "templates/post.html").read_text(encoding="utf-8")


def compact(s):
    """去掉空白与注释，便于做属性级断言。"""
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S).replace(" ", "").replace("\n", "")


def test_paginate_engine_exists():
    """分页引擎文件必须存在。"""
    assert PAGINATE_TEXT, "缺少 static/assets/journal-paginate.js"


def test_engine_is_dom_order_pagination():
    """引擎必须采用「DOM 顺序分页」，而非预先按块高贪心分配。

    判定依据：
    - 逐个 append 子节点（appendChild 在遍历循环里）
    - 有溢出检测函数（检查 bottom 是否超过内容底边）
    - 溢出时把块移出并挪到下一页（removeChild + 新页）
    """
    c = compact(PAGINATE_TEXT)
    assert "appendChild" in c, "引擎需把块逐个 append 进页"
    assert "getBoundingClientRect" in c, "引擎需用真实几何测量溢出"
    assert "removeChild" in c, "溢出时需把块移出当前页"
    # 不得再出现旧引擎的贪心分配纯函数
    assert "buildPages" not in PAGINATE_TEXT, "不得保留旧的贪心分页函数"


def test_engine_never_drops_content():
    """单块超过一整页时必须强制保留，绝不允许丢弃。

    这是本引擎最重要的安全性质：判断溢出后移出块，但若移出后当前页
    变空（说明这一块本身就比一页高），必须把它放回去而不是丢进虚空。
    """
    c = compact(PAGINATE_TEXT)
    # 必须有「页空了就把块放回去」的分支
    assert re.search(r"contentChildren\(\w+\)\.length===0|children\.length===0", c), \
        "缺少「当前页为空」的判断分支"
    # 必须有强制 append 的兜底
    assert c.count("appendChild") >= 3, "需包含正常追加 + 兜底追加两处"


def test_engine_waits_for_async_content():
    """必须等 window load 后再分页：图片、Mermaid 渲染完成会改变块高。"""
    c = compact(PAGINATE_TEXT)
    assert "load" in PAGINATE_TEXT, "需监听 window load"
    assert "readyState" in PAGINATE_TEXT, "需处理已加载完成的情况"


def test_engine_skips_pagination_on_narrow_screens():
    """窄屏不分页：小屏上固定页高会造成频繁翻页、体验差。"""
    assert "720" in PAGINATE_TEXT, "需有 720px 断点判断"


def test_engine_marks_page_number():
    """每页需有页码标识（与 PDF 观感一致）。"""
    assert "pgno" in PAGINATE_TEXT or "page-number" in PAGINATE_TEXT, \
        "每页需生成页码元素"


def test_css_defines_a4_proportion_page():
    """纸页容器必须按 A4 比例：920px 宽 × 1300px 高（1.414 比例）。

    实测 33 篇真实文章在此页高下内容零丢失、最长文章 5 页。
    """
    c = compact(STYLE)
    assert ".jpages" in STYLE, "缺少纸页容器 .jpages"
    assert ".jpages .jpage" in STYLE, "缺少单页 .jpages .jpage"
    rule = re.search(r"\.jpages \.jpage\s*\{([^}]*)\}", STYLE)
    assert rule, "无法提取 .jpages .jpage 规则"
    body = compact(rule.group(1))
    assert "height:1300px" in body, "页高必须为 1300px（A4 比例）"
    assert "overflow:hidden" in body, "纸页需隐藏溢出"
    assert "column-count:2" in body, "每页双栏"


def test_css_keeps_images_and_code_unbroken():
    """图片通栏、代码块不跨页，避免被栏线/页边界切断。"""
    c = compact(STYLE)
    assert "p:has(img)" in c, "含图片段落需通栏"
    assert "break-inside:avoid" in c, "代码块等需禁止跨页拆分"


def test_config_references_paginate_engine():
    """Earth 的 config.json 必须重新加载分页引擎。

    注意：本仓库（Emeek）不含 config.json，该断言在 Earth 侧校验，
    此处仅校验模板不再主动移除 #postBody 容器。
    """
    assert 'id="postBody"' in POST, "模板必须保留 #postBody 供引擎接管"
