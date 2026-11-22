# 质量保证与视觉验收报告（QA Report）

> **项目名称**：ASTRA YAO · 星环手记（`astrayao`）— Starloop Velvet & Vinyl / Starloop Frequency 独立技术出版物静态站（GitHub Pages 首发托管）  
> **验收角色**：`qa-verifier`（联合 `ui-designer`、`fe-engineer` 复核签字）  
> **最终结论**：**PASS（全量测试 42/42 通过，根路径与 GitHub Pages 子路径质量门禁全绿，多轮视觉审美复核签字通过）**

---

## 1. 测试环境与运行约束

- **操作系统与运行环境**：Windows + Python `3.13.15` + `pytest 9.1.1` + `Pygments 2.21.0` + `playwright`
- **浏览器引擎**：本机 Google Chrome（`C:\Program Files\Google\Chrome\Application\chrome.exe`，`headless=True`）
- **静态服务模式**：在 [tests/test_e2e_browser.py](file:///d:/网页运营/tests/test_e2e_browser.py) 进程内通过标准库 `http.server.ThreadingHTTPServer(("127.0.0.1", 0), DistStaticHandler)` 提供静态目录服务，显式配置 `.html` / `.css` / `.js` / `.json` / `.svg` / `.xml` / `.txt` / `.jpg` / `.png` MIME 类型，并将未知路径精确回退为 `404.html`（HTTP `404` 状态码）。
- **测试站点夹具（[tests/conftest.py](file:///d:/网页运营/tests/conftest.py)）**：
  - `empty_site_root`：0 篇文章、0 个项目，包含 `content/categories.json` 默认三大分类（`代码`、`图像生成`、`工程`）。
  - `populated_site_root`：2 篇测试文章（`build-fixture` 归属 `代码`、`deployment-fixture` 归属 `工程`）与 1 个测试项目。
  - `categorized_site_root`：4 篇测试文章，完整覆盖 `代码`（2 篇）、`图像生成`（1 篇）、`工程`（1 篇）三大分类与多组交叉/专属 Tag（`Python`、`架构`、`设计`、`渲染`、`色彩`、`CSS`、`部署`、`Nginx`）。
- **截图输出目录策略**：`get_screenshot_dir()` 优先读取环境变量 `QA_SCREENSHOT_DIR`，其次通过 `_try_ensure_writable_dir()` 实测默认 brain 目录可写/可删权限，无权限时自动回退至 `tempfile.mkdtemp(prefix="qa-screenshots-")`。

---

## 2. 自动化校验与测试执行结果

最终代码、视觉样式与分类配置冻结后，按顺序复跑以下全部校验：

| 检查项目 | 执行命令 | 实测结果 | 覆盖范围 |
| --- | --- | --- | --- |
| 全站构建与质量门禁（根路径） | `python scripts/check.py` | **PASS**（Exit Code `0`，`base_path=/`、`cname=no`，构建耗时 `26.48 ms`） | `5` 个 HTML 页面、`5` 个 API/订阅文件、`20` 个静态文件（含 `10` 张 `.jpg`/`.svg` 图像资产）、`126` 条站内链接零死链、`0` 未替换 `{{...}}` 占位符、`content/categories.json` 与 `dist/api/posts.json` 分类校验通过、`.nojekyll` 存在且无 `CNAME`、JSON/XML 语法合法 |
| 全站构建与质量门禁（GitHub Pages 子路径） | `python scripts/check.py --base-path /astrayao-blog --site-url https://example.github.io/astrayao-blog` | **PASS**（`devops-sre` 实测，#45） | 全部站内 `href`/`src` 带 `/astrayao-blog` 前缀并映射回 `dist/`，分类 Tab 完整渲染，API URL 与 RSS/Sitemap 无重复路径拼接 |
| 后端与构建引擎单元测试 | `pytest tests/test_backend.py -v` | **18/18 PASSED** | Frontmatter 解析、字数与阅读时间估算、`categories.json` 加载与 Frontmatter 自定义新分类自动合并、空归档大分类 Tab 渲染、分类 × 子路径链接与 `api/posts.json` 分类统计、标题唯一锚点与 TOC、Pygments 高亮、表格/引用/列表、XSS 转义、RSS/Sitemap XML、`base_path` HTML 改写（保护 `<pre>`/`<code>`）、`.nojekyll`/`CNAME` 生成、预览服务器 200/404 |
| 浏览器端到端验收测试 | `pytest tests/test_e2e_browser.py -v` | **24/24 PASSED** | 首页封面随滚动渐隐与触控/滚轮/转屏/减动效、超窄屏导航抽屉与搜索框自适应、全路由 200/404、默认暗夜与象牙日间主题切换持久化、Ctrl+K 搜索、空归档 4 大分类 Tab 切换与指示条滑动、多分类 × Tag 二级联动筛选与 URL 还原、详情页分类跳转、阅读进度/TOC/移动端折叠目录/代码复制与降级、全套 12 张视觉截图采集、GitHub Pages 严格子路径挂载部署 |
| 合并全量测试 | `pytest tests/test_backend.py tests/test_e2e_browser.py -v` | **42/42 PASSED**（耗时 `59.32s`） | 端到端全链路回归验证 |

---

## 3. 浏览器端到端验收明细（`tests/test_e2e_browser.py`）

1. **首页星环封面揭幕与多端交互（`test_home_cover_*`）**
   - 覆盖 `1440×900`、`390×844`、`320×568`、`568×280` 视口下封面遮罩随滚动渐隐与三入口（`文章` / `项目` / `关于`）上浮、鼠标滚轮暂停位置保持、移动端触控半程停驻、`prefers-reduced-motion: reduce` 降级以及手机横竖屏旋转进度保持。
2. **超窄屏导航抽屉与搜索弹窗自适应（`test_compact_navigation_and_search_fit_viewport`）**
   - 在 `280×653`、`320×568`、`568×280`、`700×360` 视口下核验顶栏操作按钮尺寸（`>= 44×44`）、抽屉焦点锁定、搜索弹窗键盘上下选择与 `220px` 极矮视口无溢出。
3. **全路由状态、资源加载与响应式零溢出（`test_routes_zero_errors_and_responsive_viewports` & `test_custom_404_page_and_assets`）**
   - 在 Desktop (`1440×900`) 与 Mobile (`390×844`) 下遍历全部核心路由与文章详情页返回 `200`，未知路由返回真实 `404`；全程 `console.error == []`、`pageerror == []`、所有图片完整加载、零横向溢出。
4. **明暗双主题切换与持久化（`test_theme_toggle_and_persistence`）**
   - 验证默认 `"dark"` 主题（星环轨道 `.home-entry-orbits` 可见）切换至 `"light"` 后写入 `localStorage['blog-theme']`、刷新保持 `"light"`，再次点击恢复 `"dark"`。
5. **空归档常驻大分类轨道与搜索空态（`test_empty_archive_and_search`）**
   - 0 篇文章时 `/articles/` 仍完整展示 `全部`、`代码`、`图像生成`、`工程` 4 个大分类 Tab（计数均为 `0`），`[data-filter-tag]` 数量为 `0`，并展示 `暂无已发布文章。`。
   - 点击 `代码` Tab 后，`aria-selected` 更新为 `"true"`、`.category-indicator` `translate3d(...)` 平滑位移、URL 同步为 `?category=代码`，再次切回 `全部` 后清除查询参数。
6. **多分类 × Tag 双层联动筛选与详情页分类跳转（`test_categorized_articles_dual_filtering_and_navigation`）**
   - **一级大分类过滤与 Tag 动态收敛**：在 `categorized_server`（4 篇文章）点击 `代码`（2 篇），列表收敛为 2 篇、计数提示更新为 `"代码 · 共 2 篇"`；仅属于 `工程` 的 `部署` 标签胶囊自动隐藏（`.is-hidden`），当前分类可用标签计数动态重算（`设计` 为 `2`、`架构` 为 `1`）。
   - **分类 × Tag 二级联动**：在 `代码` 分类下点击 `架构` 标签，列表收敛为 1 篇、计数提示为 `"代码 · 「架构」· 共 1 篇"`，URL 同步为 `?category=代码&tag=架构`。
   - **不可用 Tag 自动回退**：在选中 `Python` 标签时切换大分类至 `工程`（该分类下无 `Python` 文章），激活标签自动回退至 `all` 并展示 `工程` 分类下的 1 篇文章。
   - **行内分类按钮与行内标签点击**：点击文章行内的 `button.post-row-category[data-filter-category="图像生成"]` 与 `.tag-pill[data-filter-tag="设计"]` 均可就地触发对应分类或标签筛选。
   - **URL 参数直接还原与详情页分类跳转**：直接访问 `/articles/?category=代码&tag=CSS` 自动激活对应分类 Tab 与 Tag 胶囊并过滤出 1 篇文章；在文章详情页验证极简元信息（无 `"预计"` 冗余词）并点击 `a.post-meta-category`（`代码`）成功跳转到 `/articles/?category=%E4%BB%A3%E7%A0%81` 并自动激活 `代码` 分类。
   - **全视口零溢出**：在 `1440×900`、`390×844`、`320×568`、`280×653` 四个视口下遍历多分类归档页、文章详情页与空归档页，均满足 `scrollWidth <= clientWidth` 且零控制台/网络错误。
7. **长文阅读体验与移动端目录/剪贴板降级（`test_post_reading_experience` & `test_mobile_toc_and_clipboard_unavailable`）**
   - 验证桌面端 TOC 锚点联动、顶部阅读进度条 `[data-reading-progress]`、代码复制成功态（`.is-copied` / `"已复制"`），以及移动端 `<details data-post-toc>` 点击跳转自动收起和剪贴板不可用时的 `"复制失败"` 降级提示。
8. **GitHub Pages 项目子路径部署（`test_github_pages_subpath_deployment`）**
   - 使用 `SubpathDistHandler` 将 `base_path="/astrayao-blog"` 构建产物严格挂载于 `/astrayao-blog/`（不带前缀的 `/static/...` 与 `/api/...` 直连请求均返回 `404`），验证首页、搜索跳转 `/astrayao-blog/articles/...` 及关于页图像在子路径下零错误运行。

---

## 4. 视觉审阅闭环与截图清单

### 4.1 视觉优化与回归闭环

- **第一阶段（Paper & Ink 基础版）与第二阶段（Starloop Velvet & Vinyl 重构版）**：已完成表格代码防断词、搜索框原生蓝叉消除、暗色插画柔光以及移动端首行基线对齐优化。
- **第三阶段（Starloop Frequency 文章可扩展大分类 × Tag 双层筛选与动效）**：
  - 第一轮 5 张截图审阅后，`fe-engineer`（#47）确认前端结构与交互通过；`ui-designer`（#48）在 `static/css/components.css` 完成两项出版级精修：
    1. 将二级 Tag 激活胶囊（`.filter-pill.is-active`）由实心亮绯红调整为香槟金柔底描边（`var(--gold-soft)` + `var(--gold)` 细边），突出顶部一级大分类轨道的主视觉焦点。
    2. 收紧 `<= 640px` 移动端 `.category-tabs` / `.category-tab` 内边距与字号比例，使默认 4 个大分类（`全部`、`代码`、`图像生成`、`工程`）在 `390×844` 首屏完整同现，同时保留 `overflow-x: auto` 兼容 `320×568` / `280×653` 及后续扩展分类。
  - `qa-verifier` 重跑全部 42 项测试并刷新截图（#49），`ui-designer` 于 `#50` 正式签字通过。

### 4.2 最终视觉验收截图清单（保存于会话 brain 目录）

| 场景 | 主题与视口 | 截图文件绝对路径 |
| --- | --- | --- |
| 文章页（多分类轨道 + 二级 Tag 列表 · 暗夜） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-categories-dark.png` |
| 文章页（多分类轨道 + 二级 Tag 列表 · 象牙） | `light` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-categories-light.png` |
| 文章页（空归档常驻大分类栏 + 星环空态） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-empty-dark.png` |
| 移动端文章页（大分类轨道 + Tag 胶囊 + 列表） | `dark` · `390×844` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-mobile-dark.png` |
| 文章详情页（可点击分类徽章 + Tag 胶囊 + 封面） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\post-detail-tags.png` |
| 首页主视觉（星环封面） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-dark.png` |
| 首页展开三入口（象牙日间） | `light` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-light.png` |
| 文章页 + Cmd/Ctrl+K 搜索弹窗命中结果 | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-search.png` |
| 文章详情页（正文 + 代码块 + TOC） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\post-detail.png` |
| 精选项目目录页 | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\projects.png` |
| 关于页（含耀嘉音天琴座徽章框） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\about.png` |
| 移动端首页响应式视图 | `dark` · `390×844` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-mobile.png` |
