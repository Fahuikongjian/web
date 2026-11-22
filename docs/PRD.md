# 产品需求文档（PRD）：《ASTRA YAO · 星环手记》独立数字唱片与技术出版物

## 1. 产品概述与定位

### 1.1 产品名称与愿景
- **站点名称**：ASTRA YAO · 星环手记
- **域名与身份**：`astrayao`（示例生产域名 `https://astrayao.com`，部署时可按实际注册后缀替换）
- **核心定位**：立足上海的个人独立技术随笔与数字唱片出版空间（Editorial Vinyl Press & Portfolio）。
- **设计哲学**：以《绝区零》天琴座歌姬 **耀嘉音（Astra Yao）** 的视觉特征为灵感，融汇 **Starloop Velvet & Vinyl（复古红黑金唱片期刊美学）** 与 **慢软件（Slow Software）** 工程原则——默认呈现克制深邃的星环暗夜丝绒剧场，兼具象牙典藏日间模式、720px 高可读性长文排版与零第三方前端构建依赖。

### 1.2 目标受众与核心价值
- **目标读者**：软件工程师、前端与排版设计师、关注独立博客视觉辨识度与单机云主机运维的开发者。
- **核心价值**：
  1. **唱片期刊级的品牌辨识度**：首页以全屏抽象封面开场，随滚动露出文章、项目和关于入口。关于页配备 1:1 天琴座黑胶星徽（`astra-portrait.jpg`），全站以黑曜丝绒、绯红聚光与香槟金发丝线统领。
  2. **沉浸式中文长文阅读体验**：针对汉字视觉密度专门调校字体栈、行距、720px 栏宽、Pygments 语法高亮与右侧粘性文章目录（TOC）。
  3. **离线与国内极速访问**：100% 本地自包含字体栈、原生 JS 交互与本地插画/SVG 资产，无任何境外 CDN 阻断。
  4. **完全自主的内容与构建主权**：内容以纯文本 Markdown + JSON 存储在本地仓库，通过 Python 3.13 标准库构建为纯静态目录 `dist/`，可直接部署于阿里云华东 2（上海）ECS。

### 1.3 严格非功能性约束（设计红线）
1. **视觉克制与品牌纯度**：严禁出现与主题无关的俗套紫蓝霓虹渐变、无意义玻璃拟态卡片堆砌或第三方占位图；星环红黑金点缀与舞台光晕必须克制且保证正文高对比度可读。
2. **极简技术栈**：构建、测试与部署脚本仅允许使用 Python 3.13 标准库、`Pygments`、`pytest`、`playwright`（配合本地 Chrome），**禁止使用 `node` / `npm` / `pnpm` / `git` 及未安装的三方 Python 包（如 `markdown` / `jinja2` / `pyyaml`）**。
3. **响应式零溢出**：所有页面在桌面端（`1440×900`）、平板（`<= 1024px`）与移动端（`390×844`）均须严格满足 `scrollWidth <= clientWidth`（特别注意舞台光晕与黑胶唱盘边缘在窄屏下的裁切保护）。
4. **合规备案就绪**：页脚预留规范的工信部 ICP 备案信息展示（`沪ICP备XXXXXXXX号-1（备案中）` 链接至 `https://beian.miit.gov.cn/`）。

---

## 2. 信息架构（IA）与页面路由规划

所有站内路由均采用根相对路径（Root-relative URLs），并在静态产物 `dist/` 中以目录索引形式呈现：

