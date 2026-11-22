# 质量保证与视觉验收报告（QA Report）

> **项目名称**：ASTRA YAO · 星环手记（`astrayao`）— Starloop Velvet & Vinyl / Starloop Frequency 独立技术出版物静态站（GitHub Pages 首发托管）  
> **验收角色**：`qa-verifier`（联合 `ui-designer`、`fe-engineer` 复核签字）  
> **最终结论**：**PASS（全量测试 47/47 通过，根路径与 GitHub Pages 子路径质量门禁全绿，多轮视觉审美复核签字通过）**

---

## 1. 测试环境与运行约束

- **操作系统与运行环境**：Windows + Python `3.13.15` + `pytest 9.1.1` + `Pygments 2.21.0` + `playwright`
- **浏览器引擎**：本机 Google Chrome（`C:\Program Files\Google\Chrome\Application\chrome.exe`，`headless=True`）
- **静态服务模式**：在 [tests/test_e2e_browser.py](file:///d:/网页运营/tests/test_e2e_browser.py) 进程内通过标准库 `http.server.ThreadingHTTPServer(("127.0.0.1", 0), DistStaticHandler)` 提供静态目录服务，显式配置 `.html` / `.css` / `.js` / `.json` / `.svg` / `.xml` / `.txt` / `.jpg` / `.png` MIME 类型，并将未知路径精确回退为 `404.html`（HTTP `404` 状态码）。
- **测试站点夹具（[tests/conftest.py](file:///d:/网页运营/tests/conftest.py)）**：
  - `empty_site_root`：0 篇文章、0 个项目、0 幅图像，完整包含 `content/categories.json`（`代码`/`图像生成`/`工程`）、`content/project_categories.json`（`应用`/`工具`/`视觉`）、`content/gallery_categories.json`（`角色`/`场景`/`视觉`）。
  - `populated_site_root`：2 篇测试文章（`build-fixture` 归属 `代码`、`deployment-fixture` 归属 `工程`）与 1 个测试项目（归属 `应用`）。
  - `categorized_site_root`：
    - 4 篇多分类文章（覆盖 `代码`、`图像生成`、`工程` 与多组交叉/专属 Tag）；
    - 4 个多分类项目（覆盖预设 `应用`、`工具`、`视觉` 及未注册新分类 `实验` 以验证自动发现，含显式 `tags` 与缺省回退 `stack`）；
    - 4 幅多分类图像作品（覆盖预设 `角色`、`场景`、`视觉` 及未注册新分类 `光影`，使用本地真实静态图 `/static/images/astra-portrait.jpg`、`/static/images/starloop-cover.jpg`、`/static/images/cover-01.svg`、`/static/images/cover-02.svg`，覆盖完整 `negative_prompt`/`model`/`params`/`date` 与无 `negative_prompt` 条件隐藏场景）。
- **截图输出目录策略**：`get_screenshot_dir()` 优先读取环境变量 `QA_SCREENSHOT_DIR`，其次通过 `_try_ensure_writable_dir()` 实测默认 brain 目录可写/可删权限，无权限时自动回退至 `tempfile.mkdtemp(prefix="qa-screenshots-")`。

---

## 2. 自动化校验与测试执行结果

最终代码、视觉样式与三大板块分类配置冻结后，按顺序复跑以下全部校验：

| 检查项目 | 执行命令 | 实测结果 | 覆盖范围 |
| --- | --- | --- | --- |
| 全站构建与质量门禁（根路径） | `python scripts/check.py` | **PASS**（Exit Code `0`，`base_path=/`、`cname=no`，构建耗时 `29.67 ms`） | `6` 个 HTML 页面（含 `/gallery/`）、`7` 个 API/订阅文件（含 `api/projects.json`、`api/gallery.json`）、`20` 个静态文件（含 `10` 张 `.jpg`/`.svg` 图像资产）、`168` 条站内链接（含 `data-image`）零死链、`0` 未替换 `{{...}}` 占位符、三大板块分类注册表与 API 校验通过、`.nojekyll` 存在且无 `CNAME`、JSON/XML 语法合法 |
| 全站构建与质量门禁（GitHub Pages 子路径） | `python scripts/check.py --base-path /astrayao-blog --site-url https://example.github.io/astrayao-blog` | **PASS**（`devops-sre` 实测，#58） | 全部站内 `href`/`src`/`data-image` 带 `/astrayao-blog` 前缀并映射回 `dist/`，三大板块分类 Tab 完整渲染，API URL 与 RSS/Sitemap 无重复路径拼接 |
| 后端与构建引擎单元测试 | `pytest tests/test_backend.py -v` | **21/21 PASSED** | Frontmatter 解析、字数与阅读时间估算、三大板块分类注册表加载/缺省回退与自定义新分类自动合并、`load_projects` tag/stack 回退、`load_gallery` 必填校验/排序/`params` 字典格式化、空归档大分类 Tab 渲染、标题唯一锚点与 TOC、Pygments 高亮、表格/引用/列表、XSS 转义、RSS/Sitemap XML、`base_path` HTML 改写（保护 `<pre>`/`<code>`）、`.nojekyll`/`CNAME` 生成、预览服务器 200/404 |
| 浏览器端到端验收测试 | `pytest tests/test_e2e_browser.py -v` | **26/26 PASSED** | 首页 4 入口（`文章`/`项目`/`图像`/`关于`）随滚动揭幕与多视口间距/底边边界、触控/滚轮/转屏/减动效、超窄屏导航抽屉与搜索框自适应、全路由（含 `/gallery/`）200/404、明暗主题切换持久化、Ctrl+K 搜索、空站三大板块常驻 4 大分类 Tab 切换与指示条滑动、`/articles/` + `/projects/` + `/gallery/` 双层分类 × Tag 联动筛选与 URL 还原、详情页分类跳转、`/gallery/` 一键复制提示词与降级、Lightbox `<dialog>` 全图/正负提示词/内联标签联动、全套 19 张视觉截图采集、GitHub Pages 严格子路径挂载部署 |
| 合并全量测试 | `pytest tests/test_backend.py tests/test_e2e_browser.py -v` | **47/47 PASSED**（耗时 `82.45s`） | 端到端全链路回归验证 |

---

## 3. 浏览器端到端验收明细（`tests/test_e2e_browser.py`）

1. **首页星环封面揭幕与 4 入口多端视口几何（`test_home_cover_*`）**
   - 验证首页展开后呈现 `["文章", "项目", "图像", "关于"]` 4 张入口卡片（指向 `["/articles/", "/projects/", "/gallery/", "/about/"]`），且在 4 类核心视口下均严格满足 `bottom <= height` 与零横向溢出：
     - `1440×900`（Desktop 横向 4 卡）：实测卡间水平间距 `48.95px >= 40px`，底边 `603.44px <= 900px`；
     - `390×844`（Mobile 竖屏单列 4 卡）：实测卡间垂直间距 `23.63px >= 20px`，底边 `646.91px <= 844px`；
     - `320×568`（Compact 竖屏单列 4 卡）：实测卡间垂直间距 `16.00px >= 14px`，底边 `457.17px <= 568px`；
     - `568×280`（Mobile 横屏单行 4 卡）：实测卡间水平间距 `15.89px >= 14px`，底边 `214.80px <= 280px`。
   - 覆盖鼠标滚轮暂停位置保持、移动端触控半程停驻、`prefers-reduced-motion: reduce` 降级以及手机横竖屏旋转进度保持。
2. **超窄屏导航抽屉与搜索弹窗自适应（`test_compact_navigation_and_search_fit_viewport`）**
   - 在 `280×653`、`320×568`、`568×280`、`700×360` 视口下核验顶栏操作按钮尺寸（`>= 44×44`）、抽屉焦点锁定、搜索弹窗键盘上下选择与 `220px` 极矮视口无溢出。
3. **全路由状态、资源加载与响应式零溢出（`test_routes_zero_errors_and_responsive_viewports` & `test_custom_404_page_and_assets`）**
   - 在 Desktop (`1440×900`) 与 Mobile (`390×844`) 下遍历 `/`、`/articles/`、`/projects/`、`/gallery/`、`/about/` 及全部文章详情页返回 `200`，未知路由返回真实 `404`；全程 `console.error == []`、`pageerror == []`、所有已挂载图片完整加载、零横向溢出。
4. **明暗双主题切换与持久化（`test_theme_toggle_and_persistence`）**
   - 验证默认 `"dark"` 主题（星环轨道 `.home-entry-orbits` 可见）切换至 `"light"` 后写入 `localStorage['blog-theme']`、刷新保持 `"light"`，再次点击恢复 `"dark"`。
5. **空站三大板块常驻大分类轨道与搜索空态（`test_empty_archive_and_search`）**
   - 0 条目时 `/projects/`（`全部`/`应用`/`工具`/`视觉`）、`/gallery/`（`全部`/`角色`/`场景`/`视觉`）、`/articles/`（`全部`/`代码`/`图像生成`/`工程`）均常驻展示 4 个大分类 Tab（计数均为 `0`），`[data-filter-tag]` 数量为 `0`，并分别展示 `暂无已发布项目。`、`暂无已发布图像。`、`暂无已发布文章。`。
   - 在三个板块空态下点击具体分类 Tab 均能更新 `aria-selected="true"`、驱动 `.category-indicator` `translate3d(...)` 位移并同步 `?category=...`。
6. **文章页多分类 × Tag 双层联动与详情页分类跳转（`test_categorized_articles_dual_filtering_and_navigation`）**
   - 覆盖 `/articles/` 一级大分类过滤、Tag 计数重算与不可用隐藏、分类 × Tag 二级联动、不可用 Tag 自动回退 `all`、行内分类按钮与标签点击、`?category=...&tag=...` URL 直接还原、详情页 `a.post-meta-category` 跳转及 `1440×900` / `390×844` / `320×568` / `280×653` 零溢出。
7. **项目页多分类 × Tag 双层联动与自动发现分类（`test_projects_dual_category_tag_filtering`）**
   - 验证 `/projects/` 渲染预设 `应用`/`工具`/`视觉` 与未注册自动发现分类 `实验`（共 5 个 Tab），非全量筛选时 `.projects-grid--catalog` 自动切换 `.is-filtered` 对称双栏。
   - 验证显式 `tags` 与缺省回退 `stack`（如 `SVG`）的 Tag 胶囊动态计数与隐藏、卡片内 `button.project-category-badge` 与 `.tag-pill` 点击筛选、不可用 Tag 自动回退 `all`、`ArrowRight` 键盘方向键切换分类、`?category=工具&tag=部署` URL 还原及 4 大视口零横向溢出。
8. **图像画廊双层筛选、一键复制提示词与 Lightbox 模态窗（`test_gallery_filtering_copy_prompt_and_lightbox`）**
   - **双层分类 × Tag 联动**：验证预设 `角色`/`场景`/`视觉` 与自动发现分类 `光影`（共 5 个 Tab）、分类 × Tag 二级联动（`?category=场景&tag=星环舞台`）、计数单位 `"幅"` 与指示条平滑位移。
   - **一键复制提示词与降级**：点击卡片 `.prompt-copy-btn[data-copy-prompt]` 不触发 Lightbox 弹窗，按钮切换为 `.is-copied`（`"已复制"`），且 `navigator.clipboard.readText()` 精确等于卡片完整 `data-prompt`；在剪贴板 API 拒绝且 `execCommand` 返回 `false` + `prefers-reduced-motion: reduce` 环境下，按钮展示 `.is-copy-error`（`"复制失败"`）且零未捕获异常。
   - **Lightbox `<dialog>` 全图与提示词交互**：点击 `.gallery-media-btn` 打开模态窗，验证大图完整加载（`complete && naturalWidth > 0`）、标题/分类/模型（`Flux.1 Dev`）/格式化字典参数（`steps: 28 · cfg: 3.5 ...`）/日期芯片、完整 `Prompt` 与 `Negative` 区块展示及弹窗内一键复制；无 `negative_prompt` 的作品自动隐藏 `Negative` 区块；点击 Lightbox 内标签（`黑胶美学`）自动关闭弹窗并联动筛选画廊；点击关闭按钮 `[data-gallery-close]`、点击遮罩背景或按 `Escape` 均正常关闭并归还焦点；4 大视口零横向溢出。
9. **长文阅读体验、移动端折叠目录与 GitHub Pages 子路径部署（`test_post_reading_experience`、`test_mobile_toc_and_clipboard_unavailable`、`test_github_pages_subpath_deployment`）**
   - 验证桌面端 TOC 联动、阅读进度条、代码复制、移动端折叠 TOC 以及 `/astrayao-blog/` 严格子路径挂载下全站资源与搜索跳转零错误。

---

## 4. 视觉审阅闭环与截图清单

### 4.1 视觉优化与回归闭环

- **第一、二、三阶段**：已完成表格代码防断词、搜索框原生蓝叉消除、暗色插画柔光、移动端首行基线对齐，以及文章页二级 Tag 香槟金柔底描边层级精修与 `390×844` 大分类轨道首屏全显优化（#50 签字通过）。
- **第四阶段（首页 4 入口 + 项目页双层分类 + `/gallery/` 图像提示词画廊与 Lightbox）**：
  - `qa-verifier` 采集 7 张新增全窗口截图并通过 `read_file` 自审后提交（#60）。
  - `ui-designer` 逐张审阅 `home-entries-4-dark.png`、`home-entries-4-mobile.png`、`projects-categories-dark.png`、`gallery-dark.png`、`gallery-light.png`、`gallery-lightbox.png`、`gallery-mobile-dark.png`，确认构图平衡、4 入口琴键错落韵律、4:3 画廊展框、一键复制触感与双栏 Lightbox 比例均达出版级水准，于 `#61` **零瑕疵正式签字通过**。

### 4.2 最终视觉验收截图清单（保存于会话 brain 目录）

| 场景 | 主题与视口 | 截图文件绝对路径 |
| --- | --- | --- |
| 首页展开 4 入口（文章 / 项目 / 图像 / 关于 · 桌面端） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-entries-4-dark.png` |
| 首页展开 4 入口（文章 / 项目 / 图像 / 关于 · 移动端） | `dark` · `390×844` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-entries-4-mobile.png` |
| 项目页（多分类轨道 + 二级 Tag + 对称双栏卡片） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\projects-categories-dark.png` |
| 图像页（多分类轨道 + 4:3 画廊卡片 + 提示词复制 · 暗夜） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\gallery-dark.png` |
| 图像页（多分类轨道 + 4:3 画廊卡片 + 提示词复制 · 象牙） | `light` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\gallery-light.png` |
| 图像页 Lightbox 模态窗（左全图舞台 + 右完整正负提示词） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\gallery-lightbox.png` |
| 移动端图像页（大分类轨道 + Tag 胶囊 + 画廊卡片） | `dark` · `390×844` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\gallery-mobile-dark.png` |
| 文章页（多分类轨道 + 二级 Tag 列表 · 暗夜） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-categories-dark.png` |
| 文章页（多分类轨道 + 二级 Tag 列表 · 象牙） | `light` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-categories-light.png` |
| 文章页（空归档常驻大分类栏 + 星环空态） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-empty-dark.png` |
| 移动端文章页（大分类轨道 + Tag 胶囊 + 列表） | `dark` · `390×844` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-mobile-dark.png` |
| 文章详情页（可点击分类徽章 + Tag 胶囊 + 封面） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\post-detail-tags.png` |
| 首页主视觉（星环封面） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-dark.png` |
| 首页展开入口（象牙日间） | `light` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-light.png` |
| 文章页 + Cmd/Ctrl+K 搜索弹窗命中结果 | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\articles-search.png` |
| 文章详情页（正文 + 代码块 + TOC） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\post-detail.png` |
| 项目页（单项目基础夹具视图） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\projects.png` |
| 关于页（含耀嘉音天琴座徽章框） | `dark` · `1440×900` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\about.png` |
| 移动端首页封面视图 | `dark` · `390×844` | `C:\Users\Administrator\.gemini\antigravity\brain\0163651c-5527-4adf-88f0-50d778637e7e\home-mobile.png` |
