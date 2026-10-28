# 期刊排版：从「固定纸页分页」改为「连续滚动 + 分节双栏」

日期：2026-10-28
状态：待批准
前置：已确认方向「屏幕阅读为主」+「分节双栏」

## 一、问题定性

现状把「期刊版式」和「固定纸页分页」绑在一起，而分页层是唯一持续出血的地方：

- 近 30 次提交里 13 次改 `journal-paginate.js`，其中连续 8 个是 `fix(paginate)`
- 分页引擎同时做三件事：测量块高、决定断点、渲染纸页
- 分配单位是「块」且块不可跨页，但真实论文段落必须能跨页断开 → 页脚必然留白 → 反复调参
- `PAGE.height: 780` 在 JS 写死、`height: 780px` 在 CSS 写死，`headerHeight: 32`、`paddingBottom: 34` 是手填估值。样式一动引擎就得重新校准

结论：**删掉分页层，改连续滚动；期刊版式靠 CSS 多栏承担。**

## 二、实测依据（本方案的事实基础）

用 headless Chrome 渲染 Earth 仓库全部 33 篇文章的真实正文 HTML 验证。

### 关键发现 1：浏览器天然在标题处切分栏流

`column-span: all` 的元素会强制打断多栏流。实测恢复所有 h1–h6 的 `column-span: all` 后，33 篇里有 32 篇在每个标题处自动形成独立的双栏版面单元，每组各自「填满左栏 → 进右栏」。**不需要任何分组脚本。**

### 关键发现 2：单个版面单元的高度足够小，不需要回读

| 指标 | 结果 |
|---|---|
| 最高版面单元 | 1345px（仅 1 篇），多数 200–800px |
| 组内两栏都有内容 | 33 篇中 32 篇无「仅右栏」组 |
| 段落跨栏续排 | 实测发生（段落确实会被栏线切开续排）|
| 唯一异常 | `tou-gao-xu-zhi` 文首两张图片段落被栏线切开（图片无法分栏，属浏览器行为边界）|

### 关键发现 3：当前 CSS 在连续滚动下是灾难

`cc9c444`（21:22 提交）把标题的 `column-span: all` 全部删了，改为 `break-after: avoid`。这个改动在**固定页高**模型下是对的（跨栏会让每页碎成「左栏→标题→右栏」），但在**连续滚动**下正好相反：

| CSS 状态 | `jiao-nian-ji` 实测 | 结果 |
|---|---|---|
| 标题不跨栏（cc9c444 后）| 两栏都满=0 组，仅右栏=23 组 | 内容整块被推到右栏，左栏留空 |
| 标题跨栏（恢复 `column-span:all`）| 两栏都满=27 组，仅右栏=0 组 | 正常 |

`column-fill` 实测为 `balance`（连续媒体下 `auto` 被规范强制当 `balance`），说明**连续滚动下不能依赖 column-fill**，必须靠标题跨栏切分组。

## 三、方案设计

### 3.1 版面模型

```
#journalPaper（纸底、刊头、标题、摘要关键词写在首屏）
  └── #postBody.jpage.markdown-body   ← 连续双栏容器，无固定高度
        ├── h1/h2/... column-span:all  ← 标题通栏，天然切分栏流
        ├── p                          ← 段落跨栏续排
        ├── pre/table/figure           ← break-inside:avoid，不拆
        └── ...
```

每个标题之间形成一个「版面单元」：标题通栏 + 该节正文双栏等高。整页连续滚动，无页码，无续页页眉。

### 3.2 分层职责（与现状一致，只是抽掉一层）

| 层 | 文件 | 职责 | 本次改动 |
|---|---|---|---|
| 内容 | Earth Issue | markdown 唯一真源 | 不动 |
| 构建 | `Gmeek.py` | markdown→HTML、journalMeta 合并 | 不动 |
| 模板 | `templates/post.html` | 刊头/题目/摘要/页脚结构 | 删 1 行 |
| 版式 | `journal-style.css` | 纸刊视觉 + 双栏 | 删纸页段、恢复标题跨栏 |
| 分页 | `journal-paginate.js` | 固定页高切分 | **整文件删除** |
| 适配 | `journal-markdown.js` | Mermaid/Alert 改写 | 不动 |

