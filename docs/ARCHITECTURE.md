# 系统架构与前后端数据契约（ARCHITECTURE）

## 1. 技术选型与环境约束

| 层级 | 选型方案 | 约束说明 |
| --- | --- | --- |
| 运行与构建语言 | Python 3.13 标准库 | 仅使用标准库（`json`, `pathlib`, `re`, `html`, `math`, `shutil`, `urllib.parse`, `xml.etree.ElementTree`, `http.server` 等） |
| 语法高亮 | `Pygments 2.21.0` | 唯一内容渲染第三方依赖；禁用 `markdown` / `jinja2` / `pyyaml` |
| 前端技术 | 原生 HTML5 + CSS Tokens + Vanilla ES6 JS | 零 Node/npm/pnpm 构建链、零外部 CDN（字体/脚本/图片全本地化） |
| 质量与测试 | `pytest 9.1.1` + `playwright` (本地 Chrome) | 端到端测试进程内启动 `ThreadingHTTPServer` 预览 `dist/` |
| 生产托管 | GitHub Pages（首发） / 阿里云华东 2 ECS（可选迁移） | 纯静态目录 `dist/` 部署，支持根域名与 `/<repo>` 子路径，`.github/workflows/deploy-pages.yml` 自动构建发布 |

---

## 2. 目录结构与职责边界

```text
d:\网页运营\
├── docs/                       # 产品、架构、设计与测试报告文档
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DESIGN_SYSTEM.md
│   └── QA_REPORT.md
├── content/                    # 纯文本站点配置与内容源（Single Source of Truth）
│   ├── site.json
│   ├── categories.json         # 文章可扩展大分类注册表（代码、图像生成、工程）
│   ├── project_categories.json # 项目可扩展大分类注册表（应用、工具、视觉）
│   ├── gallery_categories.json # 图像可扩展大分类注册表（角色、场景、视觉）
│   ├── projects.json           # 项目数据源（生产保持 []）
│   ├── gallery.json            # 图像与提示词数据源（生产保持 []）
│   ├── about.md
│   └── posts/                  # 文章 Markdown 目录（生产保持为空）
├── templates/                  # 原生 {{key}} 占位符 HTML 模板（无 Jinja2 语法）
│   ├── base.html
│   ├── home.html
│   ├── articles.html
│   ├── post.html
│   ├── projects.html
│   ├── gallery.html
│   ├── about.html
│   ├── 404.html
│   └── partials/
│       ├── articles_list.html
│       ├── post_row.html
│       ├── projects_list.html
│       ├── project_card.html
│       ├── gallery_list.html
│       ├── gallery_card.html
│       └── nav_post_card.html
├── static/                     # 静态资产（构建时完整拷贝至 dist/static/）
│   ├── css/                    # tokens.css, base.css, components.css, home-cover.css, prose.css
│   ├── js/                     # theme.js, search.js, post.js, home-cover.js, gallery.js, main.js
│   └── images/                 # starloop-cover.jpg, astra-portrait.jpg, favicon.svg, author-mark.svg, hero-art.svg, cover-01..05.svg
├── backend/                    # Python 静态构建引擎
│   ├── __init__.py
│   ├── content_loader.py
│   ├── markdown_engine.py
│   ├── renderer.py
│   └── feeds.py
├── scripts/                    # 命令行入口脚本
│   ├── build.py                # 清理并生成 dist/
│   ├── serve.py                # 本地静默静态预览服务（含 404 状态回退）
│   └── check.py                # 全量构建校验与死链门禁脚本
├── deploy/                     # 生产部署套件（GitHub Pages 首发 + 阿里云 ECS 备用）
│   ├── GITHUB_PAGES_GUIDE.md
│   ├── nginx.conf
│   ├── Caddyfile
│   ├── deploy.sh
│   └── DEPLOY_GUIDE.md
├── .github/workflows/
│   └── deploy-pages.yml        # GitHub Actions 自动校验并发布 dist/ 到 GitHub Pages
├── requirements.txt            # CI 最小依赖声明（Pygments>=2.18.0）
├── tests/                      # 自动化测试套件
│   ├── conftest.py
│   ├── test_backend.py
│   └── test_e2e_browser.py
└── dist/                       # 构建输出产物目录（由 build.py 全量清理重建，含 .nojekyll 与可选 CNAME）
```

