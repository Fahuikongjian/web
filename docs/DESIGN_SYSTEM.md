# 设计系统与前后端 DOM/CSS 契约（DESIGN_SYSTEM）

> **出版物美学定位**：**Astra Yao — Starloop Velvet & Vinyl（星环绒夜 × 黑胶唱片期刊美学）**
> 以《绝区零》天琴座歌姬耀嘉音（Astra Yao）的复古红黑金美学为核心灵感：黑曜丝绒（`#0D0A0C`）作底、深红丝绒（`#E12D4B`）作点睛、香槟金线（`#DFB86B`）作装帧边栏与天琴座星光（`✦`），并保留优雅明亮的象牙白典藏版日间模式（Ivory Collector's Edition）。严禁紫蓝霓虹渐变与千篇一律的 SaaS 卡片堆砌。

---

## 1. 静态资产清单（`ui-designer` 维护 CSS/SVG；禁止覆盖 `.jpg`）

| 文件路径 | 职责说明 |
| --- | --- |
| `static/css/tokens.css` | 默认暗色（Starloop Night）与日间（Ivory Collector's Edition）色彩令牌、离线字体栈与标尺 |
| `static/css/base.css` | 盒模型复位、无障碍焦点环、Skip Link、容器尺寸与 `prefers-reduced-motion` 保护 |
| `static/css/components.css` | 粘性顶栏、唱片曲目行、搜索弹窗、TOC 与响应式断点 |
| `static/css/home-cover.css` | 首页全屏封面、滚动过渡和响应式入口卡片 |
| `static/css/prose.css` | `.prose` 长文排版、红金阅读进度条、代码块与丝绒/象牙双主题 Pygments 高亮、表格与脚注 |
| `static/images/starloop-cover.jpg` | **首页抽象封面（1120×1400, 4:5）**：由绯红舞台光、金色星轨与黑胶纹理组成，用于首页全屏开场 |
| `static/images/astra-portrait.jpg` | **定制保留资产（640×640, 1:1）**：关于页天琴座黑胶×金色五线谱×话筒徽章图（任何人不得覆盖或删除） |
| `static/images/favicon.svg` | 黑曜金边黑胶唱片与四角星芒站点图标（64×64） |
| `static/images/author-mark.svg` | 黑曜石 × 炽红 × 香槟金天琴座黑胶徽章备份矢量图（160×160） |
| `static/images/cover-01.svg` ~ `cover-05.svg` | 5 篇原创文章专属复古黑胶期刊矢量封面（统一 800×480 / 5:3 比例） |

---

## 2. 双主题色彩系统（默认 `[data-theme="dark"]`）

CSS 引入顺序严格保持：`tokens.css` → `base.css` → `components.css` → `prose.css`。

| 语义角色 | CSS Token | Dark 默认（Starloop Night） | Light（Ivory Collector's） | 用途 |
| --- | --- | --- | --- | --- |
| 主纸面/夜幕 | `--bg-paper` | `#0D0A0C` | `#FAF5F0` | 页面全局底色 |
| 卡片纯面 | `--bg-card` | `#161114` | `#FFFFFF` | 卡片、搜索框、控制条底色 |
| 暖暗次面 | `--bg-warm` | `#1F171B` | `#F2E9E1` | 引用块、标签胶囊、表头、行悬停 |
| 粘性顶栏 | `--bg-header` | `rgba(13,10,12,0.86)` | `rgba(250,245,240,0.88)` | 顶部毛玻璃导航背景 |
| 主文字墨 | `--ink-primary` | `#FBF5EE` | `#1B1216` | 标题、正文 |
| 次文字墨 | `--ink-secondary` | `#C8B9B2` | `#5D4B51` | 副标题、摘要、导航项 |
| 弱化文字 | `--ink-muted` | `#8E7B75` | `#8E7A80` | 辅助元数据、分隔符 |
| 炽红点缀 | `--accent` | `#E12D4B` | `#C41E3A` | 主 CTA、激活筛选、进度条起点、ON AIR 灯 |
| 炽红浅底 | `--accent-soft` | `rgba(225,45,75,0.16)` | `rgba(196,30,58,0.09)` | 搜索选中行、文本选区、状态胶囊 |
| 香槟金饰 | `--gold` | `#DFB86B` | `#A97E2C` | 边角星芒 `✦`、内框细线、等化器律动柱 |
| 香槟金字 | `--gold-text` | `#DFB86B` | `#855E16` | 小字号金字标签/日期/kicker（保证 ≥ 4.5:1 对比度） |
| 细发丝线 | `--border-hairline` | `rgba(223,184,107,0.14)` | `rgba(169,126,44,0.20)` | 区块边界、列表线、卡片描边 |
| 强发丝线 | `--border-strong` | `rgba(223,184,107,0.30)` | `rgba(169,126,44,0.38)` | 悬停边框、搜索弹窗外框、表格头底线 |