## 四、变更清单

### 4.1 删除文件

| 文件 | 理由 |
|---|---|
| `Emeek/static/assets/journal-paginate.js` | 分页层整体移除 |
| `Earth/static/assets/journal-paginate.js` | 同上（Earth 是构建时覆盖源）|
| `Emeek/tests/test_journal_paginate.py` | 被测对象已删除 |

### 4.2 `Emeek/static/assets/journal-style.css`

**删除**（约 155–207 行整段）：
- `.jpages`
- `.jpages .jpage`（含 `height: 780px` / `overflow: hidden` / `column-fill: auto`）
- `.jpages .jpage::after`（页码伪元素）
- `.jpages .jpage:last-child`
- `.jpages .jpage:first-child .cont-masthead`
- `.jpages .cont-masthead` 及其 `.mh-side`
- `.jpages { counter-reset }`
- `.journal-pagination`（页脚页码样式）

**修改**（标题规则，恢复跨栏）：
```css
/* 一级标题：四号黑体，通栏 —— 跨栏强制切分栏流，形成独立版面单元 */
.jpage.markdown-body h1,
.jpage.markdown-body h2 {
  column-span: all;      /* 从 break-after:avoid 改回 */
  break-after: avoid;    /* 保留，防标题落在单元底部 */
}
.jpage.markdown-body h3 { column-span: all; break-after: avoid; }
.jpage.markdown-body h4,
.jpage.markdown-body h5,
.jpage.markdown-body h6 { column-span: all; break-after: avoid; }
```

**新增**（`#postBody` 容器承担双栏 + 首屏衔接）：
```css
/* 正文容器：连续滚动双栏。不要加 height/max-height——固定高度会重新引入裁切。 */
#postBody.jpage.markdown-body {
  margin-top: 14px;
}

/* 含图片的块必须通栏：图片是行内元素，多栏流里无法跨栏，
   否则一张图被栏线切成左右两半。实测 33 篇中 27 篇有图、84 处图片块，
   加此规则后全部正确通栏（宽度 = 容器全宽）。 */
.jpage.markdown-body p:has(img) {
  column-span: all;
  break-inside: avoid;
  text-align: center;
}
.jpage.markdown-body p:has(img) img {
  display: block;
  margin: 0 auto;
}
/* 裸 a>img（不在 p 内，实测 10 处）：同样通栏 */
.jpage.markdown-body a:has(> img) {
  display: block;
  column-span: all;
  text-align: center;
}
```

> `:has()` 兼容性：Chrome 105+、Safari 15.4+、Firefox 121+。不支持的老浏览器会忽略整条规则，图片退回栏内（现状行为），不会崩版。

**删除**：`[data-color-mode="dark"] .jpages .jpage`（选择器失效）。

其余全部不动：字号令牌、纸刊配色、刊头、题目、摘要关键词、代码块、表格、图表题、文末信息、移动端 media query。

### 4.3 `Emeek/templates/post.html`

删除第 107 行：
```html
<div class="journal-pagination" aria-label="Page number">1</div>
```

`.journal-paper` 保留（作为正文的语义容器，带 `margin-top` 间距）。

### 4.4 `Emeek/tests/test_journal_layout_contract.py`

**删除或改写**：`test_paginated_pages_look_like_individual_paper_sheets`（断言 `.jpages .jpage` 白底/边框/投影/页码伪元素）——被测对象已不存在。

**新增**：`test_continuous_layout_spans_headings_and_avoids_fixed_height`
```python
def test_continuous_layout_spans_headings_and_avoids_fixed_height():
    """连续滚动双栏：标题必须跨栏以切分版面单元，容器不得有固定高度。"""
    # 所有标题跨栏（连续媒体下切分栏流的唯一可靠手段）
    for tag in ["h1", "h2", "h3"]:
        rule = css_rule(f".jpage.markdown-body {tag}")  # 组合规则需特殊处理
        assert "column-span:all" in rule.replace(" ", "")
    # 不得再有固定页高/裁切（回归防护）
    compact = STYLE.replace(" ", "").replace("\n", "")
    assert "height:780px" not in compact
    assert "overflow:hidden" not in compact
```

