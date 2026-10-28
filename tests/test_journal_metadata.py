"""期刊元数据提取与合并的契约测试。

验证两条接口的优先级行为：
- extract_journal_meta(markdown) -> (meta, body)：从文章正文提取并剥离 Gmeek 元数据块
- merge_journal_meta(article, config, issue) -> dict：文章 > 配置 > Issue 的字段归并
"""

from Gmeek import extract_journal_meta, merge_journal_meta


def test_extracts_and_removes_strict_gmeek_meta_block():
    source = """# Title

<!-- gmeek-meta
{"author":"郑郑","keywords":["GFM","期刊"]}
-->

正文段落。
"""
    meta, body = extract_journal_meta(source)
    assert meta == {"author": "郑郑", "keywords": ["GFM", "期刊"]}
    assert "gmeek-meta" not in body
    assert "正文段落" in body


def test_malformed_meta_is_ignored_without_losing_body():
    source = """<!-- gmeek-meta
{"author":
-->
正文。
"""
    meta, body = extract_journal_meta(source)
    assert meta == {}
    assert "正文" in body


def test_article_metadata_precedes_config_and_issue_fallbacks():
    merged = merge_journal_meta(
        {"author": "单篇作者", "keywords": ["单篇关键词"]},
        {"journalAuthor": "全局作者", "journalKeywords": ["全局关键词"]},
        {"author": "Issue 作者", "labels": ["标签关键词"]},
    )
    assert merged["author"] == "单篇作者"
    assert merged["keywords"] == ["单篇关键词"]


def test_missing_metadata_uses_config_then_issue_and_hides_empty_fields():
    merged = merge_journal_meta(
        {},
        {
            "journalAuthor": "全局作者",
            "journalAffiliation": "单位",
            "journalFund": "",
            "journalIgnoredLabels": ["draft"],
        },
        {"author": "Issue 作者", "labels": ["draft", "技术"]},
    )
    assert merged["author"] == "全局作者"
    assert merged["affiliation"] == "单位"
    assert merged["fund"] is None
    assert merged["keywords"] == ["技术"]