# ASTRA YAO · 星环手记（astrayao）— 零重型依赖个人静态博客

基于 **Python 3.13 标准库 + Pygments** 构建的独立唱片期刊风格个人技术博客系统。设计灵感源自《绝区零》天琴座歌姬耀嘉音（Astra Yao）的复古红黑金与星环大厦舞台美学——无需 Node.js、npm、Webpack 或任何前端重型构建工具，将纯文本 Markdown 与 JSON 内容编译为自包含的静态站点 `dist/`。**首发推荐通过 GitHub Actions 自动托管至 GitHub Pages**（零服务器成本、免 ICP 备案即可直接上线，支持子路径与自定义域名）；亦配套完整阿里云 ECS 迁移部署套件。

---

## 核心特性

- **Starloop Velvet & Vinyl 视觉系统**：默认呈现深邃温暖的 Starloop Night 暗色主视觉（黑曜石底、炽红点缀、香槟金边框），并支持一键切换 Ivory Collector's Edition 日间模式与防闪烁预加载。
- **典藏黑胶唱片舞台交互**：首页内置黑胶唱片展台（`astra-hero.jpg` + 匀速旋转唱片 + 四柱律动 EQ 与 `[data-vinyl-toggle]` 启停控制），关于页展示天琴座星环徽章（`astra-portrait.jpg`）。
- **零重型外部构建依赖**：手写 YAML Frontmatter 解析器、Markdown 渲染引擎（标题锚点 & 目录 TOC、表格、引用、列表、Pygments 语法高亮与一键复制）及轻量模板引擎。
- **全功能静态交互**：`Ctrl+K` / `Cmd+K` 站内实时搜索（基于 `/api/search-index.json`）、文章归档页多标签筛选、文章页顶部红金阅读进度条与右侧粘性目录滚动高亮。
- **完整站点产物**：自动输出首页、文章归档、文章详情、项目页、关于页、自定义 `404.html`、`/api/posts.json`、`/api/search-index.json`、`/rss.xml`、`/sitemap.xml`、`/robots.txt`、`dist/.nojekyll` 与可选 `dist/CNAME`。
- **质量门禁与双路径自动部署**：内置 `scripts/check.py` 支持根路径与子路径（`--base-path`）构建校验；提供 `.github/workflows/deploy-pages.yml` 一键托管至 GitHub Pages，以及阿里云上海 ECS `Caddyfile` / `nginx.conf` / `deploy.sh` 迁移套件。

---

## 运行环境要求

- **Python**: `3.13+`
- **Python 依赖**:
  - `Pygments`（代码块语法高亮）
  - `pytest`（单元测试与浏览器端到端测试）
  - `playwright`（可选，仅运行浏览器端到端测试 `tests/test_e2e_browser.py` 时需要）

---

## 项目目录结构

