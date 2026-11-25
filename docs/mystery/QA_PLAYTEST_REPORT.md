# 《大闰录 · 卷一：纸傩代身》（CASE-LXJZ-61）QA 验收与通关报告

> 本报告记录初版验收。新版验证范围和游玩时长口径见 [前两卷实现说明](PLAYBOOK.md)。

## 1. 验收结论

**全量门禁与自动化测试全部通过（绿灯）**，核心玩法链路、6 入口首页布局、子路径 `/astrayao-blog/mystery/` 部署、移动端 `390×844` 响应式抽屉、14 条线索 / 6 组提示 / 3 种结局及存档重置功能均已验证无误。

---

## 2. 门禁与自动化测试执行记录

| 检查项 | 命令 | 结果 |
| --- | --- | --- |
| 子路径构建与静态校验 | `python scripts/check.py --base-path /astrayao-blog --site-url https://example.github.io/astrayao-blog` | **PASS**：14 HTML 页面，6 篇文章，6 条搜索索引，15 张图片资源，606 条站内链接全部校验通过，0 未替换占位符 |
| 根路径构建恢复与校验 | `python scripts/check.py` | **PASS**：14 HTML 页面，6 篇文章，6 条搜索索引，15 张图片资源，606 条站内链接全部校验通过（`base_path='/'`） |
| 后端与迷局全流程自动化 | `pytest tests/test_backend.py tests/test_mystery.py` | **24 passed in 9.09s** |
| 全站 E2E 浏览器回归 | `pytest tests/test_e2e_browser.py` | **27 passed in 98.25s** |

### 测试套件更新说明
- [tests/test_mystery.py](file:///d:/网页运营/tests/test_mystery.py)：合入《大闰录 · 卷一：纸傩代身》全链路自动化测试，涵盖：
  - `test_darun_static_data_and_puzzle_integrity`：校验 `CASE-LXJZ-61`、`CLUE-001`~`CLUE-014`、`PZ-01`~`PZ-06`（3 档提示）、终审 `Q1`~`Q5`、3 结局、全部触发源及静态文件无未渲染 `{{ }}` 占位符。
  - `test_darun_full_playthrough_and_meta_ending`：`1440×900` 桌面端完整通关 14 条线索，依次触发 `ending_normal`、`ending_true` 与 Meta 隐藏结局 `ending_hidden`（`第六十一甲子` / `星环手记`），零控制台错误与请求失败。
  - `test_darun_subpath_mobile_and_games_banner`：`/astrayao-blog` 子路径 + `390×844` 移动端，校验 `/games/` 横幅跳转、证据板抽屉开合无横向溢出、重置存档清零，以及所有 `static/mystery/` JSON/SVG 200 加载。
- [tests/test_backend.py](file:///d:/网页运营/tests/test_backend.py)：更新 sitemap 路由数（`7 + len(posts)` 与 `/mystery/`）、`html_pages_count`（10 / 空站 8）、`expected_paths`（补充 `mystery/index.html`、`static/mystery/js/app.js`、`static/mystery/data/case_manifest.json`、`static/mystery/assets/case-emblem.svg`）及首页 `home-entry` 计数（`6`）。
- [tests/test_e2e_browser.py](file:///d:/网页运营/tests/test_e2e_browser.py)：更新首页 6 卡网格间距断言（`1440×900` 3×2 行内与行间间距、`568×280` 单行 6 卡 5 间距、`390×844` / `320×568` 单列 6 卡 5 间距）、入口计数 `6`、`routes` 包含 `/mystery/`，以及 6 入口名称与 `href` 校验。

---

## 3. 全链路通关轨迹（14/14 线索 & 3 结局）

1. **入口与门户（`https://darun.local/portal`）**：从首页「迷局」入口进入，收取 `CLUE-001`（异常备案号 `丰ICP备-LXJZ-61`），并验证 `PZ-01` 第 1 档提示解锁。
2. **千度旧网检索（`https://search.qiandu.lh/`）**：
   - 使用 `site:blog.shanye.lh` 命中未公开草稿 `draft-wild-temple` -> 收取 `CLUE-014`。
   - 触发彩蛋检索 `LXJZ-61` -> 跳转 `feiyi.fengning.gov.lh/archive/darun-draft-61` 收取 `CLUE-007`。
3. **山野拾影博客（`https://blog.shanye.lh/post/...`）**：
   - `taiping-stage` 确认太平社年份 `1994`；
   - `temple-smoke` 反白显影收取 `CLUE-002`，查看网页源码注释获取 `NUOX` 并收取 `CLUE-003`；
   - `locked-404b` 输入口令 `NUOX1994` 解锁收取 `CLUE-004`。
4. **老黄历民俗茶馆 BBS（`https://bbs.huangli.lh/`）**：
   - `thread/618` 确认常驻异常万年历（`甲辰年 闰腊月 廿九` / `2019年02月30日`）并收取 `CLUE-009`（`0815`）；
   - `thread/610` 开启 `2019-02-30` 网页时光机还原 `2F / 5F / 8F`，收取 `CLUE-005`、`CLUE-006`、`CLUE-008`（密匙段 `0230`）。
5. **槐安里物业公示网（`https://wy.huaianli.lh/notice/building7-demolition`）**：时光机状态下呈现原版/篡改版双栏对比与测绘员名片，收取 `CLUE-012`。
6. **丰宁非遗保护中心内网（`https://feiyi.fengning.gov.lh/internal`）**：
   - 以 `FY-2018-061` / `cyq081561` 登录；
   - 查阅 `doc-paper-nuo`（1994 太平社 13 人合影与《纸傩代身诀》）收取 `CLUE-010`；
   - 查阅 `doc-genealogy-leak` 收取 `CLUE-011`。
7. **第 61 号档案库总录与终审（`https://darun.local/vault-61`）**：
   - 输入最终密匙 `ZN404B610230` 解封卷宗，收取 `CLUE-013`（达成 `14 / 14`）；
   - 终审提交 `AABB` + `未知` 触发 **普通结局**，`BABB` + `未知` 触发 **真结局**，`BABB` + `星环手记` 触发 **Meta 隐藏结局《第六十一甲子：星环裂隙的凝视》**。

---

## 4. 视觉截屏验收清单（1440×900 暗色全屏）

- `C:\Users\Administrator\.gemini\antigravity\brain\5c3edbf5-656f-4e07-a36b-59e6c0f621f8\01_home_6_entries.png` — 首页 6 入口 3×2 网格
- `C:\Users\Administrator\.gemini\antigravity\brain\5c3edbf5-656f-4e07-a36b-59e6c0f621f8\02_darun_portal.png` — 旧网拾遗门户与首条线索
- `C:\Users\Administrator\.gemini\antigravity\brain\5c3edbf5-656f-4e07-a36b-59e6c0f621f8\03_huaianli_wayback.png` — 槐安里 404B 时光机双栏对比
- `C:\Users\Administrator\.gemini\antigravity\brain\5c3edbf5-656f-4e07-a36b-59e6c0f621f8\04_huangli_almanac_bbs.png` — 老黄历茶馆异常万年历与时光机还原
- `C:\Users\Administrator\.gemini\antigravity\brain\5c3edbf5-656f-4e07-a36b-59e6c0f621f8\05_fengning_internal_photo.png` — 丰宁非遗内网 13 人合影档案
- `C:\Users\Administrator\.gemini\antigravity\brain\5c3edbf5-656f-4e07-a36b-59e6c0f621f8\06_meta_hidden_ending.png` — Meta 隐藏结局《第六十一甲子》视窗