> **静态图像资产**：构建脚本将 `static/images/starloop-cover.jpg`（1120×1400，首页抽象封面）与 `static/images/astra-portrait.jpg`（640×640，关于页天琴座星徽）复制到 `dist/static/images/`。

---

## 3. URL 规范、路由映射与子路径适配

1. **源码与内容层统一使用根相对路径**（以 `/` 开头，不带域名、不使用 `../`）：
   - 样式与脚本：`/static/css/tokens.css`、`/static/js/theme.js`
   - 本地图像与矢量资源：`/static/images/starloop-cover.jpg`、`/static/images/astra-portrait.jpg`、`/static/images/favicon.svg`、`/static/images/cover-01.svg`
   - 页面路由：`/`、`/articles/`、`/articles/<slug>/`、`/projects/`、`/gallery/`、`/about/`
   - 数据与订阅：`/api/posts.json`、`/api/projects.json`、`/api/gallery.json`、`/api/search-index.json`、`/rss.xml`、`/sitemap.xml`
2. **GitHub Pages 子路径自动重写（`base_path`）**：
   - 当部署至 `https://<user>.github.io/<repo>/` 等子路径时，通过 `--base-path "/<repo>"` 触发构建期重写，源码内容与模板自身仍保持干净的根相对路径。
   - `normalize_base_path(raw)` 规范化输入（空或 `"/"` 返回 `""`，否则返回 `"/<trimmed>"`）。
   - `apply_base_path_to_html(html_text, base_path)` 将 HTML 属性中的根相对 `href="/..."` 与 `src="/..."`（排除协议相对 `//...` 及已带 `base_path` 前缀的路径；`href="/"` 转为 `href="{base_path}/"`）统一加上 `base_path` 前缀，**同时跳过 `<pre>...</pre>` 与 `<code>...</code>` 内部正文以免破坏代码展示**。
3. **绝对 URL 使用场景**。`rss.xml`、`sitemap.xml`、`robots.txt` 和 `<link rel="canonical">` 使用 `site_url` 与页面路径生成绝对 URL。当前配置为 `https://astrayao.xyz`，GitHub Pages 工作流使用部署域名和 `base_path` 覆盖此值。构建时会统一处理子路径前缀。
4. **零死链约束**：任何写入模板、Markdown 正文或 JSON 配置中以 `/` 开头的站内路径（排除 `//` 协议相对外链），在剥离可选 `base_path` 后于 `dist/` 下必须能解析为对应的文件或 `<dir>/index.html`。

---

## 4. 内容层数据契约

### 4.1 `content/site.json` 契约
必须为合法 UTF-8 JSON 对象，包含以下全部字段：

| 字段名 | 类型 | 说明与当前约定值 |
| --- | --- | --- |
| `site_title` | `string` | 站点全称：`"ASTRA YAO · 星环手记"` |
| `site_tagline` | `string` | 站点副标题：`"以星光与黑胶的节拍，记录网页美学、简洁架构与慢技术日常"` |
| `site_url` | `string` | 生产站点地址为 `"https://astrayao.xyz"`，末尾省略 `/` |
| `author_name` | `string` | 作者署名：`"Astra Yao"` |
| `author_role` | `string` | 作者身份头衔 |
| `author_location` | `string` | 所在地：`"中国 · 上海"` |
| `author_bio` | `string` | 作者简介 |
| `icp_number` | `string` | 备案状态文案：GitHub Pages 托管期间置空 `""`（页脚不输出占位符）；切回大陆 ECS 时填回正式备案号 |
| `icp_url` | `string` | 工信部备案查询链接：`"https://beian.miit.gov.cn/"` |
| `custom_domain` | `string` | 可选自定义域名（如 `""` 或 `"astrayao.com"`），非空或传入 `--cname` 时自动写入 `dist/CNAME` |
| `social_links` | `list[object]` | 每项包含 `name`、`label`、`url` |

### 4.2 可扩展大分类注册表家族与合并契约
三个内容板块各自拥有独立的可扩展 JSON 注册表，即使站内尚无内容条目也常驻展示顶部大分类栏：

| 板块 | 注册表文件 | 预设大分类与图标映射 |
| --- | --- | --- |
| 文章 (`/articles/`) | `content/categories.json` | `代码` (`code`), `图像生成` (`image`), `工程` (`engineering`) |
| 项目 (`/projects/`) | `content/project_categories.json` | `应用` (`code`), `工具` (`engineering`), `视觉` (`image`) |
| 图像 (`/gallery/`) | `content/gallery_categories.json` | `角色` (`character`), `场景` (`scene`), `视觉` (`image`) |

