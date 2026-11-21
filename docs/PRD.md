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
  1. **唱片期刊级的品牌辨识度**：首页以全屏抽象封面开场，随滚动露出站点介绍和文章入口。关于页配备 1:1 天琴座黑胶星徽（`astra-portrait.jpg`），全站以黑曜丝绒、绯红聚光与香槟金发丝线统领。
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
| `/` | `dist/index.html` | **首页**：全屏抽象封面（`starloop-cover.jpg`）、站点介绍与文章入口、ON AIR 状态与站点统计、精选导读、近期文章、精选项目与主题索引 |
| `/articles/` | `dist/articles/index.html` | **文章归档与筛选页**：全量文章按日期倒序陈列，顶部标签胶囊筛选栏（支持 `all` 与 URL `?tag=` 参数初始化自动筛选），实时显示匹配条数 |
| `/articles/<slug>/` | `dist/articles/<slug>/index.html` | **文章详情页**：顶部红金渐变阅读进度条、文章元信息头（分类/日期/字数/阅读分钟数/标签）、星环主题 SVG 封面、居中正文排版区、右侧粘性 TOC、Pygments 高亮代码块及复制按钮、上下篇导航与相关文章推荐 |
| `/projects/` | `dist/projects/index.html` | **精选项目页**：展示 `content/projects.json` 全部舞台作品与开源实验，含状态标识、年份、简介、技术栈标签与直达链接 |
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
- **视觉构成**：全屏封面（`/static/images/starloop-cover.jpg`）由绯红舞台光、金色星轨与黑胶纹理组成。滚动时，封面保持原有尺寸并自下而上淡出，站点标题、介绍和文章入口同步从下方升起。过渡进度随滚动位置变化，支持中途停留和反向滚动。
- **可控与无障碍**：点击「向下滑动」可直接到达站点介绍。系统开启 `prefers-reduced-motion: reduce` 时，封面与介绍按页面顺序展示。

### 3.3 Cmd / Ctrl + K 全局搜索弹窗
- **唤醒方式**：点击导航栏搜索按钮 `[data-search-open]` 或按下键盘快捷键 `Ctrl+K` / `Cmd+K`。
- **加载策略**：仅在首次打开搜索弹窗时请求 `/api/search-index.json` 并缓存于内存，避免影响常规页面首屏加载。
- **检索与键盘体验**：对 `title`、`summary`、`category`、`tags` 与正文 `excerpt` 进行中英文大小写不敏感匹配并对命中词高亮；支持 `↑` / `↓` 选中切换（`.is-selected`）、`Enter` 跳转、`Escape` 或点击遮罩关闭。

### 3.4 文章归档页实时标签筛选与阅读页辅助
- `/articles/` 点击 `[data-filter-tag]`（含 `"all"`）过滤 `[data-tags]` 文章行、更新计数提示并同步 URL `?tag=...`，支持首页标签带参数跳入自动筛选。
- `/articles/<slug>/` 顶部红金渐变阅读进度条 `[data-reading-progress]`、右侧目录基于 `IntersectionObserver` 滚动高亮 `.toc-link.is-active`、代码块 `.code-copy-btn` 点击复制并显示 `"已复制"` 状态反馈。

---

## 4. 首期内容清单与状态

### 4.1 首批原创专栏文章（5 篇）
1. **《编辑部美学：如何在网页中重建纸质出版物的克制与秩序》**（`editorial-web-aesthetics` · `设计与审美` · `featured: true` · 含 `html` 代码块，阐释红黑金唱片期刊美学）
2. **《从域名到独立服务器上线：阿里云 ECS、Nginx 与 ICP 备案实战手记》**（`from-domain-to-live-site` · `运维与上线` · 含 `nginx` 代码块与缓存矩阵表）
3. **《零重型依赖的静态站引擎：用 Python 3.13 标准库写透内容构建管线》**（`python-static-architecture` · `系统架构` · 含 `python` 代码块与模块架构表）
4. **《中文网页排版细节：行距、标点挤压、字族栈与混排节奏》**（`typography-in-chinese-web` · `设计与审美` · 含 `css` 代码块）
5. **《慢软件随笔：在算力过剩的时代写一组十年后依然能跑的代码》**（`notes-on-slow-software` · `技术随笔` · 含 `bash` 代码块）

### 4.2 精选项目（5 项，首页展示前 3 项）
- 星环静态出版引擎 (`Starloop Press`) — `已开源`
- Starloop Velvet & Vinyl 视觉系统 — `进行中`
- 天琴座中文排版标尺 (`Lyra CJK Ruler`) — `实验中`
- astrayao 阿里云 ECS 单机静态部署套件 — `已开源`
- 慢软件十年维护检查表 (`Side B Notes`) — `进行中`

---

## 5. 发布与质量验收标准（Definition of Done）

1. **后端单元测试全绿**：`pytest tests/test_backend.py` 100% 通过。
2. **全站门禁校验通过**：`python scripts/check.py` 退出码为 `0`（构建成功、核心页面/API/XML 与静态图片资产齐全、零未替换 `{{...}}` 占位符、站内链接 0 死链、JSON/XML 语法合法）。
3. **浏览器端到端验收全绿**：`pytest tests/test_e2e_browser.py` 通过（全路由 200 / 404 状态码、`console.error == []`、`pageerror == []`、静态 `.jpg`/`.svg`/`.css`/`.js` 资源零失败、Desktop/Mobile 零横向溢出、默认 dark 主题与切换持久化、黑胶开关、搜索、标签筛选、TOC/代码复制全功能验证通过）。
4. **视觉审美最终签字**：由 UI/UX 设计师逐一审阅默认暗夜首页、日间首页、搜索弹窗、文章阅读、项目、关于与 Mobile 首页渲染截图并签字通过。