---

## 3. 字体栈与排版规范

- `--font-serif`: `"Songti SC", "Noto Serif SC", "Source Han Serif SC", "STSong", Georgia, serif;`
- `--font-sans`: `"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei UI", -apple-system, BlinkMacSystemFont, sans-serif;`
- `--font-mono`: `"JetBrains Mono", "Cascadia Code", Consolas, monospace;`（数字、年份、阅读时长启用 `font-variant-numeric: tabular-nums`）。
- 长文正文：`1.0625rem`、`line-height: 1.85`、单栏 `720px`、`overflow-wrap: break-word`；表格内代码 `.prose th code, .prose td code { white-space: nowrap; }` 避免标识符被断行。

---

## 4. 新版核心组件 DOM 与 CSS 类名契约（供 `@fe-engineer` 对齐）

### 4.1 主题默认与防闪烁

- `templates/base.html` 内联脚本与 `static/js/theme.js`：**当 `localStorage.getItem('blog-theme')` 为空时，默认主题设为 `'dark'`**（Starloop Night），支持 `'dark'` ↔ `'light'` 双向切换与持久化。
- `.theme-toggle[data-theme-toggle]` 内置 `.icon-sun` 与 `.icon-moon`，CSS 根据 `[data-theme="dark"]` 自动显隐，零闪烁。

### 4.2 首页全屏封面与四栏导航入口（`templates/home.html` & `static/css/home-cover.css`）

- `.home-cover` 使用抽象黑胶封面与渐变遮罩，随滚动由下往上淡出。
- `.home-entries` 升级为 4 栏入口（`文章` `.home-entry--articles`、`项目` `.home-entry--projects`、`图像` `.home-entry--gallery`、`关于` `.home-entry--about`）：
  - 夜间以暗红光晕、金色星轨（`.home-entry-orbits`）和星芒围绕 4 枚入口；日间（`[data-theme="light"]`）保持隐藏 `.home-entry-orbits`，采用象牙白底、白色卡面和淡金角线。
  - **严格视口几何**：桌面 `1440×900` 4 列横排错落琴键韵律（卡间间隙 ≥ 40px）；竖屏 `390×844` 与 `320×568` 单列 4 卡（`min-height: clamp(3.6rem, 10.5svh, 5rem)`、`gap: clamp(1rem, 2.8svh, 1.75rem)`，总底边稳落视口内且间距 ≥ 14px）；横屏 `568×280` 4 列单行（`min-height: clamp(5.25rem, 32svh, 8.25rem)`、`gap: clamp(0.95rem, 2.8vw, 2rem)`，零横向溢出）。
- **首页第 4 入口 `.home-entry--gallery` 抽象棱镜星环 SVG 图标（`viewBox="0 0 48 48"`）**：
  ```html
  <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <ellipse cx="24" cy="24" rx="20" ry="7.2" transform="rotate(-24 24 24)" opacity="0.58"/>
    <path d="M24 7.5L38.5 24L24 40.5L9.5 24Z"/>
    <path d="M16.5 16L31.5 32" opacity="0.38"/>
    <path d="M24 16.5L25.9 22.1L31.5 24L25.9 25.9L24 31.5L22.1 25.9L16.5 24L22.1 22.1Z" fill="var(--accent)" stroke="none"/>
  </svg>
  ```

### 4.3 关于页天琴座徽章框（`templates/about.html`）

```html
<div class="about-portrait-frame">
  <img src="/static/images/astra-portrait.jpg" alt="天琴座黑胶与金色五线谱徽章" width="640" height="640">
</div>
```
放置于 `.about-hero` 左侧（原 `.about-mark` 位置；旧 `.about-mark` 样式继续保留兼容）。

### 4.4 「Starloop Frequency」跨板块双层分类轨道、Tag 筛选与 7 枚抽象 SVG 图标契约

`/articles/`、`/projects/`、`/gallery/` 三个内容板块统一复用「大分类频率轨道（Tier 1）+ 细标签微胶囊（Tier 2）」视觉体系与 60fps 动效语言（保持极简少字，不新增解释性小字）：