| 路由路径 | 输出文件 | 页面职责与核心模块 |
| --- | --- | --- |
| `/` | `dist/index.html` | **首页**采用全屏抽象封面（`starloop-cover.jpg`），滚动后展示文章、项目和关于三个入口 |
| `/articles/` | `dist/articles/index.html` | **文章归档与双层筛选页**：顶部始终展示可扩展大分类栏（`全部` + `categories.json` 及 Frontmatter 自动合并分类）；有文章时按日期倒序陈列并展示 Tag 细筛选胶囊，支持分类 × Tag 二级联动、实时条数更新与 URL `?category=...&tag=...` 同步 |
| `/articles/<slug>/` | `dist/articles/<slug>/index.html` | **文章详情页**：顶部红金渐变阅读进度条、极简元信息头（日期、可点击分类链接、字数、阅读时长及标签胶囊）、封面、居中正文区、右侧粘性 TOC、Pygments 高亮代码块与复制按钮、上下篇导航与延伸阅读 |
| `/projects/` | `dist/projects/index.html` | **项目页**读取 `content/projects.json`，提供状态、年份、简介、技术栈与链接，空列表显示提示 |
| `/about/` | `dist/about/index.html` | **关于与建造说明页**：天琴座黑胶星徽（`astra-portrait.jpg`）、主理人介绍、写作理念、站内 Colophon（建造说明）与 RSS/GitHub/Email 联系渠道 |
| `/404.html` | `dist/404.html` | **自定义 404 页面**：温和优雅的唱片跳针/离轨迷路提示，提供返回首页、浏览归档与唤醒搜索弹窗的快捷入口 |
| `/api/posts.json` | `dist/api/posts.json` | **全量文章元数据 API**：包含全部已发布文章元数据与标签/分类统计 |
| `/api/search-index.json` | `dist/api/search-index.json` | **站内全文检索索引**：供前端 `Cmd/Ctrl+K` 搜索弹窗按需拉取与模糊匹配 |
| `/rss.xml` | `dist/rss.xml` | **RSS 2.0 订阅源**：完整输出文章标题、链接、摘要与发布时间 |
| `/sitemap.xml` | `dist/sitemap.xml` | **站点地图**：列出全部核心路由与文章页绝对 URL（基于 `site_url`） |
| `/robots.txt` | `dist/robots.txt` | **爬虫协议声明**：允许索引并指向 `sitemap.xml` |

---

## 3. 核心交互体验需求

### 3.1 默认暗夜星环与双主题切换（Starloop Night / Ivory Edition）
- **默认主视觉（Starloop Night, `[data-theme="dark"]`）**：当用户本地 `localStorage('blog-theme')` 无历史偏好时，默认启用 `'dark'` 主题——深邃黑曜丝绒底 `#0D0A0C`、舞台深褐黑卡片 `#161114`、象牙主墨 `#FBF5EE`、天鹅绒绯红 `#E12D4B` 与香槟金 `#DFB86B`。
- **日间典藏版（Ivory Collector's Edition, `[data-theme="light"]`）**：象牙宣纸底 `#FAF5F0`、纯白卡片 `#FFFFFF`、深酒褐墨 `#1B1216`、正红 `#C41E3A` 与古铜金 `#A97E2C`。
- **防闪烁机制（Anti-FOUC）**：`<head>` 内联脚本在首屏渲染前读取 `localStorage.getItem('blog-theme')`，未命中时默认写入 `'dark'` 至 `document.documentElement.dataset.theme`。
- **交互控件**：点击 `[data-theme-toggle]` 立即切换 `'dark'` ↔ `'light'`、更新 `localStorage` 与按钮无障碍 `aria-label` 及图标态，刷新页面后状态持久化保持。

### 3.2 首页封面与滚动过渡
- 全屏封面（`/static/images/starloop-cover.jpg`）由绯红舞台光、金色星轨与黑胶纹理组成。滚动时，封面保持原有尺寸并自下而上淡出，三个入口同步从下方升起。过渡进度随滚动位置变化，支持中途停留和反向滚动。
- 点击「向下滑动」可直接到达三个入口。系统开启 `prefers-reduced-motion: reduce` 时，封面与入口按页面顺序展示。

### 3.3 Cmd / Ctrl + K 全局搜索弹窗
- **唤醒方式**：点击导航栏搜索按钮 `[data-search-open]` 或按下键盘快捷键 `Ctrl+K` / `Cmd+K`。
- **加载策略**：仅在首次打开搜索弹窗时请求 `/api/search-index.json` 并缓存于内存，避免影响常规页面首屏加载。
- **检索与键盘体验**：对 `title`、`summary`、`category`、`tags` 与正文 `excerpt` 进行中英文大小写不敏感匹配并对命中词高亮；支持 `↑` / `↓` 选中切换（`.is-selected`）、`Enter` 跳转、`Escape` 或点击遮罩关闭。

