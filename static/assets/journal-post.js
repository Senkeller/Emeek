/* Journal of Earth post enhancements
   本文件承载文章页的代码增强、目录吸顶与纸页分页引擎，
   由 post.html 在文章页实际加载（config 的 script 与模板兜底双保险）。 */

(function () {
  'use strict';

  /* ================= 代码块增强 ================= */
  function enhanceCodeBlocks() {
    document.querySelectorAll('pre.notranslate').forEach(function (pre) {
      if (!pre.parentElement.classList.contains('snippet-clipboard-content')) {
        var wrapper = document.createElement('div');
        wrapper.className = 'snippet-clipboard-content';
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);
      }
      pre.setAttribute('tabindex', '0');
      pre.setAttribute('role', 'region');
      pre.setAttribute('aria-label', '代码示例，可横向滚动');
    });
  }

  function updateTOC() {
    var toc = document.querySelector('.toc');
    if (!toc) return;
    if (window.innerWidth < 1250) {
      toc.style.position = 'static';
      toc.style.left = 'auto';
      toc.style.right = 'auto';
      toc.style.transform = 'none';
    } else {
      toc.style.position = 'fixed';
      toc.style.left = 'auto';
      toc.style.right = '24px';
      toc.style.transform = 'none';
    }
  }

  /* ================= 纸页分页引擎 ================= */

  // 纸页宽度：双页并排时每页约占 (容器宽 - 页间距24px) / 2，单页则占满容器。
  // 与 CSS 里 .journal-paper 的 grid 轨道宽度保持一致。
  function pageWidth(paper) {
    var twoPage = window.matchMedia('(orientation: landscape) and (min-width: 1000px)').matches;
    return Math.floor((paper.clientWidth - (twoPage ? 24 : 0)) / (twoPage ? 2 : 1));
  }

  // 单一测量源：临时建一个真实的 .jpage 探测元素，让浏览器用共享 CSS
  // 解析出最终生效的纸页几何（高度、留白、栏数、栏距、字体、字号、行高）。
  // 之所以读计算样式而非硬编码：CSS 调整密度时分页测量自动跟随，保证
  // 样式与分页两处永不漂移。读取完立即移除探测元素，避免干扰纸面网格。
  function getLayoutMetrics() {
    var paper = document.getElementById('journalPaper');
    var probe = document.createElement('div');
    probe.id = 'jpage-probe';
    probe.className = 'jpage markdown-body';
    probe.style.position = 'absolute';
    probe.style.visibility = 'hidden';
    probe.style.top = '0';
    probe.style.left = '0';
    probe.style.width = pageWidth(paper) + 'px';
    paper.appendChild(probe);
    var cs = window.getComputedStyle(probe);
    var metrics = {
      pageWidth: probe.getBoundingClientRect().width,
      pageHeight: parseFloat(cs.height) || 780,
      paddingTop: parseFloat(cs.paddingTop) || 0,
      paddingRight: parseFloat(cs.paddingRight) || 0,
      paddingBottom: parseFloat(cs.paddingBottom) || 0,
      paddingLeft: parseFloat(cs.paddingLeft) || 0,
      columnCount: parseInt(cs.columnCount, 10) || 1,
      columnGap: parseFloat(cs.columnGap) || 0,
      fontFamily: cs.fontFamily,
      fontSize: parseFloat(cs.fontSize) || 16,
      lineHeight: parseFloat(cs.lineHeight) || 1.72
    };
    paper.removeChild(probe);
    return metrics;
  }

  // 移动端自然流动判定：与 CSS 的 max-width:720px 断点共用同一份媒体查询，
  // 单一维护点。小屏上不再生成固定纸页，避免固定高度把文字截断。
  function isMobileFlow() {
    return window.matchMedia('(max-width: 720px)').matches;
  }

  // 分页引擎给超高块注入内联限制（maxHeight/overflow）前的原始内联值快照。
  // 元素 -> {maxHeight, overflow}；还原正文时按快照恢复，从而只清掉本引擎
  // 注入的行内样式，文章作者在 Markdown 里自带的内联样式原样保留。
  var engineConstraintSnapshot = new WeakMap();

  // 给超高块施加“独立成页 + 内部滚动”的约束。同一元素只记录一次原始值，
  // 避免多轮分页互相覆盖；非 Element 节点（文本/注释）没有 style，防御跳过。
  function constrainOversizedBlock(el, contentHeight) {
    if (!el || el.nodeType !== 1) return;
    if (!engineConstraintSnapshot.has(el)) {
      engineConstraintSnapshot.set(el, {
        maxHeight: el.style.maxHeight,
        overflow: el.style.overflow
      });
    }
    el.style.maxHeight = Math.max(120, contentHeight - 20) + 'px';
    el.style.overflow = 'auto';
  }

  // 仅恢复分页引擎注入过的内联限制：把 maxHeight/overflow 还原到注入前的
  // 原始值（作者没写内联时即还原为空串，等于去掉这两条行内样式）。
  function releaseEngineConstraints(el) {
    if (!el || el.nodeType !== 1) return;
    if (engineConstraintSnapshot.has(el)) {
      var prev = engineConstraintSnapshot.get(el);
      el.style.maxHeight = prev.maxHeight;
      el.style.overflow = prev.overflow;
      engineConstraintSnapshot.delete(el);
    }
  }

  // 还原子元素：把上一轮已拆进 .jpage 的孩子按原顺序放回 #postBody。
  // 每次重排都从完整正文出发重建，孩子只被移出一次、放回一次，绝不丢内容。
  function restoreBodyContent() {
    var paper = document.getElementById('journalPaper');
    var body = document.getElementById('postBody');
    if (!paper || !body) return;
    var pages = paper.querySelectorAll('.jpage:not(#jpage-probe)');
    for (var i = 0; i < pages.length; i++) {
      var page = pages[i];
      while (page.firstChild) {
        // 放回正文前释放引擎注入的内联限制：桌面切到移动端时，超高块不再
        // 带 maxHeight/overflow，保证移动端 #postBody 自然流式不被行内样式打断
        releaseEngineConstraints(page.firstChild);
        body.appendChild(page.firstChild);
      }
      paper.removeChild(page);
    }
  }

  function paginate() {
    var paper = document.getElementById('journalPaper');
    var body = document.getElementById('postBody');
    if (!paper || !body) return [];

    // 分页前先把旧纸页全部还原回正文容器，保证每轮从完整内容出发
    restoreBodyContent();

    // 移动端：直接自然流动，不生成任何固定纸页
    if (isMobileFlow()) return [];

    var metrics = getLayoutMetrics();
    // 内容净高 = 纸页高 - 上下留白，是判定“是否切页”的唯一标尺
    var contentHeight = metrics.pageHeight - metrics.paddingTop - metrics.paddingBottom;

    // 隐藏测量节点：用与真实纸页相同的宽度/字号/行高/栏数/留白构造，
    // 高度设为自动，逐块放入看 scrollHeight 是否超出净高——超了就得换页。
    var measure = document.createElement('div');
    measure.id = 'jpage-measure';
    measure.style.cssText =
      'position:absolute;visibility:hidden;top:0;left:0;pointer-events:none;box-sizing:border-box;' +
      'width:' + metrics.pageWidth + 'px;' +
      'padding-top:' + metrics.paddingTop + 'px;padding-right:' + metrics.paddingRight + 'px;' +
      'padding-bottom:' + metrics.paddingBottom + 'px;padding-left:' + metrics.paddingLeft + 'px;' +
      'column-count:' + metrics.columnCount + ';column-gap:' + metrics.columnGap + 'px;column-fill:auto;' +
      'font-family:' + metrics.fontFamily + ';font-size:' + metrics.fontSize + 'px;line-height:' + metrics.lineHeight + ';';
    paper.appendChild(measure);

    // 把 #postBody 的全部孩子提出为数组，逐块探测、逐页分配
    var items = [];
    while (body.firstChild) {
      items.push(body.firstChild);
      body.removeChild(body.firstChild);
    }

    var pages = [];        // 已创建的真实纸页
    var page = null;       // 正在填充的当前纸页
    var pageItems = [];    // 已分配给当前纸页、仍留在测量节点里的元素

    // 把当前页累积的元素真正挂到纸页 div 上，清空当前页状态
    function commitPage() {
      if (!page) return;
      for (var k = 0; k < pageItems.length; k++) page.appendChild(pageItems[k]);
      pageItems = [];
      page = null;
    }

    function openNextPage() {
      page = document.createElement('div');
      page.className = 'jpage markdown-body';
      paper.appendChild(page);
      pages.push(page);
    }

    // 至少先开一页，保证空文档也有一个纸页容器
    openNextPage();

    for (var i = 0; i < items.length; i++) {
      var el = items[i];
      measure.appendChild(el);
      pageItems.push(el);
      // 加入该块后累计内容超出净高且非孤块：把它退回，上一页落定，换新页重试
      if (measure.scrollHeight > contentHeight && pageItems.length > 1) {
        measure.removeChild(el);
        pageItems.pop();
        commitPage();
        openNextPage();
        measure.appendChild(el);
        pageItems.push(el);
      }
      // 单块本身超净高（长代码/宽表格/大图）：分页安全优先，绝不裁剪或拆分该块，
      // 而是让整块独立成页，仅对它内部限高并允许滚动查看。
      if (measure.scrollHeight > contentHeight) {
        constrainOversizedBlock(el, contentHeight);
      }
    }
    // 收尾：把最后一页的元素挂上纸页
    commitPage();

    paper.removeChild(measure);
    return pages;
  }

  // 总入口：脚本可能被 config 与模板同时加载，用全局标志保证只初始化一次，
  // 避免分页与事件监听叠加执行。
  function start() {
    enhanceCodeBlocks();
    updateTOC();
    window.addEventListener('resize', updateTOC, { passive: true });
    setupPagination();
  }

  function setupPagination() {
    var paper = document.getElementById('journalPaper');
    var body = document.getElementById('postBody');
    if (!paper || !body) return;

    // 去掉与期刊头题名重复的首个 h1：题名已由 .journal-title 渲染在期刊头部，
    // 正文再保留同一标题会在桌面上重复、显得冗余。此删除在分页前无条件执行，
    // 移动端同样生效，保证 #postBody 自然流式里也只出现一份标题，两处体验一致。
    var first = body.firstElementChild;
    var jt = document.querySelector('.journal-title');
    if (first && jt && first.tagName.toLowerCase() === 'h1') {
      var a = (first.textContent || '').trim().toLowerCase().replace(/\s+/g, '');
      var b = (jt.textContent || '').trim().toLowerCase().replace(/\s+/g, '');
      if (a && (a === b || a.indexOf(b) >= 0 || b.indexOf(a) >= 0)) body.removeChild(first);
    }

    paginate();

    // 窗口尺寸或横竖屏变化后，防抖重分页
    var resizeTimer = null;
    function scheduleRepaginate() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { paginate(); }, 200);
    }
    window.addEventListener('resize', scheduleRepaginate);
    window.addEventListener('orientationchange', scheduleRepaginate);
    var orientationQuery = window.matchMedia('(orientation: landscape)');
    if (orientationQuery.addEventListener) {
      orientationQuery.addEventListener('change', scheduleRepaginate);
    } else if (orientationQuery.addListener) {
      orientationQuery.addListener(scheduleRepaginate);
    }

    // 图片资源加载完成后高度才准确，再重分页校正切页位置
    var imgs = paper.querySelectorAll('img');
    var pending = imgs.length;
    function onImgDone() { if (--pending === 0) paginate(); }
    if (pending === 0) return;
    for (var m = 0; m < imgs.length; m++) {
      if (imgs[m].complete) onImgDone();
      else imgs[m].addEventListener('load', onImgDone);
    }
  }

  // 幂等初始化：无论脚本被加载几次，只有第一次真正注册逻辑
  if (!window.__journalPaginationWired) {
    window.__journalPaginationWired = true;
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', start);
    } else {
      start();
    }
  }
})();