**后端通用加载与合并规则（`backend/content_loader.py`）**：
1. **`load_categories_file(path)` / `load_categories(content_dir)` / `load_project_categories(content_dir)` / `load_gallery_categories(content_dir)`**：读取并规范化对应 JSON 文件；若文件不存在则平稳返回 `[]`。每项提取 `id`、`name`、`icon`。
2. **`compute_category_stats(items, configured_categories=None)`**：
   - 兼容属性访问与字典访问（支持 `Post`、规范化后的项目字典与图像字典）。
   - 先按 `configured_categories` 顺序输出全部预设大类，统计每个分类下的条数（无条目时保留 `count: 0`）。
   - 再遍历内容条目的 `category` 字段：若出现注册表未列出的新分类名，则**自动追加**至结果末尾，默认赋予 `icon: "default"`，实现“零配置自动扩展”。
3. **`compute_tag_stats(items)`**：聚合条目的 `tags` 列表计数，按频次降序、标签名升序输出 `[{"name", "count"}]`。
4. **`load_all_content()`**：统一加载 `categories`、`project_categories`、`gallery_categories`，计算并输出 `category_stats`、`project_category_stats`、`project_tag_stats`、`gallery_category_stats`、`gallery_tag_stats`。

### 4.3 `content/projects.json` 契约
必须为 JSON 数组（生产仓库默认保持 `[]`）。`/projects/` 渲染全部项目，数组为空时保留大分类栏并显示「暂无已发布项目。」。每项包含以下字段：
- `name` (`string`): 项目名称
- `status` (`string`): 状态标签（`"进行中"` / `"已开源"` / `"实验中"`）
- `year` (`string`): 年份（如 `"2026"`）
- `summary` (`string`): 一至两句精炼介绍
- `stack` (`list[string]`): 技术栈标签列表
- `url` (`string`): 站内文章路由或外部 `https://` 仓库链接（可选为空字符串）
- `category` (`string`, 可选): 所属大分类（如 `"应用"` / `"工具"` / `"视觉"`，可写任意新分类并自动合并至大分类栏；缺省时为空字符串或按需展示）
- `tags` (`list[string]`, 可选): 细粒度筛选标签列表；**当 `tags` 省略或为空数组时，后端规范化逻辑自动回退使用 `stack`**，确保既有项目数据零改动即可参与二级 Tag 筛选。

### 4.4 `content/gallery.json` 契约（「图像」提示词与效果图 Schema）
必须为 JSON 数组（生产仓库默认保持 `[]`）。`/gallery/` 按 `date` 降序（同日或无日期时保持原始声明次序）渲染全部作品，数组为空时保留大分类栏并显示「暂无已发布图像。」。每项字段规范：

| 字段 | 类型 | 必填 | 说明与默认值 |
| --- | --- | --- | --- |
| `id` | `string` | 推荐 | 唯一标识符，用于 DOM `data-gallery-id`；缺省时由加载器按规范化索引生成唯一 ID |
| `title` | `string` | 是 | 作品标题（极简短题） |
| `image` | `string` | 是 | 效果图路径，推荐根相对路径（如 `"/static/images/..."`），构建时支持 `base_path` 前缀重写 |
| `prompt` | `string` | 是 | 正向生成提示词（支持卡片 2 行预览与一键复制、Lightbox 全文展示与复制） |
| `negative_prompt` | `string` | 否 | 反向提示词，默认 `""`（仅非空时在 Lightbox 展示 `Negative` 区块与复制按钮） |
| `model` | `string` | 否 | 生成模型标识（如 `"Flux.1 dev"` / `"Midjourney v6"`），默认 `""` |
| `params` | `string \| dict` | 否 | 生成参数（如 `"Steps: 28 · CFG: 7.0 · 4:3"` 或键值对象，统一格式化为简洁展示字符串），默认 `""` |
| `category` | `string` | 否 | 所属大分类（如 `"角色"` / `"场景"` / `"视觉"`，支持自动发现新分类），默认 `""` |
| `tags` | `list[string]` | 否 | 细筛选标签数组，默认 `[]` |
| `date` | `string` | 否 | 发布日期（`YYYY-MM-DD`），默认 `""` |