### 3.4 文章归档页双层分类×标签筛选与阅读页辅助
- **可扩展大分类栏（`/articles/`，始终可见）**：
  - 顶部 `.category-bar` 即使在 0 篇文章时也常驻展示 `全部` 与 `content/categories.json` 预设分类（`代码`、`图像生成`、`工程`），并自动并入文章 Frontmatter 中出现的新分类。
  - 点击分类 Tab（`[data-filter-category]`）时，激活指示条（`.category-indicator`）通过 GPU 合成变换丝滑滑动定位、`aria-selected` 同步切换、URL 更新 `?category=...`；窄屏（`<=640px` / `320px` / `280px`）支持平滑横向滚动且严禁页面级横向溢出；空归档切换分类时 `.empty-stage` 呈现轻柔星环交叉淡入反馈。
- **细小 Tag 标签二级联动（仅存在文章时渲染）**：
  - 点击 `[data-filter-tag]`（含 `"all"`）在当前选中大分类范围内进一步过滤文章行（`[data-category][data-tags]`），并动态刷新当前分类下各 Tag 胶囊的可用性与计数（切换分类导致原 Tag 不可用时自动回退 `tag = 'all'`）。
  - 筛选命中文章行以错峰交错动效（`.is-entering`）呈现，更新 `[data-articles-count]` 与空态 `[data-articles-empty]`，并双向同步 `?category=...&tag=...`（支持行内分类/标签按钮及文章详情页分类链接带参跳入）。所有动效完整响应 `prefers-reduced-motion: reduce`。
- **文章阅读页辅助**：`/articles/<slug>/` 头部提供可点击跳回分类筛选页的分类链接、极简时长展示（`{{post_reading_time}} 分钟`）、顶部阅读进度条 `[data-reading-progress]`、右侧目录 `IntersectionObserver` 滚动高亮 `.toc-link.is-active` 与 `.code-copy-btn` 复制反馈。

---

## 4. 内容状态与扩展方式

- **大分类预设与零配置扩展**：`content/categories.json` 定义默认大分类顺序与抽象图标映射（`代码`、`图像生成`、`工程`）。后续可通过向 `content/categories.json` 追加条目，或在任意新文章 Frontmatter 中直接填写 `category: 新分类` 自动合并扩展。
- **当前文章与项目状态**：默认空仓库状态下文章归档与项目页为空态展示（文章页大分类栏仍保持可交互）；发布新文章至 `content/posts/*.md` 后自动纳入大分类、Tag 统计与搜索索引，项目追加至 `content/projects.json` 后进入 `/projects/`。

---

## 5. 发布与质量验收标准（Definition of Done）

1. **后端单元测试全绿**：`pytest tests/test_backend.py` 100% 通过。
2. **全站门禁校验通过**：`python scripts/check.py` 退出码为 `0`（构建成功、核心页面/API/XML 与静态图片资产齐全、零未替换 `{{...}}` 占位符、站内链接 0 死链、JSON/XML 语法合法）。
3. **浏览器端到端验收全绿**：`pytest tests/test_e2e_browser.py` 通过（全路由 200 / 404 状态码、`console.error == []`、`pageerror == []`、静态 `.jpg`/`.svg`/`.css`/`.js` 资源零失败、`1440×900` / `390×844` / `320×568` / `280×653` 全视口零横向溢出、大分类空态与多分类×Tag 联动、URL 参数还原、主题切换持久化、搜索、TOC/代码复制全功能验证通过）。
4. **视觉审美最终签字**：由 UI/UX 设计师逐一审阅最新归档大分类×Tag（Dark/Light/空态/移动端）与详情页分类标签截图并签字通过。
