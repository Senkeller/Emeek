# -*- coding: utf-8 -*-
"""正文行距契约测试。

需求：正文整体偏松，希望更紧凑。
根因：--journal-body-leading 为 1.7，而项目还原目标《西北工业大学学报》
论文模板实测行距为 1.37 倍（字号 10.4pt，行距 14.2pt）。

本文件锁定该契约，防止行距被误改回宽松值。
"""
from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
STYLE = (ROOT / "static/assets/journal-style.css").read_text(encoding="utf-8")


def _root_token(name):
    """从 :root 块里取出某个 CSS 自定义属性的值。"""
    m = re.search(r":root\s*\{([^}]*)\}", STYLE, re.S)
    assert m, "缺少 :root 令牌块"
    body = m.group(1)
    tm = re.search(re.escape(name) + r"\s*:\s*([^;]+);", body)
    assert tm, f"缺少令牌 {name}"
    return tm.group(1).strip()


def test_body_leading_matches_paper_template():
    """正文行距必须是 1.37 倍。

    来源：《西北工业大学学报》论文模板 PDF 实测：
        正文字号 10.4pt，行距 14.2pt → 14.2 / 10.4 ≈ 1.37

    原值 1.7 比模板松 24%，是「读起来空、一屏字少」的直接原因。
    """
    value = _root_token("--journal-body-leading")
    assert value == "1.37", f"正文行距应为 1.37，实际为 {value}"


def test_paragraph_spacing_is_preserved():
    """段落间距必须保持 0.45em，不随行距一起收紧。

    本文档靠首行缩进 2 字符区分段落（.jpage.markdown-body > p 有 text-indent）。
    段距过小会让段落边界模糊——截图对比确认 0.2em 时上下段几乎连成一片。
    """
    m = re.search(r"\.jpage\.markdown-body > p\s*\{([^}]*)\}", STYLE, re.S)
    assert m, "缺少 .jpage.markdown-body > p 规则"
    body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S).replace(" ", "")
    assert "margin:000.45em" in body, f"段落间距应为 0 0 0.45em，实际为 {body[:80]}"
    assert "text-indent:2em" in body, "段落必须有首行缩进，这是段落边界的主要标记"


def test_code_and_table_leading_unaffected():
    """代码块与表格有独立行距令牌，不应被正文行距改动波及。"""
    value = _root_token("--journal-code-leading")
    assert value == "1.55", f"代码/表格行距应保持 1.55，实际为 {value}"


def test_leading_token_is_referenced_by_page_containers():
    """行距令牌必须同时作用于分页前容器和分页后纸页。

    分页引擎会把 #postBody 替换为 .jpages > .jpage，
    若只有前者引用令牌，分页后行距会回退到默认值。
    """
    # 分页前：.jpage.markdown-body
    m1 = re.search(r"\.jpage\.markdown-body\s*\{([^}]*)\}", STYLE, re.S)
    assert m1, "缺少 .jpage.markdown-body 规则"
    assert "var(--journal-body-leading" in m1.group(1), \
        "分页前容器需引用行距令牌"

    # 分页后：.jpages .jpage
    m2 = re.search(r"\.jpages \.jpage\s*\{([^}]*)\}", STYLE, re.S)
    assert m2, "缺少 .jpages .jpage 规则"
    assert "var(--journal-body-leading" in m2.group(1), \
        "分页后纸页需引用行距令牌，否则分页后行距回退"