#### 1) 大分类轨道 DOM 与类名（常驻于 `.page-body` 顶部）
```html
<div class="category-bar" data-category-bar>
  <div class="category-tabs" data-category-tabs role="tablist" aria-label="分类筛选">
    <span class="category-indicator" data-category-indicator aria-hidden="true"></span>
    <button type="button" class="category-tab is-active" role="tab" aria-selected="true" data-filter-category="all">
      <span class="category-tab-icon" aria-hidden="true"><!-- all SVG --></span>
      <span class="category-tab-label">全部</span>
      <span class="category-tab-count">0</span>
    </button>
    <!-- 其余大类 Tab：role="tab" aria-selected="false" data-filter-category="{{name}}" -->
  </div>
</div>
```
- **滑动指示条协议**：`main.js` 首次定位时先为 `.category-tabs` 添加 `.is-initializing` 禁止过渡，计算当前激活 Tab 的 `offsetLeft`/`offsetWidth` 后写入 `transform: translate3d(<left>px, 0, 0)` 与 `width: <w>px`，为 `.category-indicator` 添加 `.is-ready` 并为 `.category-tabs` 添加 `.has-indicator`（无 JS 时自动回退为 Tab 自身激活底色），下一帧移除 `.is-initializing`。此后切换以 `320ms cubic-bezier(0.22, 1, 0.36, 1)` 60fps 丝滑滑动。
- **移动端防溢出**：`.category-tabs` 启用 `max-width: 100%; overflow-x: auto;` 并隐藏滚动条，在 `390px` / `320px` / `280px` 视口下仅在轨道内部平滑横滑，零页面横向溢出。

#### 2) 7 枚抽象分类 SVG 图标（`16×16`, `viewBox="0 0 18 18"`, `currentColor` 随主题/激活态变色）
- `all`（天琴星环）：`<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true"><ellipse cx="9" cy="9" rx="7.2" ry="3.2" transform="rotate(-22 9 9)" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.72"/><path d="M9 3.6L10.15 7.85L14.4 9L10.15 10.15L9 14.4L7.85 10.15L3.6 9L7.85 7.85Z" fill="currentColor"/></svg>`
- `code`（括号星点）：`<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true"><path d="M6.2 5.2L2.5 9L6.2 12.8M11.8 5.2L15.5 9L11.8 12.8" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 6.6L10.3 9L9 11.4L7.7 9Z" fill="currentColor" fill-opacity="0.85"/></svg>`
- `image`（星光画框）：`<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true"><rect x="2.6" y="3.2" width="12.8" height="11.6" rx="2.2" stroke="currentColor" stroke-width="1.25"/><path d="M3.4 12.6L6.9 9.2L9.6 11.6L11.7 9.8L14.6 12.6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.8"/><path d="M12.2 5.2L12.7 6.5L14 7L12.7 7.5L12.2 8.8L11.7 7.5L10.4 7L11.7 6.5Z" fill="currentColor"/></svg>`
- `engineering`（星环节点）：`<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true"><circle cx="9" cy="9" r="5.6" stroke="currentColor" stroke-width="1.25"/><circle cx="9" cy="9" r="2" fill="currentColor"/><path d="M9 1.8V3.4M9 14.6V16.2M1.8 9H3.4M14.6 9H16.2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`
- `character`（歌姬星冠）：`<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true"><circle cx="9" cy="6.6" r="2.7" stroke="currentColor" stroke-width="1.25"/><path d="M4.2 14.8C4.8 11.9 6.6 10.6 9 10.6C11.4 10.6 13.2 11.9 13.8 14.8" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/><path d="M13.6 2.6L14.15 4.05L15.6 4.6L14.15 5.15L13.6 6.6L13.05 5.15L11.6 4.6L13.05 4.05Z" fill="currentColor"/></svg>`
- `scene`（星环地平）：`<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true"><path d="M2.2 13.8H15.8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-opacity="0.65"/><path d="M3 13.6L7.1 8.5L10.3 11.7L12.6 9.3L15.2 13.6" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M12.4 3.2L12.95 4.65L14.4 5.2L12.95 5.75L12.4 7.2L11.85 5.75L10.4 5.2L11.85 4.65Z" fill="currentColor"/></svg>`
- `default`（天琴星芒，扩展新分类默认）：`<svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true"><circle cx="9" cy="9" r="6.2" stroke="currentColor" stroke-width="1.15" stroke-opacity="0.65"/><path d="M9 4.5L9.9 8.1L13.5 9L9.9 9.9L9 13.5L8.1 9.9L4.5 9L8.1 8.1Z" fill="currentColor"/></svg>`