```text
.
├── .github/workflows/
│   └── deploy-pages.yml      # GitHub Pages 自动构建、门禁校验与发布流水线
├── backend/                  # 纯 Python 静态构建引擎
│   ├── __init__.py
│   ├── content_loader.py     # 加载站点配置、项目数据与 Markdown 文章（含 Frontmatter 与阅读时间估算）
│   ├── markdown_engine.py    # Markdown -> HTML 渲染器、TOC 提取与 Pygments 代码高亮
│   ├── renderer.py           # {{key}} 模板渲染器、子路径重写、.nojekyll/CNAME 与页面生成
│   └── feeds.py              # 生成 posts.json、search-index.json、rss.xml、sitemap.xml、robots.txt
├── content/                  # 所有站点文本与配置数据源
│   ├── site.json             # 站点标题、作者信息、Hero 文案、自定义域名、可选备案号与社交链接
│   ├── projects.json         # 项目作品集列表
│   ├── about.md              # 关于页面正文
│   └── posts/                # Markdown 博客文章（如 01-editorial-web-aesthetics.md）
├── templates/                # HTML5 页面模板与局部组件片段
│   ├── base.html             # 全站骨架（site-base-path 元标签、防闪烁脚本、搜索弹窗、页脚）
│   ├── home.html / articles.html / post.html / projects.html / about.html / 404.html
│   └── partials/             # featured_card.html / post_row.html / project_card.html 等
├── static/                   # 静态资源（构建时原样复制至 dist/static/）
│   ├── css/                  # tokens.css / base.css / components.css / prose.css
│   ├── js/                   # theme.js / search.js / post.js / main.js
│   └── images/               # astra-hero.jpg、astra-portrait.jpg 及自包含原创 SVG 封面与图标
├── scripts/                  # 构建、预览与质量检查脚本
│   ├── build.py              # 清理并重新构建 dist/（支持 --base-path / --site-url / --cname）
│   ├── serve.py              # 本地静态预览服务器（支持自定义 404.html 与 404 状态码）
│   └── check.py              # 全链路构建与质量门禁（产物、.nojekyll、.jpg/.svg、JSON/XML、零死链）
├── deploy/                   # 上云托管与服务器部署指南与配置
│   ├── GITHUB_PAGES_GUIDE.md # GitHub Pages 自动托管 + 阿里云域名 DNS 绑定保姆级指南（当前首选）
│   ├── Caddyfile             # Caddy 2 自动 HTTPS 配置（ECS 迁移备选）
│   ├── nginx.conf            # 生产级 Nginx 静态站点配置（ECS 迁移备选）
│   ├── deploy.sh             # 一键构建校验并原子部署至 ECS 的脚本（tar/scp 或 rsync）
│   └── DEPLOY_GUIDE.md       # 阿里云上海 ECS + ICP 备案完整运维文档（后续迁移用）
├── docs/                     # 产品、架构、设计规范与测试验收文档
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DESIGN_SYSTEM.md
│   └── QA_REPORT.md
├── tests/                    # 自动化测试
│   ├── test_backend.py       # 后端解析、子路径前缀、构建输出与 Feeds 单元测试
│   └── test_e2e_browser.py   # Playwright 端到端功能、子路径与响应式布局验收测试
├── requirements.txt          # 生产构建依赖声明（Pygments>=2.18.0）
├── .gitignore
└── README.md
```

---

## 如何新增文章与更新内容

### 1. 新增博客文章
在 `content/posts/` 目录下新建 `.md` 文件（建议按序号或日期命名，例如 `06-my-new-article.md`），文件顶部必须包含标准 Frontmatter：

```markdown
---
title: 文章标题
slug: my-new-article
date: 2026-11-21
category: 工程实践
tags: [Python, 架构设计, 独立博客]
summary: 一两句精炼的导语摘要，将展示在文章列表、卡片与站内搜索结果中。
cover: /static/images/cover-01.svg
featured: false
draft: false
---

## 第一节标题

正文支持标准 Markdown 语法：

- 列表、`> 引用块`、表格
- 带语言标识的代码块（如 ```python、```css、```nginx、```bash）
- 站内链接请使用根相对路径，例如 `[关于我](/about/)`
```

**Frontmatter 字段说明**：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `title` | 是 | 文章标题 |
| `slug` | 是 | URL 路径标识，最终生成 `/articles/<slug>/` |
| `date` | 是 | 发布日期（`YYYY-MM-DD`），文章列表按此字段倒序排列 |
| `category` | 是 | 文章分类 |
| `tags` | 是 | 标签列表，支持行内列表 `[标签1, 标签2]` 或 YAML 多行 `- 标签1` |
| `summary` | 是 | 文章摘要，用于首页卡片、文章列表与 SEO 描述 |
| `cover` | 否 | 封面图片根相对路径（如 `/static/images/cover-01.svg`） |
| `featured` | 否 | `true` 表示置顶推荐到首页 Spotlight 区域 |
| `draft` | 否 | `true` 表示草稿，构建时不会发布到 `dist/` 与订阅源中 |

