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

### 4.2 首页全屏封面与导航入口（`templates/home.html`）

- `.home-cover` 使用抽象黑胶封面与渐变遮罩，随滚动由下往上淡出。
- `.home-entries` 随滚动从下方升起。金色星轨和星芒围绕三个入口延展，入口边角有独立的金线装饰。桌面宽屏错落横排，手机竖屏单列。

### 4.3 关于页天琴座徽章框（`templates/about.html`）

```html
<div class="about-portrait-frame">
  <img src="/static/images/astra-portrait.jpg" alt="天琴座黑胶与金色五线谱徽章" width="640" height="640">
</div>
```
放置于 `.about-hero` 左侧（原 `.about-mark` 位置；旧 `.about-mark` 样式继续保留兼容）。

### 4.4 其余全站既有契约保持 100% 兼容

- **顶栏/抽屉**：`.site-header`、`.nav-link.is-active`、`.mobile-drawer.is-open`
- **搜索弹窗**：`.search-modal[data-search-modal][hidden]` > `.search-dialog` > `.search-header`（已清除浏览器原生蓝叉 `::-webkit-search-cancel-button`）+ `.search-results`（`.search-result-item.is-selected`）+ `.search-footer`
- **列表与筛选**：`.posts-list` > `.post-row[data-tags]`、`.filter-bar` > `.filter-pill.is-active`、`.projects-grid.projects-grid--catalog`
- **文章阅读页**：`.reading-progress` > `.reading-progress-bar[data-reading-progress]`、`.post-layout` > `.post-prose.prose` + `.toc-sidebar`（`.toc-nav` > `.toc-list` > `.toc-item.toc-level-2/3` > `.toc-link.is-active`）、`.code-block-wrapper > .code-block-header + .highlight`、`.table-wrap > table`、`.post-nav-grid` > `.nav-post-card`