#### 3) Tag 胶囊、列表项与 60fps 动效类
- **Tag 胶囊与计数条**：`.filter-bar`（以及 `.articles-toolbar` / `.projects-toolbar` / `.gallery-toolbar`）> `.filter-pills` > `.filter-pill[data-filter-tag]`（激活态为克制的香槟金描边柔底 `.is-active` / `aria-pressed="true"`；不可用标签 `.is-hidden`；按压回弹 `scale(0.97)`）+ `.articles-count` / `.projects-count` / `.gallery-count`。
- **文章行**：`article.post-row[data-category][data-tags]`，悬停左侧绯金竖线 `::before` 竖向光扫展开；命中进场附加 `.is-entering` 与 `--stagger-index`；行内 `button.post-row-category[data-filter-category]` 与 `.tag-pill[data-filter-tag]`。
- **项目卡片（`/projects/`）**：`.projects-grid.projects-grid--catalog`（筛选非全量时可加 `.is-filtered` 保持对称双栏）> `article.project-card[data-category][data-tags]`（命中进场 `.is-entering` + `--stagger-index`），顶部 `.project-card-top` 含 `.project-card-meta`（`.project-year` + 可点击 `button.project-category-badge[data-filter-category]`）与 `.project-status`，底部 `.project-stack` 支持可点击 `.tag-pill[data-filter-tag]`。
- **空态切换**：`.empty-stage` 切换空分类时触发 `.is-transitioning`（容器轻柔淡入 + `.empty-stage-mark` 星环微旋呼应）。
- **详情页分类**：`<a class="post-meta-category" href="/articles/?category={{post_category_url}}">{{post_category}}</a>` 内置绯红四角星芒 `::before` 与淡金边框。

### 4.5 图像板块 `/gallery/` 提示词画廊与 Lightbox 契约

- **画廊网格**：`.gallery-grid`（桌面 `>=1025px` 3 列、平板 `641–1024px` 2 列、移动 `<=640px` 1 列；空态复用 `.empty-stage` 仅展示「暂无已发布图像。」）。
- **画廊卡片（`article.gallery-card[data-category][data-tags]`）**：
  - 媒体区 `.gallery-card-media` > `<button type="button" class="gallery-media-btn" data-gallery-open="...">`（`4:3` `object-fit: cover` 图像 + 右下角星芒展开角标 `.gallery-expand-badge`）。
  - 内容区 `.gallery-card-body`：
    - `.gallery-card-head`：`.gallery-card-title` + `.gallery-card-meta`（可点击 `button.gallery-category-badge[data-filter-category]` + 可选 `.gallery-model-chip`）。
    - `.gallery-prompt-box`：两行截断 `font-mono` 的 `.gallery-prompt-preview` + 一键拷贝按钮 `<button type="button" class="prompt-copy-btn" data-copy-prompt>`（成功态 `.is-copied` 金绯微光、失败态 `.is-copy-error`）。
    - `.gallery-card-tags`：紧凑可点击 `.tag-pill[data-filter-tag]`。
  - 筛选入场：`.gallery-card.is-entering` + `--stagger-index`（每张错峰 `45ms` 上浮淡入）。
- **Lightbox 模态窗（`<dialog class="gallery-lightbox" data-gallery-lightbox>`）**：
  - 居中双栏容器 `.gallery-lightbox-shell`（桌面左图舞台 `.gallery-lightbox-stage` `object-fit: contain` + 右信息面板 `.gallery-lightbox-panel`；`<=860px` 切换上下单栏内滚动，零页面溢出）。
  - 右栏结构：`.gallery-lightbox-header`（`.gallery-lightbox-title` + `44×44` `.gallery-lightbox-close[data-gallery-close]`）、`.gallery-lightbox-meta`（分类/模型 `.gallery-model-chip`/参数 `.gallery-param-chip`/日期 `.gallery-date-chip`）、`.gallery-prompt-section`（`.gallery-prompt-header` 含 `.gallery-prompt-label`「Prompt」+ `.prompt-copy-btn`、`<pre class="gallery-prompt-full">`）、可选 `.gallery-negative-section`（`.gallery-prompt-label`「Negative」+ `.prompt-copy-btn` + `<pre class="gallery-prompt-full">`）、底部 `.gallery-lightbox-tags`。
- **减少动态偏好**：`@media (prefers-reduced-motion: reduce)` 全面禁用滑动过渡、卡片入场动画、Lightbox 开启动画、星环脉冲与按压缩放。

### 4.6 其余全站既有契约保持 100% 兼容

- **顶栏/抽屉**：`.site-header`、`.nav-link.is-active`、`.mobile-drawer`
- **搜索弹窗**：`.search-modal[data-search-modal]` > `.search-dialog` > `.search-header`（已清除浏览器原生蓝叉 `::-webkit-search-cancel-button`）+ `.search-results`（`.search-result-item.is-selected`）+ `.search-footer`
- **文章阅读页**：`.reading-progress` > `.reading-progress-bar[data-reading-progress]`、`.post-layout` > `.post-prose.prose` + `.toc-sidebar`（`.toc-details` / `.toc-nav` > `.toc-list` > `.toc-item.toc-level-2/3` > `.toc-link.is-active`）、`.code-block-wrapper > .code-block-header + .highlight`、`.table-wrap > table`、`.post-nav-grid` > `.nav-post-card`
