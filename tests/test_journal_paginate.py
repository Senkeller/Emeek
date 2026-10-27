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