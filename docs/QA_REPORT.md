# 质量保证与视觉验收报告（QA Report）

> **项目名称**：ASTRA YAO · 星环手记（`astrayao`）— Starloop Velvet & Vinyl 独立技术出版物静态站（GitHub Pages 首发托管）  
> **验收角色**：`qa-verifier`（联合 `ui-designer`、`fe-engineer` 复核签字）  
> **最终结论**：**PASS（全量测试 24/24 通过，根路径与 GitHub Pages 子路径质量门禁全绿，视觉审美复核签字通过）**

---

## 1. 测试环境与运行约束

- **操作系统与运行环境**：Windows + Python `3.13.15` + `pytest 9.1.1` + `Pygments 2.21.0` + `playwright`
- **浏览器引擎**：本机 Google Chrome（`C:\Program Files\Google\Chrome\Application\chrome.exe`，`headless=True`）
- **静态服务模式**：在 [tests/test_e2e_browser.py](file:///d:/网页运营/tests/test_e2e_browser.py) 进程内通过标准库 `http.server.ThreadingHTTPServer(("127.0.0.1", 0), DistStaticHandler)` 提供 `dist/` 目录服务，显式配置 `.html` / `.css` / `.js` / `.json` / `.svg` / `.xml` / `.txt` / `.jpg` / `.png` MIME 类型，并将未知路径精确回退为 `dist/404.html`（HTTP `404` 状态码）。
- **截图输出目录策略**：`get_screenshot_dir()` 优先读取环境变量 `QA_SCREENSHOT_DIR`，其次通过 `_try_ensure_writable_dir()` 实测默认 brain 目录可写/可删权限，无权限时自动回退至 `tempfile.mkdtemp(prefix="qa-screenshots-")`，保证跨会话与 CI 环境可移植性。

---

## 2. 自动化校验与测试执行结果

最终代码、视觉样式与内容冻结后，按顺序复跑以下全部校验：

| 检查项目 | 执行命令 | 实测结果 | 覆盖范围 |
| --- | --- | --- | --- |
| 全站构建与质量门禁（根路径） | `python scripts/check.py` | **PASS**（Exit Code `0`，`base_path=/`、`cname=no`） | `10` 个 HTML 页面（`5` 篇文章、`5` 个项目、`20` 个标签）、`5` 个 API/订阅文件、`18` 个静态文件（含 `10` 张 `.jpg`/`.svg` 图像资产）、`424` 条站内链接零死链、`0` 未替换 `{{...}}` 占位符、`.nojekyll` 存在且无 `CNAME`、JSON/XML 语法合法 |
| 全站构建与质量门禁（GitHub Pages 子路径） | `python scripts/check.py --base-path /astrayao-blog --site-url https://example.github.io/astrayao-blog` | **PASS**（`devops-sre` 实测，#36） | 全部站内 `href`/`src` 带 `/astrayao-blog` 前缀并映射回 `dist/`，API URL 与 RSS/Sitemap 无重复路径拼接 |
| 后端与构建引擎单元测试 | `pytest tests/test_backend.py -v` | **15/15 PASSED** | Frontmatter 解析、字数与阅读时间估算、草稿过滤与上下篇、标题唯一锚点与 TOC、Pygments 高亮、表格/引用/列表、XSS 转义、RSS/Sitemap XML、`base_path` 规范化与 HTML 改写（保护 `<pre>`/`<code>`）、`.nojekyll`/`CNAME` 生成、预览服务器 200/404 与 `image/jpeg` MIME |
| 浏览器端到端验收测试 | `pytest tests/test_e2e_browser.py -v` | **9/9 PASSED** | 全路由 200/404、Console/Page/资源零错误、Desktop & Mobile 零横向溢出、默认暗夜主题与日间切换持久化、黑胶唱片展台暂停/恢复与定制图像加载、Ctrl+K 搜索、标签筛选、阅读进度/TOC/复制、视觉截图采集、GitHub Pages 严格子路径挂载部署 |
| 合并全量测试 | `pytest tests/test_backend.py tests/test_e2e_browser.py -v` | **24/24 PASSED**（耗时 `35.66s`） | 端到端全链路回归验证 |

---

## 3. 浏览器端到端验收明细（`tests/test_e2e_browser.py`）

1. **全路由状态、资源加载与响应式零溢出（`test_routes_zero_errors_and_responsive_viewports`）**
   - 在 **Desktop (`1440×900`)** 与 **Mobile (`390×844`)** 两个视口下依次访问 `/`, `/articles/`, `/projects/`, `/about/` 及 `dist/api/posts.json` 中的全部 5 篇 `/articles/<slug>/` 路由（每视口 9 个路由）。
   - 全部路由 HTTP 状态码为 `200`，无任何未替换 `{{...}}` 模板标记，所有 `<img>` 加载完整（`complete && naturalWidth > 0`），且均严格满足 `document.documentElement.scrollWidth <= document.documentElement.clientWidth`。
   - 移动端（`390×844`）验证汉堡菜单按钮 `[data-mobile-menu-toggle]` 可展开 `.mobile-drawer.is-open` 并通过 `Escape` 键正常收起。
   - 全程 `console.error == []`、`pageerror == []`、静态资源请求无 `>= 400` 或失败请求。
2. **自定义 404 页面验证（`test_custom_404_page_and_assets`）**
   - 在 Desktop 与 Mobile 下访问 `/non-existent-page-404/`，验证真实 HTTP 状态码 `404`、`.error-page` 正确展示 `404` 提示、零横向溢出、无 JS `pageerror`，且所有静态子资源正常加载（无 4xx/5xx）。
3. **Starloop 默认暗夜主题与 Ivory 日间切换持久化（`test_theme_toggle_and_persistence`）**
   - 在显式 `color_scheme="light"` 环境下首次访问 `/`，验证默认主题仍为 `"dark"`（Starloop Night）；点击 `[data-theme-toggle]` 切换至 `"light"`（Ivory Collector's Edition）并写入 `localStorage['blog-theme']`；执行 `page.reload()` 后仍保持 `"light"`；再次点击切回 `"dark"`。
4. **黑胶唱片展台交互与定制插画加载（`test_vinyl_stage_toggle_and_astra_assets`）**
   - 首页核验 `/static/images/astra-hero.jpg` 可见且完整加载（`complete && naturalWidth > 0`）。
   - 验证 `[data-vinyl-stage]` 默认处于旋转态（无 `.is-paused`，`[data-vinyl-toggle]` `aria-pressed="false"`、文案 `"旋转中"`）；点击后切换为 `.is-paused`、`aria-pressed="true"`、文案 `"已暂停"`；再次点击恢复旋转态。
   - 关于页核验 `.about-portrait-frame img[src="/static/images/astra-portrait.jpg"]` 可见且完整加载。
5. **Cmd/Ctrl+K 全局搜索弹窗（`test_search_modal_shortcut_and_results`）**
   - 按 `Control+k` 唤醒 `[data-search-modal]`，输入中文关键词 `"设计"` 与 `"服务器"` 均在 `[data-search-results]` 渲染匹配结果及 `<mark class="search-highlight">` 高亮片段；按 `Escape` 正常关闭弹窗。
6. **文章归档标签筛选（`test_articles_tag_filtering`）**
   - 在 `/articles/` 点击子集标签按钮 `.filter-pills [data-filter-tag]`，验证可见文章数精确收敛且 URL 同步写入 `?tag=...`；点击 `"all"` 恢复全部 5 篇文章；直接访问 `/articles/?tag=...` 时页面初始化自动完成对应标签筛选。
7. **文章长文阅读交互体验（`test_post_reading_experience`）**
   - 访问 `/articles/python-static-architecture/`，验证右侧 `.toc-nav .toc-list` 存在多个 `#` 锚点链接；点击 `.code-copy-btn` 后按钮附加 `.is-copied` 类并由 `"复制"` 切换为 `"已复制"`；向下滚动正文后，顶部阅读进度条 `[data-reading-progress]` 宽度大于 `0`，且 `.toc-link.is-active` 随滚动位置激活。
8. **GitHub Pages 项目子路径部署（`test_github_pages_subpath_deployment`）**
   - 调用 `render_site(PROJECT_ROOT, dist_dir=tmp_path / "dist", clean=True, base_path="/astrayao-blog", site_url="https://example.github.io/astrayao-blog")` 构建到临时目录，断言 `stats["base_path"] == "/astrayao-blog"`、`.nojekyll` 存在、未生成 `CNAME`。
   - 使用 `SubpathDistHandler` 将临时 `dist/` **严格**挂载于 `/astrayao-blog/`：未带前缀的 `/static/css/tokens.css` 与 `/api/search-index.json` 直连请求（绕过环境代理）均返回 `404`，模拟真实 GitHub Pages 项目站点。
   - Chrome 访问 `/astrayao-blog/` 返回 `200`，`<meta name="site-base-path">` 为 `/astrayao-blog`，`/astrayao-blog/static/images/astra-hero.jpg` 完整加载；`Ctrl+K` 搜索 `"设计"` 命中且结果 `href` 以 `/astrayao-blog/articles/` 开头，点击后成功跳转；`/astrayao-blog/about/` 中 `astra-portrait.jpg` 完整加载；全程 console/page/资源零错误。

---

## 4. 视觉审阅闭环与截图清单

### 4.1 视觉优化与回归闭环

- **第一阶段（Paper & Ink 基础版）闭环**：完成表格行内代码断词（`white-space: nowrap`）、搜索框原生蓝叉消除、暗色图像柔光过渡与 TOC 末行防孤行优化。
- **第二阶段（Astra Yao — Starloop Velvet & Vinyl 重构版）闭环**：
  - 第一轮全套 7 张视觉审阅后，`qa-verifier` 与 `fe-engineer` 在 `#26`/`#27` 指出移动端 `390×844` 下 `.hero-eyebrow` 换行时左侧 `✦` 居中对齐可更精致。
  - `ui-designer` 在 `#28` 更新 `static/css/components.css`，将 `.hero-eyebrow` 设为 `align-items: baseline` 并将 `.now-badge` / `.now-dot` 改为首行对齐，重跑 `python scripts/check.py` 通过。
  - `qa-verifier` 重跑全部 21 项测试并刷新截图，`ui-designer` 于 `#30` 正式签字通过。

### 4.2 最终视觉验收截图清单（保存于会话 brain 目录）

| 场景 | 主题与视口 | 截图文件绝对路径 |
| --- | --- | --- |
| 首页主视觉（黑胶唱片展台） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-dark.png` |
| 首页象牙典藏版 | `light` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-light.png` |
| 文章归档页 + 搜索弹窗命中结果 | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-search.png` |
| 文章详情页（正文 + 代码块 + TOC） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\post-detail.png` |
| 精选项目目录页 | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\projects.png` |
| 关于页（含耀嘉音天琴座徽章框） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\about.png` |
| 移动端首页响应式视图 | `dark` · `390×844` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-mobile.png` |