### 2. 修改站点信息、项目与关于页
- **站点、域名与托管信息**：编辑 `content/site.json`：
  - `site_url`：当前默认为 `https://astrayao.com`（若部署在 GitHub Pages 子路径，CI 会自动按页面地址覆盖；绑定自定义域名时请按实际后缀替换）。
  - `custom_domain`：可选自定义域名（如 `"astrayao.com"`），设置后自动生成 `dist/CNAME`。
  - `icp_number`：GitHub Pages 托管期间保留为 `""` 不展示占位备案号；若迁回国内服务器，再填入真实备案号。
- **项目展示**：编辑 `content/projects.json`。
- **关于页面**：编辑 `content/about.md`。

---

## 本地构建、预览、校验与测试

```bash
# 1. 构建静态站点到 dist/（默认根路径 '/'）
python scripts/build.py

#    如需在本地模拟 GitHub Pages 项目子路径构建：
python scripts/build.py --base-path /astrayao-blog --site-url https://example.github.io/astrayao-blog

# 2. 运行全链路构建与质量门禁（推荐每次发布或改稿后执行）
#    自动重新构建 dist/，校验关键产物、.nojekyll、.jpg/.svg 静态资源、JSON/XML 合法性、零未替换模板变量、零死链
python scripts/check.py

#    同时支持子路径门禁校验（校验完成后建议再跑一次 `python scripts/check.py` 恢复根路径 dist/）：
python scripts/check.py --base-path /astrayao-blog --site-url https://example.github.io/astrayao-blog

# 3. 启动本地预览服务器（默认 http://127.0.0.1:8000/）
python scripts/serve.py
python scripts/serve.py --host 127.0.0.1 --port 8080

# 4. 运行后端单元测试
pytest tests/test_backend.py

# 5. 运行浏览器端到端验收测试（需本机 Chrome 与 playwright）
pytest tests/test_e2e_browser.py
```

---

## 部署上线

### 方案一：GitHub Pages 自动托管（当前推荐首发方案）
零服务器费用、无需 ICP 备案即可直接上线，推送到 `main` 分支后由 `.github/workflows/deploy-pages.yml` 自动完成构建、校验与发布：
- **完整图文与命令行保姆级教程**：请阅读 [GitHub Pages 部署与阿里云域名绑定指南](deploy/GITHUB_PAGES_GUIDE.md)
- **核心流程**：
  1. 推送代码到 GitHub 仓库 `main` 分支（含 `.github/workflows/deploy-pages.yml` 与 `requirements.txt`）。
  2. 在 GitHub 仓库 **Settings -> Pages -> Source** 选择 **GitHub Actions**。
  3. 如需绑定在阿里云购买的 `astrayao` 域名，在云解析 DNS 添加 GitHub Pages 官方 `A` 记录（`185.199.108.153`~`185.199.111.153`）与 `www` `CNAME` 后，在 Pages 设置页填写 Custom domain 并开启 Enforce HTTPS。

### 方案二：迁移至阿里云华东 2（上海）ECS（后续按需切换）
若未来完成域名 ICP 备案并希望获得中国大陆服务器独立托管与极速访问，可无缝切换至阿里云 ECS 方案：
- **完整部署与备案运维指南**：请阅读 [阿里云上海 ECS 部署运维指南](deploy/DEPLOY_GUIDE.md)
- **Web 服务器配置二选一**：
  - [deploy/Caddyfile](deploy/Caddyfile)：Caddy 2 自动申请与续期 Let's Encrypt HTTPS 证书，个人博客首选。
  - [deploy/nginx.conf](deploy/nginx.conf)：Nginx 静态站生产配置（Gzip、`/static/` 长期缓存、HTML 协商缓存、安全响应头、404 页面映射与 HTTPS 示例）。
- **一键发布脚本**：
  ```bash
  # 先在本地执行演练（校验 + 不上传）
  bash deploy/deploy.sh --dry-run

  # 配置 ECS_HOST 后一键构建校验、打包上传并原子切换线上目录
  ECS_HOST="47.100.xx.xx" bash deploy/deploy.sh
  ```