### 4.5 `content/about.md` 契约
- 纯 Markdown 文本文件（无需 Frontmatter，标题层级从 `##` 开始，避免与页面 `<h1>` 冲突）。
- 如文件中以 `---\n` 开头存在可选 Frontmatter，加载器应容错剥离；否则整篇作为 Markdown 正文渲染注入 `{{about_body_html}}`。

### 4.6 `content/posts/*.md` Frontmatter 与文章计算契约
所有博客文章均以 `---` 包裹纯 YAML 简单键值对开头：

```yaml
---
title: 文章标题
slug: article-slug
date: 2026-11-20
category: 设计与审美
tags: [前端审美, 排版, 独立博客]
summary: 一两句精炼的导语摘要
cover: /static/images/cover-01.svg
featured: true
draft: false
---
```

**后端解析与计算规则（`backend/content_loader.py`）**：
1. **字段类型解析**：
   - 布尔值：`true`/`false`（大小写不敏感）解析为 Python `bool`。
   - 列表：`tags` 必须同时支持行内方括号格式 `[标签1, 标签2]` 与标准多行 `- 标签1` 格式，去除项首尾空白与可选引号。
   - 字符串：支持去掉首尾成对单/双引号。
2. **过滤与排序**：过滤所有 `draft is True` 的文章；其余已发布文章按 `date` 降序排列（同日按文件名或 `slug` 稳定次序）。
3. **字数与阅读时间**：
   - 中文字符计数：匹配 `[\u4e00-\u9fff]` 汉字数量。
   - 西文词计数：剔除汉字与代码块符号后匹配 `[A-Za-z0-9_]+` 单词数量。
   - `word_count = cjk_count + latin_word_count`。
   - `reading_time = max(1, math.ceil(word_count / 350))`（整数分钟）。
4. **上下篇与相关文章**：
   - 按发布时间降序列表 `posts` 计算相邻文章：索引 `i - 1`（更新一篇）与 `i + 1`（较早一篇），在模板中使用 `nav_post_card.html` 清晰标示方向，首尾篇缺失的一侧渲染为空字符串（绝不能出现未替换的 `{{...}}`）。
   - 相关文章：排除自身后，依据 `(共享 tags 数 * 3 + 同 category * 2)` 降序，其次按发布时间降序，取前 2–3 篇。

---

## 5. Markdown 渲染与核心 DOM 契约

### 5.1 Markdown 语法支持范围（`backend/markdown_engine.py`）
1. **ATX 标题（`#` 到 `####`）**：
   - `h2` 与 `h3` 必须生成全篇唯一且确定性的 `id` 锚点（保留中英文字符与数字，小写化并转连字符；同文本重复标题追加 `-2`、`-3` 后缀）。
   - 提取结构化 TOC 列表：`[{"level": 2, "id": "...", "text": "..."}]`（转义后安全文本）。
2. **围栏代码块（```` ```lang ````）**：
   - 先行抽取避免内部被二次 Markdown/HTML 解析。
   - 调用 `Pygments`：`get_lexer_by_name(lang)`，未知语言降级 `TextLexer()`，并使用 `HtmlFormatter(cssclass="highlight")` 输出。
   - **代码块 DOM 契约**：
     ```html
     <div class="code-block-wrapper">
       <div class="code-block-header">
         <span class="code-lang">python</span>
         <button type="button" class="code-copy-btn" aria-label="复制代码">复制</button>
       </div>
       <div class="highlight"><pre>...</pre></div>
     </div>
     ```
3. **标准 Markdown 表格**：
   - 识别表头行、分隔行（支持左/中/右对齐）与数据行。
   - **表格 DOM 契约**：必须包裹在 `<div class="table-wrap"><table>...</table></div>` 中以防止窄屏横向溢出。
4. **引用块 `>`**：支持连续多行 `>` 合并渲染为同一 `<blockquote>`。
5. **列表与分隔线**：支持 `- ` / `* ` 无序列表、`1. ` 有序列表及独立行 `---` / `***` 分隔线 `<hr>`。
6. **行内语法与 XSS 防护**：
   - 先保护行内代码 `` `...` `` 并对其进行 `html.escape`。
   - 转义危险原始 HTML 标签（禁止 `<script>` 等 XSS 载荷原样穿透），过滤 `javascript:` 危险协议，再解析图片、链接、加粗、斜体，最后还原行内代码 `<code>...</code>`。
   - 确保最终 HTML 输出不含未替换模板键模式（`{{[a-zA-Z0-9_]+}}`）。

### 5.2 文章目录（TOC）DOM 契约
`{{post_toc_html}}` 由后端根据 `toc` 列表渲染为：
```html
<nav class="toc-nav" aria-label="文章目录">
  <ul class="toc-list">
    <li class="toc-item toc-level-2" data-level="2"><a class="toc-link" href="#heading-id">标题文本</a></li>
    <li class="toc-item toc-level-3" data-level="3"><a class="toc-link" href="#sub-id">子标题文本</a></li>
  </ul>