**新增**：`test_pagination_engine_is_removed`
```python
def test_pagination_engine_is_removed():
    """分页引擎已退役，不得再被模板或配置引用。"""
    assert not (ROOT / "static/assets/journal-paginate.js").exists()
    assert "journal-paginate" not in POST
```

### 4.5 `Earth/config.json`

`script` 字段移除 journal-paginate 引用：
```json
"script": "<script src='/Earth/assets/GmeekTOC.js'></script><script src='/Earth/assets/journal-post.js'></script><script src='/Earth/assets/journal-markdown.js'></script>"
```

### 4.6 `Earth/static/assets/journal-style.css`

同步 Emeek 版本（两份必须一致，否则 `cp -r ./*` 会用旧 CSS 覆盖）。同时补上当前已存在的 3 处漂移：

| 差异 | Emeek（新）| Earth（旧）|
|---|---|---|
| `--journal-code-size` / `--journal-code-leading` 令牌 | 有 | 缺 |
| `hr` margin | `0.7em 0` | `1.2em 0` |
| 表格 font-size/line-height | 用令牌 | 15px 写死 |
| `pre` font-size/line-height | 用令牌 | 12px 写死 |

## 五、风险与边界

| 风险 | 评估 | 缓解 |
|---|---|---|
| 短节只占左栏 | 实测 33 篇中普遍存在（多为 1–3 行小标题），右半边留白 | 论文排版的正常现象，不是缺陷。若介意可后续加「短节自动单栏」，但那会重新引入测量逻辑，不建议 |
| 单一版面单元过高需回读 | 最高 1345px，仅 1 篇；多数 <800px | 可接受。若出现极端长节，作者可按 `##` 拆节 |
| 图片跨栏失败 | **已解决**：实测 27 篇有图文章、84 处图片块，加 `p:has(img){column-span:all}` 后全部通栏，零异常 | 见 4.2 新增规则 |
| 移动端 | 现有 `@media (max-width:720px)` 已设 `column-count:1` | 无需改动 |
| 深色主题 | 删掉一条失效选择器 | 需确认 `.jpage.markdown-body` 的 dark 规则覆盖正文 |

## 六、验收标准

1. `journal-paginate.js` 在 Emeek 和 Earth 中均不存在
2. `Earth/config.json` 的 `script` 不再引用 journal-paginate
3. 所有 h1–h6 恢复 `column-span: all`
4. CSS 中不再有 `height:780px` / `overflow:hidden` / `.jpages` / `.cont-masthead` / `.journal-pagination`
5. `templates/post.html` 不再有 `journal-pagination` div
6. `pytest tests/` 全绿（`test_journal_metadata.py` 需先装 `PyGithub`，或用 `--ignore`）
7. 桌面端（>720px）正文双栏，标题通栏，连续滚动无页码
8. 移动端（≤720px）单栏自然滚动
9. 真实文章实测：任意一篇在浏览器中，每个节的两栏都有内容（「仅右栏」= 0）
10. 含图文章的图片全部通栏（宽度 = 容器全宽，未被栏线切开）
11. Emeek 与 Earth 的 `journal-style.css` 完全一致（`diff` 无输出）

## 七、执行顺序

1. 先写失败测试（4.4 的两条新测试）→ 跑，确认失败
2. 改 CSS（4.2）→ 跑测试，确认标题跨栏断言通过
3. 删分页引擎（4.1）、改模板（4.3）、改 config（4.5）
4. 同步 Earth 的 CSS（4.6）
5. `diff` 校验两份 CSS 一致
6. headless Chrome 抽查 3 篇真实文章的 DOM 布局
7. 提交

## 八、已确认决策

1. **图片跨栏**：本次解决，用 `p:has(img)` + `a:has(>img)` 通栏。已实测 33 篇全部通过。
2. **`.journal-paper` 容器**：保留。它现在是语义容器、无样式，未来若需加边框/间距有落点，模板改动最小（只删页码那一行）。
3. **是否顺带合并 `journal-markdown.js`**：留到下一轮。本次不扩大改动范围。
