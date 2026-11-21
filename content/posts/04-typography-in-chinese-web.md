---
title: 中文网页排版细节：行距、标点挤压、字族栈与混排节奏
slug: typography-in-chinese-web
date: 2026-11-05
category: 设计与审美
tags: [中文排版, CSS, 字体设计, 可读性]
summary: 中文方块字的高视觉密度要求截然不同的网页排版尺度。本文拆解零外链离线字体栈设计、68ch 黄金栏宽、表格数字对齐与明暗双主题对比度工程。
cover: /static/images/cover-04.svg
featured: false
draft: false
---

绝大多数优秀的开源英文博客模板，一旦直接套上中文文章就会显得局促而凌乱。原因并不复杂：拉丁字母以音素为单位横向拼写，字词之间天然带有空格，字符高低错落（升部与降部形成天然空气感）；而中文则是满框均布的方块字，字面率高、笔画密集，连续成段铺在屏幕上时，整块文字的“灰度”远比英文浓重得多。

如果我们沿用英文网站常见的 `line-height: 1.5` 与宽大字号差，中文段落很快就会变成一堵密不透风的灰色砖墙。要让中文网页读起来有纸质书般的通透呼吸感，必须从字体栈、行高尺度、段间节奏与数字符号对齐四个方面重新标定 CSS 基线。

## 零外链阻塞的离线字体栈

很多中文设计师习惯在页面头部引入外部网络字体（Web Fonts），然而一份完整的中文字体子集动辄数兆字节，遇到网络波动或离线阅读环境，页面要么长时间处于无字白屏（FOIT），要么在加载完成后发生刺眼的字体闪烁重排（FOUT）。

面向技术出版物与独立博客，**充分信任并精心编排系统内置字体栈**，反而能换来瞬时首屏渲染与极佳的屏幕锐度。在 *Paper & Ink* 系统中，我们将字体职责分成三条清晰的轨道：

- **衬线展示字体（`--font-serif`）**：用于大标题、精选导语与引用块装饰，优先匹配 macOS 的 `"Songti SC"`、Linux 常见 `"Noto Serif SC"` / `"Source Han Serif SC"` 与 Windows 的 `"STSong"`，营造书卷与刊物气质。
- **无衬线正文字体（`--font-sans`）**：长文正文仍需高屏幕可辨识度，依次回退 `"PingFang SC"`、`"Hiragino Sans GB"` 与 `"Microsoft YaHei UI"`，确保高分屏与普通显示器都清晰不糊边。
- **等宽技术字体（`--font-mono`）**：用于代码块、目录编号、文章发布日期与标签数量统计，并强制开启 `font-variant-numeric: tabular-nums` 让列表里的年份与月份垂直对齐。

> 好的排版设计不是强行让所有设备显示完全相同的某一款商业字体，而是在不同操作系统的原生字库之上，建立同样优雅稳定的比例、行距与字重关系。

## 中文长文的核心 CSS 尺度

经过反复在不同字号与显示器上的视觉校对，我们把文章正文区域（`.prose`）的基础排版参数收敛成下面这组克制的样式变量：

```css
.prose {
  max-width: 720px;
  margin-inline: auto;
  color: var(--color-ink);
  font-family: var(--font-sans);
  font-size: 1.0625rem; /* 17px：兼顾屏幕清晰度与长文舒适度 */
  line-height: 1.85;
  letter-spacing: 0.015em;
  overflow-wrap: break-word;
}

.prose h2 {
  font-family: var(--font-serif);
  font-size: 1.55rem;
  line-height: 1.38;
  margin-top: 2.6em;
  margin-bottom: 0.85em;
  padding-bottom: 0.45em;
  border-bottom: 1px solid var(--color-border);
  scroll-margin-top: 5.5rem;
}

.prose blockquote {
  margin: 1.75em 0;
  padding: 0.25em 1.25em;
  border-left: 3px solid var(--color-accent);
  color: var(--color-ink-muted);
}
```

### 容易被忽视的锚点跳转偏移

上面这段 CSS 里有一个极易遗漏却影响深远的属性：`scroll-margin-top: 5.5rem`。当页面顶部拥有高度约 `64px` 的粘性导航栏时，如果不给 `h2`、`h3` 设置足够的顶部滚动边距，读者点击右侧目录（TOC）跳转时，目标章节标题就会被导航栏严严实实地遮住一半。一个声明就能彻底根除这种生硬感。

### 中英文混排与行内代码保护

在技术写作中，中文句子里几乎必定夹杂英文术语、路径或函数名。为了让视觉重心保持平稳：

1. 在手动写作时于中文与英文/数字之间保留一个半角空格，例如“使用 `Python 3.13` 构建”，能显著减轻视觉粘连。
2. 为行内 `<code>` 元素设定略小于正文的字号（`0.88em`）、轻微的暖灰底色与 `2px 6px` 内边距，让技术名词自然融入行流，既清晰可辨，又不至于在整段文字里炸出刺眼的色块。
3. 控制代码块容器横向滚动（`overflow-x: auto`），而绝不允许一行长命令撑破整张移动端页面，保证在 `390px` 宽度下依然保持零横向溢出。

排版是一门向读者隐身的工艺。当一篇文章的段落节奏恰到好处、表格与代码块干净利落时，读者几乎不会想起任何一行 CSS 代码的存在，而只记得思想顺畅流动的愉悦。如果你对如何把这套美学贯彻到全站组件感兴趣，不妨回顾 [编辑部美学：如何在网页中重建纸质出版物的克制与秩序](/articles/editorial-web-aesthetics/)。