</nav>
```
当文章不包含 `h2`/`h3` 时，输出带 `.toc-empty` 的温和空状态提示。

---

## 6. HTML 模板占位符与前端交互契约

### 6.1 模板渲染规则（`backend/renderer.py`）
- 模板引擎**严格仅使用双花括号 `{{key}}` 纯字符串键替换**，模板文件中**禁止出现任何 Jinja2 `{% ... %}` 或表达式语法**。
- 单遍正则替换 `re.sub(r"\{\{([a-zA-Z0-9_]+)\}\}", resolver, template_text)`：
  - 若 `key` 未在上下文提供，立即抛出 `KeyError`。
  - 所有纯文本插槽必须经过 `html.escape(value, quote=True)` 转义；`*_html` 富片段插槽直接注入已安全组装的 HTML。

### 6.2 各模板占位符完整清单

#### `templates/base.html`
- `{{base_path}}`, `{{page_title}}`, `{{page_description}}`, `{{canonical_url}}`, `{{site_title}}`, `{{site_tagline}}`, `{{author_name}}`, `{{icp_html}}`, `{{nav_home_active}}`, `{{nav_articles_active}}`, `{{nav_projects_active}}`, `{{nav_gallery_active}}`, `{{nav_about_active}}`, `{{extra_head}}`, `{{page_content}}`, `{{extra_scripts}}`, `{{current_year}}`
- 顶部主导航（`.site-nav`）、移动端抽屉导航（`.mobile-nav-list`）与页脚导航（`.footer-links`）同步纳入 `<a href="/gallery/">图像</a>`。
- `<head>` 内必须包含 `<meta name="site-base-path" content="{{base_path}}">`（由后端 `_wrap_base()` 注入规范化后的 `base_path`，根挂载时为空字符串 `""`，子路径挂载时为 `"/<repo>"`），供 `static/js/search.js` 动态拼装索引请求地址。
- `<head>` 内联防闪烁主题脚本在无 `localStorage('blog-theme')` 保存值时默认设置 `document.documentElement.dataset.theme = 'dark'`；全局脚本引入 `/static/js/main.js`（带版本参数）。

#### `templates/home.html`
- `.home-cover-artwork` 展示 `/static/images/starloop-cover.jpg`。
- `.home-entries` 升级为 4 列琴键错落入口（`文章` `/articles/`、`项目` `/projects/`、`图像` `/gallery/`、`关于` `/about/`），其中 `.home-entry--gallery` 配备 `48×48` 抽象棱镜星环 SVG（`viewBox="0 0 48 48"`），确保在 `1440×900`、`390×844`、`320×568`、`568×280` 视口下全数严密落于单屏内且零横向溢出。

#### `templates/articles.html`
- `{{category_tabs_html}}`：置于 `.page-body` 顶部，始终渲染 `.category-bar[data-category-bar] > .category-tabs[data-category-tabs][role="tablist"]`（内含 `.category-indicator[data-category-indicator]`、`全部` Tab 及 `categories.json` 与 Frontmatter 合并后的全部大类 Tab，携带 `data-filter-category` 与抽象 SVG 图标）。
- `{{archive_html}}`：当有文章时渲染 `partials/articles_list.html`；当站内 0 篇文章时渲染 `.empty-stage`（内含星环 SVG 与 `<p class="search-empty" data-articles-empty>暂无已发布文章。</p>`，确保空归档 `[data-filter-tag]` 数为 0 且切换分类仍有反馈）。

#### `templates/post.html`
- `{{post_title}}`, `{{post_subtitle}}`, `{{post_date}}`, `{{post_reading_time}}`, `{{post_word_count}}`, `{{post_category}}`, `{{post_category_url}}`（URL 编码后的分类名，用于 `<a class="post-meta-category" href="/articles/?category={{post_category_url}}">{{post_category}}</a>`）, `{{post_tags_html}}`, `{{post_cover_html}}`, `{{post_body_html}}`, `{{post_toc_html}}`, `{{prev_post_html}}`, `{{next_post_html}}`, `{{related_posts_html}}`
- 元信息时长保持极简，直接展示 `{{post_reading_time}} 分钟`（去掉 `"预计"` 等冗余词）。

#### `templates/projects.html`、`templates/gallery.html`、`templates/about.html`、`templates/404.html`
- `templates/projects.html`：`{{category_tabs_html}}`（项目大分类轨道，始终显示）、`{{projects_list_html}}`（有项目时渲染 `partials/projects_list.html`，0 项目时渲染 `.empty-stage` 含 `<p class="search-empty" data-projects-empty>暂无已发布项目。</p>`）。
- `templates/gallery.html`：`{{category_tabs_html}}`（图像大分类轨道，始终显示）、`{{gallery_html}}`（有图像时渲染 `partials/gallery_list.html`，0 图像时渲染 `.empty-stage` 含 `<p class="search-empty" data-gallery-empty>暂无已发布图像。</p>`），并内含居中原生 `<dialog class="gallery-lightbox" data-gallery-lightbox>` 弹窗骨架（左图舞台 `.gallery-lightbox-stage` + 右侧 `.gallery-lightbox-panel` 含关闭按钮、元信息、正/负向提示词 `<pre class="gallery-prompt-full">`、一键复制按钮 `.prompt-copy-btn` 与标签）。
- `templates/about.html`: `{{author_name}}`, `{{author_role}}`, `{{author_location}}`, `{{author_bio}}`, `{{about_body_html}}`, `{{social_links_html}}`（左侧肖像框展示 `/static/images/astra-portrait.jpg`）
- `templates/404.html`: 静态片段嵌入 `base.html` 的 `{{page_content}}`（不含未替换占位符）

#### `templates/partials/*.html`
- `articles_list.html`: `{{total_posts}}`, `{{tag_filters_html}}`, `{{articles_list_html}}`（含筛选空态 `.empty-stage.is-hidden[data-articles-empty]`）
- `post_row.html`: `{{url}}`, `{{date}}`, `{{date_short}}`, `{{year}}`, `{{category}}`, `{{tags_csv}}`, `{{title}}`, `{{summary}}`, `{{reading_time}}`, `{{tags_html}}`（根元素 `article.post-row` 同时携带 `data-category="{{category}}"` 与 `data-tags="{{tags_csv}}"`；分类按钮为 `<button type="button" class="post-row-category" data-filter-category="{{category}}">{{category}}</button>`）
- `projects_list.html`: `{{total_projects}}`, `{{tag_filters_html}}`, `{{projects_cards_html}}`（含 `.projects-toolbar`、`.projects-count[data-projects-count]`、`.projects-grid.projects-grid--catalog[data-projects-list]` 及筛选空态 `.empty-stage.is-hidden[data-projects-empty]`）
- `project_card.html`: `{{category}}`, `{{tags_csv}}`, `{{category_badge_html}}`（可点击 `<button type="button" class="project-category-badge" data-filter-category="...">`）, `{{name_html}}`, `{{status}}`, `{{year}}`, `{{summary}}`, `{{tags_html}}`（可点击 `.tag-pill[data-filter-tag]`）, `{{link_html}}`（根元素 `article.project-card` 携带 `data-category="{{category}}"` 与 `data-tags="{{tags_csv}}"`）
- `gallery_list.html`: `{{total_gallery}}`, `{{tag_filters_html}}`, `{{gallery_cards_html}}`（含 `.gallery-toolbar`、`.gallery-count[data-gallery-count]`、`.gallery-grid[data-gallery-list]` 及筛选空态 `.empty-stage.is-hidden[data-gallery-empty]`）
- `gallery_card.html`: `{{id}}`, `{{title}}`, `{{image}}`, `{{prompt}}`, `{{negative_prompt}}`, `{{model}}`, `{{params}}`, `{{category}}`, `{{tags_csv}}`, `{{category_badge_html}}`, `{{model_chip_html}}`, `{{tags_html}}`（根元素 `article.gallery-card` 携带 `data-gallery-id`、`data-category`、`data-tags`；内含 `.gallery-media-btn` 触发 Lightbox、`.gallery-prompt-preview`、`.prompt-copy-btn` 一键复制按钮与可点击 `.tag-pill[data-filter-tag]`）
- `nav_post_card.html`: `{{direction_label}}`, `{{direction_class}}`, `{{url}}`, `{{title}}`, `{{date}}`

### 6.3 前端交互属性契约（Hooks）
- **主题**：`[data-theme-toggle]`、`document.documentElement.dataset.theme` (`"dark"` 默认 | `"light"`)、`localStorage['blog-theme']`
- **首页滚动**：`[data-home-opening]`、`#home-intro` 与 `--cover-progress`，由 `static/js/home-cover.js` 随原生滚动更新。
- **搜索弹窗**：`[data-search-open]`、`[data-search-modal]`、`[data-search-input]`、`[data-search-results]`、`[data-search-close]`、选中态 `.search-result-item.is-selected`；`static/js/search.js` 读取 `meta[name="site-base-path"]` 构造 `INDEX_URL = basePath + '/api/search-index.json'`，并为结果条目的跳转 `href` 保证正确子路径前缀兜底。
- **通用双层分类 × 标签筛选与动效（`static/js/main.js` 统一服务 `/articles/`、`/projects/`、`/gallery/`）**：
  - 大分类：`[data-category-bar]`、`[data-category-tabs]`、`[data-category-indicator]`（`.category-indicator` 基于 `offsetLeft`/`offsetWidth` + `ResizeObserver` 丝滑定位）、`[data-filter-category]`（`role="tab"`、`aria-selected`、`.is-active`）及卡片行内分类触发器（`.post-row-category` / `.project-category-badge` / `.gallery-category-badge`）。
  - 细标签：`[data-filter-tag]`（含 `"all"`）、`.filter-pill-count`、不可用状态 `.is-hidden`（切换分类若导致当前 Tag 无条目则自动回退 `tag = 'all'`）。
  - 列表与空态：条目元素（`.post-row` / `.project-card` / `.gallery-card`，均带 `data-category` 与 `data-tags`）命中时错峰附加 `.is-entering` 与 `--stagger-index`；计数提示（`[data-articles-count]` / `[data-projects-count]` / `[data-gallery-count]`）；空态容器（`[data-articles-empty]` / `[data-projects-empty]` / `[data-gallery-empty]`，空态切换分类触发 `.empty-stage.is-transitioning`），并双向同步 URL `?category=...` / `?tag=...` / `?category=...&tag=...`。
- **图像提示词复制与 Lightbox（`static/js/gallery.js` / `main.js`）**：
  - `.prompt-copy-btn`：一键复制对应 `prompt` / `negative_prompt`（`navigator.clipboard.writeText` + 降级 `execCommand`），成功切换 `.is-copied` 并临时展示 `"已复制"`，失败标记 `.is-copy-error`；同时阻止点击冒泡以免误触发外层弹窗。
  - `.gallery-media-btn`：从当前 `.gallery-card` 提取完整原图、标题、模型、参数、正/负向提示词与标签填充至 `<dialog class="gallery-lightbox">` 并调用 `showModal()`；支持 `.gallery-lightbox-close`、点击遮罩外部与 `Escape` 键安全关闭，并恢复触发按钮焦点。
- **文章阅读**：`[data-reading-progress]`、`.toc-link.is-active`、`.code-copy-btn`、`.post-meta-category`（跳回 `/articles/?category=...`）

---

## 7. API、订阅源与静态构建流水线契约

### 7.1 `dist/api/search-index.json`
顶层为 JSON 数组，按文章发布日期倒序排列，每项包含：
`title`, `slug`, `url`, `date`, `category`, `tags`, `summary`, `excerpt`, `reading_time`。
当传入非空 `base_path`（如 `"/astrayao-blog"`）时，`feeds.py` 自动为每条记录的 `url` 加上 `base_path` 前缀（如 `"/astrayao-blog/articles/<slug>/"`）。

### 7.2 `dist/api/posts.json`、`dist/api/projects.json` 与 `dist/api/gallery.json`
- **`dist/api/posts.json`**：顶层为 JSON 对象，包含 `generated_at`, `total`, `posts`, `tags`, `categories`；受 `base_path` 参数影响，确保子路径部署时 `posts[].url` 与 `posts[].cover` 带统一前缀。
- **`dist/api/projects.json`**：顶层为 JSON 对象，包含 `generated_at`, `total`, `projects`（每项含 `name`, `status`, `year`, `summary`, `stack`, `category`, `tags`, `url`，站内根相对 `url` 自动加 `base_path` 前缀）, `tags`, `categories`。
- **`dist/api/gallery.json`**：顶层为 JSON 对象，包含 `generated_at`, `total`, `items`（每项含 `id`, `title`, `image`, `prompt`, `negative_prompt`, `model`, `params`, `category`, `tags`, `date`，站内根相对 `image` 自动加 `base_path` 前缀）, `tags`, `categories`。

### 7.3 `dist/rss.xml`、`dist/sitemap.xml` 与 `dist/robots.txt`
- `rss.xml`：标准 RSS 2.0 XML（使用覆写后的 `site_url` 与 `site_title`）。若 `site_url` 已含子路径（如 `https://example.github.io/astrayao-blog`），文章绝对链接按 `site_url` 根路径与文章原始相对路径 `/articles/<slug>/` 正确拼接，绝不出现 `/astrayao-blog/astrayao-blog/` 重复路径。
- `sitemap.xml`：符合 `http://www.sitemaps.org/schemas/sitemap/0.9` 命名空间，包含 `/`, `/articles/`, `/projects/`, `/gallery/`, `/about/` 及全部 `/articles/<slug>/` 的规范绝对 URL。
- `robots.txt`：声明 `User-agent: *`、`Allow: /` 及 `Sitemap: <site_url>/sitemap.xml`。

### 7.4 GitHub Pages 与通用构建开关（`renderer.py` / `build.py` / `check.py`）
1. **`render_site(project_root, dist_dir=None, clean=True, base_path="", site_url=None, cname="")`**：
   - `base_path` 经 `normalize_base_path` 规范化后注入 `{{base_path}}`，并在写出每份 HTML（含 `/gallery/index.html`）前执行 `apply_base_path_to_html` 重写根相对属性（跳过 `<pre>`/`<code>` 内部文本）。
   - `site_url` 非空时覆盖 `site["site_url"]`，用于 `canonical`、`rss.xml`、`sitemap.xml` 与 `robots.txt`。
   - **强制生成 `dist/.nojekyll`**（0 字节空文件），禁用 GitHub Pages 默认 Jekyll 过滤。
   - **可选生成 `dist/CNAME`**：优先取显式 `cname` 参数，其次读取 `site.json` 的 `custom_domain`；清理协议头与尾部路径后若非空则写入 `dist/CNAME`（`f"{domain}\n"`），为空时不生成该文件。
   - 返回的 `stats` 字典额外包含 `"base_path"`、`"has_cname"` 及项目/图像计数统计。
2. **命令行与环境变量接口**：
   - `scripts/build.py` 支持 `--base-path`（默认读取 `SITE_BASE_PATH`）、`--site-url`（默认读取 `SITE_URL`）、`--cname`（默认读取 `SITE_CNAME`）。
   - `scripts/check.py` 支持透传 `--base-path`、`--site-url`、`--cname` 至 `build.py`：必检清单纳入 `gallery/index.html`、`api/projects.json`、`api/gallery.json` 及 `.nojekyll`（允许 0 字节），校验 `categories.json` / `project_categories.json` / `gallery_categories.json` 预设分类已渲染至对应页面，并在 `base_path` 非空时校验 HTML 中的站内 `href`/`src` 均带 `base_path` 前缀且剥离前缀后真实存在于 `dist/`。
3. **GitHub Actions 自动发布流水线（`.github/workflows/deploy-pages.yml`）**：
   - 依赖声明于根目录 `requirements.txt`（`Pygments>=2.18.0`）。
   - `push` 到 `main` 或手动 `workflow_dispatch` 触发；`build` 作业执行 `actions/configure-pages@v5`、`python scripts/check.py --base-path "${{ steps.pages.outputs.base_path }}" --site-url "${{ steps.pages.outputs.origin }}${{ steps.pages.outputs.base_path }}"`（可选传入 `vars.PAGES_CNAME`）并上传 `dist/` 为 Pages artifact，`deploy` 作业通过 `actions/deploy-pages@v4` 发布。
4. **本地预览服务**：
   - `python scripts/serve.py --host 127.0.0.1 --port 8080`：本地静态服务，正确返回 `.html`/`.css`/`.js`/`.svg`/`.jpg`/`.json`/`.xml` MIME type，未知路径回退展示 `dist/404.html` 并返回 HTTP `404` 状态码。
