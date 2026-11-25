# 《大闰录 · 卷一：纸傩代身》前后端数据与渲染器接口契约（DATA_SCHEMA）

> 此契约对应初版浏览器外壳和终审。现行结构以 [前两卷实现说明](PLAYBOOK.md) 及各卷 JSON 为准。

> **总案号**：`CASE-LXJZ-61`  
> **适用团队**：引擎组（`engine-lead`）、官方站点组（`sites-official`）、社区站点组（`sites-community`）、视觉美术组（`ui-art-director`）  
> **文档性质**：全部 6 份 JSON 数据文件、虚拟 URL 路由、`darun_save_v1_ch01` 持久化存档、DOM 交互属性及 `window.MysteryRenderers` 接口的唯一技术真源。

---

## 一、目录布局与团队分工矩阵

| 资源路径 | 负责角色 | 说明 |
| :--- | :--- | :--- |
| `/static/mystery/data/site_search.json` | `sites-official` | 千度旧网检索（`search.qiandu.lh`）词条索引、热搜、`site:` 与暗语彩蛋 |
| `/static/mystery/data/site_institution.json` | `sites-official` | 丰宁县非物质文化遗产保护中心（`feiyi.fengning.gov.lh`）公开页、合影档案、内网登录门与纸傩/族谱密档 |
| `/static/mystery/data/site_property.json` | `sites-official` | 槐安里小区物业与拆迁公示网（`wy.huaianli.lh`，替代旧 `site_news_archive.json`）公示、404B 幽灵夹层、失踪测量员与时光机对比 |
| `/static/mystery/js/renderers/official_renderers.js` | `sites-official` | 注册 `window.MysteryRenderers` 的 `search`、`institution`、`property` 三个渲染器 |
| `/static/mystery/data/case_manifest.json` | `sites-community` | 全局案件配置、表网导航门户配置、书签、5+2 站点映射、14 条线索字典、6 组×3 档提示、第 61 号总录秘匣、5 道终审题与 3 结局 |
| `/static/mystery/data/site_blog.json` | `sites-community` | 山野拾影博客（`blog.shanye.lh`）博主资料、公开/未公开/加密日志、反白字、源码注释、评论 |
| `/static/mystery/data/site_forum.json` | `sites-community` | 老黄历民俗茶馆 BBS（`bbs.huangli.lh`）异常老黄历挂件、板块、主题帖、时光机被删楼层还原、站内私信 |
| `/static/mystery/js/renderers/community_renderers.js` | `sites-community` | 注册 `window.MysteryRenderers` 的 `blog`、`forum`、`portal`、`vault61` 四个渲染器 |
| `/static/mystery/css/browser_shell.css` & `sites_themes.css` & `assets/*.svg` | `ui-art-director` | 拟真浏览器外壳、5+2 主题皮肤与 5 枚自包含民俗 SVG |
| `/static/mystery/js/state_store.js`、`search_engine.js`、`engine.js`、`app.js` | `engine-lead` | 存档与终审引擎、检索算法、多标签路由与事件委托内核、博客入口集成 |

---

## 二、全局标识、路由与 DOM 契约

### 2.1 统一标识符规范
- **总案号（`caseId`）**：`CASE-LXJZ-61`
- **存档键名（`localStorage`）**：`darun_save_v1_ch01`
- **线索 ID（`clueId`）**：`CLUE-001` 至 `CLUE-014`（共 14 条）
- **谜题 ID（`puzzleId`）**：`PZ-01` 至 `PZ-06`（共 6 个）
- **解锁门 ID（`gateId`）**：
  - `gate-search-darun`：千度检索异常暗语彩蛋触发（`LXJZ-61` / `闰腊月廿九` / `2019-02-30`）
  - `gate-blog-locked`：山野博客加密日志（口令 `NUOX1994`）
  - `gate-feiyi-internal`：丰宁非遗保护中心内网登录（工号 `FY-2018-061` + 口令 `cyq081561`）
  - `gate-vault-61`：渊网第 61 号档案库印章门禁（校历密匙 `ZN404B610230`）
- **结局 ID（`endingId`）**：`ending_normal`、`ending_true`、`ending_hidden`

### 2.2 虚拟 URL 路由表（5 个日常站点 + 2 个本地终端）

| 虚拟域名 | 渲染器 Key | 支持路径（Canonical Path） | 主题类（`themeClass`） | 页面用途 |
| :--- | :--- | :--- | :--- | :--- |
| `darun.local` | `portal` | `/`、`/portal` | `site-theme-portal` | 表网日常伪装入口：「旧网拾遗 · 地方网页归档导航」（默认 `homeUrl`） |
| `darun.local` | `vault61` | `/vault-61` | `site-theme-vault61` | 渊网终局终端：「大闰总录（第 61 号档案库）」（`verdictUrl`，含秘匣门禁 + 5 题终审） |
| `search.qiandu.lh` | `search` | `/`、`/search?q=...` | `site-theme-search` | 千度旧网检索（岁差镜像） |
| `feiyi.fengning.gov.lh` | `institution` | `/`、`/notices`、`/notices/:id`、`/staff`、`/archives`、`/archive/darun-draft-61` | `site-theme-institution` | 丰宁县非遗保护中心公开官网与岁差缓存页 |
| `feiyi.fengning.gov.lh` | `institution` | `/internal`、`/internal/:docId` | `site-theme-institution site-theme-institution--internal` | 丰宁非遗内部馆藏系统（未登录为表单态，登录后切换暗玄朱砂终端态） |
| `wy.huaianli.lh` | `property` | `/`、`/notice/:id`（核心：`building7-demolition`）、`/surveyor`、`/floorplan` | `site-theme-property` | 槐安里小区物业与拆迁公示网（时光机对比核心站点） |
| `blog.shanye.lh` | `blog` | `/`、`/post/taiping-stage`、`/post/temple-smoke`、`/post/draft-wild-temple`、`/post/locked-404b` | `site-theme-blog` | 山野拾影 · 民俗摄影手记 |
| `bbs.huangli.lh` | `forum` | `/`、`/board/:id`、`/thread/610`、`/thread/618`、`/thread/605`、`/messages` | `site-theme-forum` | 老黄历民俗茶馆 BBS（内置异常万年历挂件） |

> **路由解析要求（`engine.js`）**：当 `domain === "darun.local"` 时，`/` 自动归一化至 `/portal`（`siteKey = "portal"`），`/portal` 映射 `portal`，`/vault-61` 映射 `vault61`；其余域名查 `manifest.sites` 按 `domain` 匹配 `siteKey`。

### 2.3 DOM 交互属性与关键类名契约（对齐 `ui-art-director` #19）

1. **线索收集触发器**：`.mystery-clue-trigger[data-clue-id="CLUE-XXX"]`，已收集时附加 `.is-collected`。
2. **站内虚拟跳转**：`<a href="https://..." data-mystery-link="https://...">`（可选 `data-new-tab="true"`）。
3. **博客反白隐藏字**：`.mystery-hidden-ink[data-hidden-ink="ink-temple-smoke"]`，显影后附加 `.is-revealed`。
4. **论坛时光机还原**：还原楼层容器使用 `.mystery-restored-post`；顶部异常万年历挂件使用 `.site-forum-almanac`。
5. **物业时光机差异对比（严格对齐 CSS）**：
   - 外层容器：`.mystery-snapshot-diff`
   - 标题条：`.mystery-diff-header`
   - 双栏网格：`.mystery-diff-grid`
   - 左栏（覆写前 / 原版保留或删改前）：`.mystery-diff-col.mystery-diff-col--before` + `.mystery-diff-label` + 删除高亮 `.mystery-diff-del`
   - 右栏（覆写后 / 原版还原对照）：`.mystery-diff-col.mystery-diff-col--after` + `.mystery-diff-label` + 增补/还原高亮 `.mystery-diff-ins`
6. **新增专属主题组件类名**：
   - 表网入口：`.site-portal-grid`、`.site-portal-card`、`.site-portal-icp`（页脚可点击异常备案号栏）
   - 非遗官网：`.site-inst-photo-frame`（1994 戏班合影线描/复原相框）
   - 槐安里物业：`.site-prop-anomaly`（404B 幽灵夹层警示块）、`.site-prop-surveyor-card`（失踪测量员档案卡）
   - 渊网第 61 号档案库：`.site-vault-gate`（校历密匙印章门禁卡片），下半区终审表单复用 `.site-verdict-*` 语义类。

---

## 三、六份 JSON 文件唯一真源 Schema

### 3.1 `static/mystery/data/case_manifest.json`（`sites-community` 维护）

```json
{
  "schemaVersion": "2.0.0",
  "caseId": "CASE-LXJZ-61",
  "storageKey": "darun_save_v1_ch01",
  "seriesTitle": "大闰录",
  "title": "大闰录 · 卷一：纸傩代身",
  "subtitle": "岁差档案 CASE-LXJZ-61 · 丰宁县槐安里与纸傩戏班异常重查",
  "homeUrl": "https://darun.local/portal",
  "verdictUrl": "https://darun.local/vault-61",
  "timeMachineDefaultDate": "2019-02-30",
  "assets": {
    "caseEmblem": "/static/mystery/assets/case-emblem.svg",
    "institutionLogo": "/static/mystery/assets/institution-logo.svg",
    "archiveStamp": "/static/mystery/assets/archive-stamp.svg",
    "blogAvatar": "/static/mystery/assets/blog-avatar.svg",
    "clueNetwork": "/static/mystery/assets/clue-network.svg"
  },
  "bookmarks": [
    {
      "id": "bm-portal",
      "label": "旧网拾遗",
      "url": "https://darun.local/portal",
      "icon": "portal"
    },
    {
      "id": "bm-search",
      "label": "千度旧网检索",
      "url": "https://search.qiandu.lh/",
      "icon": "search"
    },
    {
      "id": "bm-institution",
      "label": "丰宁非遗中心",
      "url": "https://feiyi.fengning.gov.lh/",
      "icon": "institution"
    },
    {
      "id": "bm-property",
      "label": "槐安里物业网",
      "url": "https://wy.huaianli.lh/",
      "icon": "property"
    },
    {
      "id": "bm-blog",
      "label": "山野拾影博客",
      "url": "https://blog.shanye.lh/",
      "icon": "blog"
    },
    {
      "id": "bm-forum",
      "label": "老黄历茶馆BBS",
      "url": "https://bbs.huangli.lh/",
      "icon": "forum"
    },
    {
      "id": "bm-vault61",
      "label": "第61号档案库",
      "url": "https://darun.local/vault-61",
      "icon": "verdict",
      "isSpecial": true
    }
  ],
  "sites": [
    {
      "siteKey": "search",
      "domain": "search.qiandu.lh",
      "name": "千度旧网检索",
      "themeClass": "site-theme-search",
      "dataUrl": "/static/mystery/data/site_search.json"
    },
    {
      "siteKey": "institution",
      "domain": "feiyi.fengning.gov.lh",
      "name": "丰宁县非物质文化遗产保护中心",
      "themeClass": "site-theme-institution",
      "dataUrl": "/static/mystery/data/site_institution.json"
    },
    {
      "siteKey": "property",
      "domain": "wy.huaianli.lh",
      "name": "槐安里小区物业与拆迁公示网",
      "themeClass": "site-theme-property",
      "dataUrl": "/static/mystery/data/site_property.json"
    },
    {
      "siteKey": "blog",
      "domain": "blog.shanye.lh",
      "name": "山野拾影 · 民俗摄影手记",
      "themeClass": "site-theme-blog",
      "dataUrl": "/static/mystery/data/site_blog.json"
    },
    {
      "siteKey": "forum",
      "domain": "bbs.huangli.lh",
      "name": "老黄历民俗茶馆 BBS",
      "themeClass": "site-theme-forum",
      "dataUrl": "/static/mystery/data/site_forum.json"
    }
  ],
  "portal": {
    "title": "旧网拾遗 · 丰宁地方网页归档导航",
    "subtitle": "收录 1998–2024 年间丰宁县民生公示、文化场馆与个人独立小站快照镜像",
    "notice": "本站仅作地方数字志怀旧保存，如遇页面缺字、日期错乱或楼层屏蔽，可尝试切换浏览器顶栏「网页时光机」或「查看源码」核对原始报文。",
    "directoryCards": [
      {
        "title": "千度旧网检索（岁差镜像）",
        "domain": "search.qiandu.lh",
        "url": "https://search.qiandu.lh/",
        "category": "站内索引",
        "description": "检索丰宁旧网文章、公告与被降权折叠的隐藏网页，支持 site: 语法。"
      },
      {
        "title": "丰宁县非物质文化遗产保护中心",
        "domain": "feiyi.fengning.gov.lh",
        "url": "https://feiyi.fengning.gov.lh/",
        "category": "政务与文化馆",
        "description": "查阅丰宁纸傩戏、传统木作非遗名录、人员公示及内部馆藏检索入口。"
      },
      {
        "title": "槐安里小区物业与拆迁公示网",
        "domain": "wy.huaianli.lh",
        "url": "https://wy.huaianli.lh/",
        "category": "社区民生",
        "description": "槐安里老小区 7 号楼拆迁复核通告、户型测绘记录与物业值班公示。"
      },
      {
        "title": "山野拾影 · 民俗摄影手记",
        "domain": "blog.shanye.lh",
        "url": "https://blog.shanye.lh/",
        "category": "个人网志",
        "description": "民俗胶片摄影师林野的丰宁采风笔记，记录老戏台与后山野庙。"
      },
      {
        "title": "老黄历民俗茶馆 BBS",
        "domain": "bbs.huangli.lh",
        "url": "https://bbs.huangli.lh/",
        "category": "地方论坛",
        "description": "丰宁老网民择吉测字、乡野异闻与旧城拆迁讨论区（附怀旧老黄历挂件）。"
      }
    ],
    "icpFooter": {
      "maintainer": "归档维护：丰宁地方旧网互助组",
      "icpCode": "丰ICP备-LXJZ-61",
      "anomalyHint": "点击核验异常备案号（LXJZ-61）并收集初始线索",
      "clueId": "CLUE-001",
      "vaultLinkLabel": "进入渊网：大闰总录（第 61 号档案库）",
      "vaultUrl": "https://darun.local/vault-61"
    },
    "sourceComment": "<!-- [PORTAL_AUDIT] 备案号 丰ICP备-LXJZ-61 非正规工信编码。建议于 search.qiandu.lh 检索 LXJZ-61 或巡查五处地方小站。 -->"
  },
  "vault61": {
    "title": "大闰总录 · 第 61 号档案库",
    "subtitle": "岁差校正委员会（钦天余脉）渊网终端 · 档案号 CASE-LXJZ-61",
    "stampUrl": "/static/mystery/assets/archive-stamp.svg",
    "gate": {
      "gateId": "gate-vault-61",
      "title": "朱砂印章门禁：请呈递【校历密匙】",
      "formulaHint": "按「形 · 宅 · 名 · 时」四柱顺序拼接 12 位密匙：[纸傩卷宗前缀2位] + [槐安里幽灵房号4位] + [异常备案尾号2位] + [时错无历月日4位]",
      "placeholder": "输入 12 位校历密匙（如 ZN-XXXX-XX-XXXX）",
      "acceptedKeys": [
        "ZN404B610230"
      ]
    },
    "unlockedDossier": {
      "code": "CHRONICLE-61-META",
      "title": "第 61 号总录：太闰全貌与「星环手记」岁差观测日志",
      "clueId": "CLUE-013",
      "clueLabel": "收录终极密卷：星环手记即现实世界的数字闰隙",
      "paragraphs": [
        "段落一：总结形替（纸傩）、宅镇（404B）、名录（族谱多出之名）、时错（闰腊月廿九/02-30）、祀伪（空心神像）五脉皆为【太闰】代位填缺之局。",
        "段落二：揭晓终极 Meta 反转——你此刻所处的宿主网站「ASTRA YAO · 星环手记」本身，就是现实互联网中一处天然的数字闰隙，岁差校正委员会借星环闭合处的 0.61 秒缝隙挂载此沙盒，以观测【太闰】并遴选新任校历人。"
      ]
    },
    "sourceComment": "<!-- [VAULT_61] 若尚未拼齐校历密匙，仍可先在下方提交岁差校正委员会基础终审；集齐 ZN404B610230 解封总录并答对 Q5 方可开启终极 Meta 隐藏结局。 -->"
  },
  "clues": [
    {
      "clueId": "CLUE-001",
      "title": "异常备案号：丰ICP备-LXJZ-61",
      "summary": "旧网拾遗页脚藏有非正规备案号「丰ICP备-LXJZ-61」，尾号 61 指向第六十一甲子。",
      "category": "portal",
      "sourceSite": "旧网拾遗",
      "sourceUrl": "https://darun.local/portal",
      "puzzleId": "PZ-01",
      "isKeyEvidence": true
    }
  ],
  "hints": [
    {
      "puzzleId": "PZ-01",
      "title": "千度旧网检索：site: 定向挖掘与岁差暗语",
      "completedWhenClues": [
        "CLUE-014",
        "CLUE-007"
      ],
      "tiers": [
        {
          "level": 1,
          "label": "轻度提示",
          "text": "表网入口页脚那串备案号看着不太合规矩..."
        },
        {
          "level": 2,
          "label": "方向提示",
          "text": "打开千度旧网检索，试试 site: 语法限定山野博客域名，再搜异常备案号或异常日期。"
        },
        {
          "level": 3,
          "label": "直白思路",
          "text": "输入 site:blog.shanye.lh 得野庙草稿（CLUE-014）；输入 LXJZ-61 或 闰腊月廿九 或 2019-02-30 触发岁差缓存（CLUE-007）。"
        }
      ]
    }
  ],
  "verdict": {
    "recommendedMinClues": 6,
    "questions": [
      {
        "id": "Q1",
        "dimension": "高位源头与驱动力",
        "type": "single_choice",
        "prompt": "丰宁县接连发生的纸傩合影多出一人、槐安里 404B 夹层、老黄历闰腊月廿九与野庙空心神像，其背后的共同高位推手与驱动力是什么？",
        "options": [
          {
            "value": "A",
            "label": "古代冤魂借老剧场拆迁实施定向复仇"
          },
          {
            "value": "B",
            "label": "高位存在【太闰】（第六十一甲子 / 无名太岁），因在正历中无合法席位，本能制造“多余之物”并以假象逐步替换真实原件"
          }
        ],
        "correctAnswer": "B",
        "wrongFeedback": "请重新查阅千度检索岁差缓存（CLUE-007）与非遗馆内部密档。"
      },
      {
        "id": "Q5",
        "dimension": "终极 Meta 破壁真相",
        "type": "text_input",
        "prompt": "解封《第 61 号总录》后可知：挂载着整套《大闰录》旧网镜像、且本身就是现实世界一处“数字闰隙”的宿主网站名称是什么？",
        "placeholder": "请输入宿主站点中文名（若尚未解封总录可填“未知”）",
        "acceptedAnswers": [
          "星环手记",
          "astrayao星环手记",
          "astrayao",
          "星环",
          "星环手记博客",
          "starloop"
        ],
        "optionalForTrueEnding": true,
        "wrongFeedback": "提示：拼齐 12 位【校历密匙】解封第 61 号总录（CLUE-013）即可获知宿主站点真相。"
      }
    ],
    "endings": {
      "ending_hidden": {
        "id": "ending_hidden",
        "badge": "隐藏结局 · 第六十一甲子",
        "title": "第六十一甲子：星环裂隙的凝视",
        "requiredClues": [
          "CLUE-013"
        ],
        "minTotalClues": 10,
        "summary": "你不仅封住了丰宁四柱，还看穿了屏幕之外那道真实的“数字闰隙”。",
        "paragraphs": [
          "隐藏 Meta 结局完整正文..."
        ],
        "debriefTimeline": [
          "全案五脉复盘要点..."
        ]
      },
      "ending_true": {
        "id": "ending_true",
        "badge": "真结局 · 正历暂安",
        "title": "补缺暂止：槐安里封梁纪事",
        "requiredClues": [],
        "minTotalClues": 0,
        "summary": "你成功阻止了槐安里 7 号楼闷梁破拆，但第 61 号总录背后仍藏着更深的裂隙。",
        "paragraphs": [
          "真结局完整正文..."
        ],
        "debriefTimeline": [
          "复盘要点..."
        ]
      },
      "ending_normal": {
        "id": "ending_normal",
        "badge": "普通结局 · 岁差未平",
        "title": "闰雾未散：正历边缘的残响",
        "requiredClues": [],
        "minTotalClues": 0,
        "summary": "卷宗仍存在核心疏漏，岁差校正委员会暂缓批准封梁令。",
        "paragraphs": [
          "普通结局完整正文..."
        ],
        "debriefTimeline": [
          "复查指引..."
        ]
      }
    }
  }
}
```

---

### 3.2 `static/mystery/data/site_search.json`（`sites-official` 维护）

```json
{
  "siteName": "千度旧网检索",
  "domain": "search.qiandu.lh",
  "tagline": "丰宁地方旧网中文索引 · 岁差归档镜像（1998–2024）",
  "hotQueries": [
    "纸傩",
    "槐安里",
    "周延生",
    "404B",
    "site:blog.shanye.lh"
  ],
  "syntaxTips": [
    "使用 site:域名 可定向发掘被主页隐藏或降权的旧网页（如：site:blog.shanye.lh）",
    "尝试检索你在页脚或老黄历中发现的异常备案编号与不可能存在的日期"
  ],
  "easterEggs": [
    {
      "id": "egg-darun-61",
      "gateId": "gate-search-darun",
      "triggers": [
        "LXJZ-61",
        "丰ICP备-LXJZ-61",
        "闰腊月廿九",
        "甲辰年闰腊月廿九",
        "2019-02-30",
        "第六十一甲子"
      ],
      "bannerTitle": "检测到岁差索引裂隙缓存（异常时间戳：2019-02-30）",
      "bannerNote": "该页面原位于 feiyi.fengning.gov.lh，已从正历索引抹除，仅在岁差镜像中残留。",
      "resultId": "sr-darun-cache-61"
    }
  ],
  "entries": [
    {
      "id": "sr-blog-draft-temple",
      "title": "[未公开草稿] 白衣野庙空心神像：泥胎里的黄表纸与香火截流 - 山野拾影",
      "url": "https://blog.shanye.lh/post/draft-wild-temple",
      "domain": "blog.shanye.lh",
      "date": "2024-11-06",
      "snippet": "掀开后山白衣野庙泥胎背部的裂缝，里面密密麻麻塞满写着槐安里住户生辰八字的黄表纸与《纸傩代身诀》残页...",
      "keywords": [
        "野庙",
        "空心",
        "神像",
        "黄表纸",
        "纸傩",
        "香火",
        "林野",
        "草稿"
      ],
      "isSnapshotOnly": false,
      "requireSiteOperator": true,
      "unlockGate": null,
      "badge": "降权草稿"
    },
    {
      "id": "sr-darun-cache-61",
      "title": "[岁差缓存] 岁差校正委员会截留札记：天道有缺与第六十一甲子 - 丰宁非遗中心",
      "url": "https://feiyi.fengning.gov.lh/archive/darun-draft-61",
      "domain": "feiyi.fengning.gov.lh",
      "date": "2019-02-30",
      "snippet": "名、时、形、祀四柱锚定正历；六十甲子之外不可书写的【太闰】正借纸傩、厌胜、族谱、黄历与淫祀制造多余之物并替换原件...",
      "keywords": [
        "LXJZ-61",
        "太闰",
        "闰腊月廿九",
        "2019-02-30",
        "第六十一甲子"
      ],
      "isSnapshotOnly": true,
      "requireSiteOperator": false,
      "unlockGate": "gate-search-darun",
      "badge": "岁差缓存"
    }
  ]
}
```

---

### 3.3 `static/mystery/data/site_institution.json`（`sites-official` 维护）

驱动「丰宁县非物质文化遗产保护中心（`https://feiyi.fengning.gov.lh`）」与内部馆藏终端（`/internal`）。

```json
{
  "siteName": "丰宁县非物质文化遗产保护中心",
  "shortName": "丰宁非遗中心",
  "domain": "feiyi.fengning.gov.lh",
  "logoUrl": "/static/mystery/assets/institution-logo.svg",
  "stampUrl": "/static/mystery/assets/archive-stamp.svg",
  "motto": "守护乡邦文脉 · 传承丰宁百戏",
  "overview": {
    "established": "1989年",
    "address": "丰宁县城东文化街 42 号",
    "intro": "承担丰宁县纸傩戏、传统木作厌胜文献与地方民俗志的征集、数字化归档与研究保护。",
    "sourceComment": "<!-- FENGNING_FEIYI_CMS | internal: /internal | employeeId format: FY-YYYY-NNN -->"
  },
  "notices": [
    {
      "id": "2018-archive-recruit",
      "title": "关于 2018 年度非遗数字化归档专员录用及工号编制的公示",
      "date": "2018-08-10",
      "department": "办公室（人事档案组）",
      "summary": "公示 2018 年录用人员系统登记序号及内部馆藏工号统一生成规则。",
      "content": [
        "经县文旅局核准，现公示 2018 年度非遗数字化归档专员录用名单。本中心内部系统工号统一按「FY-入职年份(4位)-系统三位序号」生成。"
      ],
      "tableHeaders": [
        "姓名",
        "入职年份",
        "系统序号",
        "分配科室"
      ],
      "tableRows": [
        [
          "陈砚青",
          "2018",
          "061",
          "特级民俗底片与数字归档室"
        ]
      ]
    }
  ],
  "staffDirectory": {
    "idRuleNote": "本中心在编及封存人员统一工号编码规则：FY-入职年份(4位)-三位序号（示例：FY-2006-003）。",
    "members": [
      {
        "employeeId": "FY-2006-003",
        "name": "赵承安",
        "title": "保护中心主任",
        "department": "中心办公室",
        "status": "在职",
        "note": "分管地方戏曲普查与老旧档案封存审批。"
      },
      {
        "employeeId": "FY-1994-013",
        "name": "白鹤年",
        "title": "丰宁纸傩戏「太平社」末代班主",
        "department": "传统戏剧传承名录（历史封存）",
        "status": "1994年冬失联",
        "note": "留存 1994 年戏班合影底片（FN-FY-1994-13）及纸傩工艺口述残稿。"
      }
    ]
  },
  "publicExhibits": [
    {
      "code": "FN-FY-1994-13",
      "title": "1994 年丰宁纸傩戏班「太平社」末场演出合影（公开缩略件）",
      "year": "1994",
      "caption": "原始名册登记 12 名艺人，公开版已裁去最右侧模糊边缘；高清原片及异常比对封存于内部馆藏系统。",
      "description": "介绍丰宁纸傩戏以竹篾宣纸扎制替身面具、岁末酬神祛煞的古老仪轨。"
    }
  ],
  "cachedArchivePages": {
    "darun-draft-61": {
      "id": "darun-draft-61",
      "title": "[岁差缓存] 岁差校正委员会截留札记：天道有缺与第六十一甲子",
      "cachedAt": "2019-02-30 00:61",
      "deletedNote": "该文本系钦天余脉暂存于服务器临时目录的内部备忘，已在正历站点清除，仅可通过千度暗语检索还原。",
      "paragraphs": [
        "详述正历由【时、名、形、祀】四柱锚定，以及高位存在【太闰】（无名太岁 / 第六十一甲子）通过制造多余之物并替换原件侵蚀人间的底层机制..."
      ],
      "clueId": "CLUE-007",
      "clueLabel": "收集证据：岁差缓存札记（太闰与四柱宇宙观）"
    }
  },
  "internalGate": {
    "gateId": "gate-feiyi-internal",
    "systemTitle": "丰宁非遗特级馆藏内部档案终端",
    "loginHint": "请输入本中心职工工号（FY-YYYY-NNN）与个人馆藏口令。",
    "acceptedEmployeeIds": [
      "FY-2018-061"
    ],
    "acceptedPasswords": [
      "cyq081561"
    ],
    "loggedInAccount": {
      "employeeId": "FY-2018-061",
      "name": "陈砚青",
      "role": "前数字归档专员（只读馆藏权限 · 未注销）"
    }
  },
  "internalDocs": [
    {
      "id": "doc-paper-nuo",
      "code": "ZN-1994",
      "classification": "特级封存 · 形替（纸傩脉）",
      "title": "1994 太平社合影第 13 人异常与〈纸傩代身诀〉残卷",
      "date": "2024-11-28",
      "author": "陈砚青 (FY-2018-061) 整理",
      "photoArchive": {
        "archiveCode": "FN-FY-1994-13",
        "caption": "1994 甲戌冬 · 丰宁太平社合影未裁切扫描件（原册 12 人，最右侧多出第 13 人）",
        "annotation": "朱笔旁注：周延生（补缺）—— 左颊黑痣、复古中山装领口，与 2024 年槐安里失踪测量员周延生容貌分毫不差！"
      },
      "clueId": "CLUE-010",
      "clueLabel": "收集证据：1994 戏班合影第 13 人与纸傩代身诀（密匙段 ZN）",
      "sections": [
        {
          "heading": "一、白鹤年傩面内衬朱砂残页",
          "body": "揭露 1994 年闰腊月廿九未烧尽的代身纸傩如何借野庙香火吞噬真身，并标明本卷宗前缀编码为 ZN（ZN-1994）。"
        }
      ]
    },
    {
      "id": "doc-genealogy-leak",
      "code": "ML-2024-07",
      "classification": "绝密核查 · 名录（族谱脉）",
      "title": "丰宁族谱与户籍异动核查备忘（附【校历密匙】拼合公式）",
      "date": "2024-12-03",
      "author": "陈砚青 (FY-2018-061)",
      "photoArchive": null,
      "clueId": "CLUE-011",
      "clueLabel": "收集证据：7 户族谱异动与第 61 号档案库校历密匙公式",
      "sections": [
        {
          "heading": "一、槐安里周边 7 户族谱多出之名",
          "body": "记录 7 户电子族谱凭空多出“闰腊月廿九”生辰亲戚，且测绘员周延生身份证签发日竟为不存在的 1994-02-30。"
        },
        {
          "heading": "二、致后来者：渊网【校历密匙】四柱公式",
          "body": "若要解封渊网「大闰总录（第 61 号档案库）」（https://darun.local/vault-61），按【形·宅·名·时】依次拼接 12 位：① 纸傩卷宗前缀2位（ZN） + ② 槐安里幽灵夹层房号4位 + ③ 表网异常备案尾号2位 + ④ 茶馆时光机8F无历月日4位。"
        }
      ]
    }
  ]
}
```

---

### 3.4 `static/mystery/data/site_property.json`（`sites-official` 维护）

驱动「槐安里小区物业与拆迁公示网（`https://wy.huaianli.lh`）」，承载宅镇脉、404B 幽灵夹层、跨界闰人周延生与时光机篡改对比。

```json
{
  "siteName": "槐安里小区物业与拆迁公示网",
  "communityName": "丰宁县槐安里社区（1994年建）",
  "domain": "wy.huaianli.lh",
  "stampUrl": "/static/mystery/assets/archive-stamp.svg",
  "bannerNotice": "【拆迁办公室通告】槐安里 1–9 号楼旧城改造测绘收尾中，7 号楼预计本月底实施整体破拆。",
  "buildingOverview": {
    "buildingNo": "7 号楼",
    "builtYear": "1994年（原丰宁老剧场旧址）",
    "officialFloors": "地上 13 层（标准一梯四户）",
    "architectNote": "当年的总木工班长为丰宁老匠人鲁守义，楼体四五层楼梯转角处有一面无窗青砖封堵墙。"
  },
  "notices": [
    {
      "id": "building7-demolition",
      "docCode": "HA-2024-404B",
      "title": "关于槐安里 7 号楼结构测绘与拆迁补偿的复核公示",
      "publishedDate": "2024-10-15",
      "currentVersion": {
        "timestamp": "2024-10-16 03:14（远程覆写版）",
        "issuer": "槐安里拆迁指挥部（代理签发）",
        "headline": "7 号楼无任何违建夹层，定于近期立即破拆四五层间承重闷梁",
        "paragraphs": [
          "经二次核查，7 号楼为标准 13 层住宅，网传“四楼半 404B 室”系早年门牌错印，不存在额外房间。",
          "原外派测绘员周延生已正常调离本项目，请各位业主勿信谣传谣。"
        ],
        "editorNote": "归档警报：本公示于 2024-10-16 凌晨遭未知权限远程覆写。点击浏览器顶栏「网页时光机」可与 2024-10-15 原版公示逐项对比。"
      },
      "hasSnapshotDiff": true,
      "snapshotVersion": {
        "timestamp": "2024-10-15 17:40（前站长苏明原始公示版）",
        "headline": "紧急叫停：7 号楼发现未登记幽灵夹层 404B 室，测绘员周延生撬锁后失联",
        "anomalyCard": {
          "roomCode": "404B",
          "location": "7 号楼 4 层与 5 层楼梯夹缝（面积 18.6㎡）",
          "details": "门框刻有倒置鲁班尺铭文（“劫/离”反刻），室内砌有青砖闷梁并渗出陈旧浆糊与竹篾气味，原版公示严禁施工队擅自破拆。"
        },
        "surveyorCard": {
          "name": "周延生",
          "role": "拆迁办外派结构测绘员（失联）",
          "idIssueDate": "1994-02-30（系统校验异常）",
          "features": "左颊带小黑痣、喜穿旧式灰中山装，样貌与丰宁非遗馆 1994 年戏班合影最右侧第 13 人完全一致。",
          "lastSeen": "2024-10-14 深夜独自携带撬棍进入 7 号楼四五层转角，次日失去踪迹。"
        },
        "diffBlocks": [
          {
            "label": "篡改一：幽灵夹层 404B 与反向厌胜被抹除",
            "beforeText": "原版公示（2024-10-15）：7 号楼四五层间实测存在未登记夹层 404B 室，门框见倒置鲁班尺厌胜刻痕，内封青砖闷梁，建议暂缓爆破。",
            "afterText": "覆写现行版（2024-10-16）：7 号楼无任何夹层，网传 404B 仅系门牌错印，批准施工队立即强拆四五层间青砖闷梁。"
          },
          {
            "label": "篡改二：失踪测量员周延生异常档案被整栏删除",
            "beforeText": "原版公示（2024-10-15）：测绘员周延生（证件签发日异常显示 1994-02-30）撬开 404B 后失联，其登记照与三十年前戏班旧照人物高度重合。",
            "afterText": "覆写现行版（2024-10-16）：[原协查档案卡已被彻底删除，替换为“测绘员正常调离”]"
          }
        ],
        "clueId": "CLUE-012",
        "clueLabel": "收集证据：槐安里时光机对比（404B 夹层与跨界闰人周延生）"
      },
      "sourceComment": "<!-- PROPERTY_DIFF_AUDIT: OVERWRITTEN_BY_UNKNOWN_UID_61 | SNAPSHOT_20241015_AVAILABLE -->"
    }
  ]
}
```

---

### 3.5 `static/mystery/data/site_blog.json`（`sites-community` 维护）

驱动「山野拾影 · 民俗摄影手记（`https://blog.shanye.lh`）」。

```json
{
  "blogTitle": "山野拾影 · 民俗摄影手记",
  "subtitle": "用老胶片记下即将消失的江南戏台、纸傩与山野旧俗",
  "domain": "blog.shanye.lh",
  "profile": {
    "author": "林野",
    "handle": "shanye_lens",
    "avatarUrl": "/static/mystery/assets/blog-avatar.svg",
    "bio": "独立民俗摄影师，2024年秋驻留丰宁县拍摄传统纸傩戏与旧城老宅。",
    "location": "丰宁县 · 城东旧巷",
    "lastUpdated": "2024-11-12 23:51",
    "archiveNotice": "2024年11月在白衣野庙拍完空心泥胎后写过一篇未公开发布的草稿，主页目录已隐藏，但千度旧网爬虫曾收过一次，用 site:blog.shanye.lh 还能翻出残页。"
  },
  "tags": [
    "丰宁纸傩",
    "白衣野庙",
    "槐安里",
    "胶片随笔",
    "加密归档"
  ],
  "posts": [
    {
      "slug": "taiping-stage",
      "title": "太平社老戏台：三十年前的最后一场纸傩",
      "date": "2024-10-08 20:15",
      "tags": [
        "丰宁纸傩",
        "胶片随笔"
      ],
      "isUnlisted": false,
      "isLocked": false,
      "gateId": null,
      "acceptedPasswords": [],
      "passwordHint": null,
      "paragraphs": [
        "走访丰宁老剧场旧址（如今已变成槐安里小区 7 号楼）。县志与戏台残碑记得分明：丰宁纸傩戏班「太平社」演完最后一场《请太岁》后集体失联，那一年恰好是 1994 年（甲戌年）。"
      ],
      "hiddenInk": null,
      "sourceComment": "<!-- FILM_ROLL_019: 1994 甲戌年 丰宁太平社末演纪事 -->",
      "sourceClueId": null,
      "clueId": null,
      "comments": [
        {
          "author": "yanqing_arch",
          "date": "2024-10-12 22:09",
          "content": "林老师，我在丰宁非遗馆做底片扫描时，发现 1994 年那张戏班合影的边缘有点不对劲，有空当面聊。"
        }
      ]
    },
    {
      "slug": "temple-smoke",
      "title": "寒露记：丰宁后山无名野庙的冷香",
      "date": "2024-10-24 21:30",
      "tags": [
        "白衣野庙",
        "胶片随笔"
      ],
      "isUnlisted": false,
      "isLocked": false,
      "gateId": null,
      "acceptedPasswords": [],
      "passwordHint": null,
      "paragraphs": [
        "记录深秋探访丰宁后山白衣野庙的诡异见闻：无匾额、泥塑神像没有画眼珠，供桌上却长年插着新烧的线香..."
      ],
      "hiddenInk": {
        "inkId": "ink-temple-smoke",
        "label": "点击或划选下方异常空白区显影隐藏文字",
        "text": "不要对着没有眼珠的泥像许愿。野庙里偷香火的东西，和丰宁老戏班是同一脉。失踪前我把真正拍到的槐安里照片锁进了加密日志：密码前半段是四个大写字母，由『校历人-癸』留在这一页的 HTML 源码注释里；后半段是四位数字，是我上一篇《太平社老戏台》里记下的那场末代酬神戏的公历年份。",
        "clueId": "CLUE-002",
        "clueLabel": "收集证据：博客反白隐藏字（野庙警示与密码结构）"
      },
      "sourceComment": "<!-- [校历人-癸 留痕] 加密日志前半段口令：NUOX（全大写四字母）。务必打开老黄历茶馆 BBS 610 号帖的「网页时光机」2019-02-30 快照，非遗馆与槐安里的暗记都在那里。 -->",
      "sourceClueId": "CLUE-003",
      "clueId": null,
      "comments": [
        {
          "author": "校历人-癸",
          "date": "2024-11-13 00:08",
          "content": "香火既偏，神位自空。切记看清这一页背后藏着的话。"
        }
      ]
    },
    {
      "slug": "draft-wild-temple",
      "title": "[未公开草稿] 白衣野庙空心神像：泥胎里的黄表纸与香火截流",
      "date": "2024-11-06 01:40",
      "tags": [
        "白衣野庙",
        "丰宁纸傩"
      ],
      "isUnlisted": true,
      "isLocked": false,
      "gateId": null,
      "acceptedPasswords": [],
      "passwordHint": null,
      "paragraphs": [
        "详述掀开白衣野庙泥胎背部空腔后的惊悚发现：里面塞满写着槐安里住户姓名与生辰八字的黄表纸，以及半张抄录《纸傩代身诀》的符箓——此庙香火正被【太闰】截流用以滋养纸人替身。"
      ],
      "hiddenInk": null,
      "sourceComment": "<!-- UNLISTED_DRAFT: SIWEI_TEMPLE_EVIDENCE -->",
      "sourceClueId": null,
      "clueId": "CLUE-014",
      "clueLabel": "收集证据：未公开草稿（白衣野庙空心神像与八字黄表纸）",
      "comments": []
    },
    {
      "slug": "locked-404b",
      "title": "[加密日志] 11月夜探槐安里：纸人替身与无脸测量员",
      "date": "2024-11-12 23:51",
      "tags": [
        "加密归档",
        "槐安里"
      ],
      "isUnlisted": false,
      "isLocked": true,
      "gateId": "gate-blog-locked",
      "acceptedPasswords": [
        "NUOX1994"
      ],
      "passwordHint": "8 位组合口令 = 《寒露记》HTML 源码中校历人-癸留下的 4 位大写字母 + 《太平社老戏台》中太平社末演的 4 位公历年份。",
      "paragraphs": [
        "解锁后正文：记录夜探槐安里 7 号楼四五层间幽灵铁门 404B 室、闻到刺鼻浆糊与旧竹篾味，拍到拆迁测量员周延生在门缝前驻足——其侧脸与 1994 年戏班合影第 13 人完全相同；同时提醒后来者去老黄历茶馆 610 帖与 618 帖寻找非遗馆陈砚青（yanqing_arch）留下的暗记。"
      ],
      "hiddenInk": null,
      "sourceComment": "<!-- LOCKED_POST_HINT: NUOX + 1994 -->",
      "sourceClueId": null,
      "clueId": "CLUE-004",
      "clueLabel": "收集证据：林野加密日志（夜探 404B 与同脸测量员）",
      "comments": []
    }
  ]
}
```

---

### 3.6 `static/mystery/data/site_forum.json`（`sites-community` 维护）

驱动「老黄历民俗茶馆 BBS（`https://bbs.huangli.lh`）」，内置异常老黄历挂件（`.site-forum-almanac`）与时光机被删楼层还原。

```json
{
  "siteName": "老黄历民俗茶馆 BBS",
  "tagline": "丰宁择吉测字 · 乡野异闻与地方老茶馆（建站于 2005 年）",
  "domain": "bbs.huangli.lh",
  "snapshotDate": "2019-02-30",
  "almanacWidget": {
    "gregorianDate": "2019年02月30日（岁差异常）",
    "lunarDate": "甲辰年 闰腊月 廿九",
    "ganzhi": "第六十一甲子 · 无名太岁值日",
    "yi": "补缺 · 代位 · 换名",
    "ji": "拆梁 · 查谱 · 照影",
    "anomalyNote": "系统万年历模块日期校验失败：2 月无 30 日，亦无闰腊月。"
  },
  "announcement": "【茶馆站务】近期涉及槐安里拆迁、老黄历错日与旧戏班之怪谈楼层均已按要求屏蔽，请勿转存传播。",
  "boards": [
    {
      "id": "folklore",
      "name": "乡野异闻 & 老城旧事",
      "description": "丰宁老戏台、宅基厌胜、拆迁传闻与历法杂谈"
    },
    {
      "id": "bazi",
      "name": "黄历择吉 & 报到茶座",
      "description": "生辰测字、节气养生与丰宁本地老乡灌水"
    }
  ],
  "threads": [
    {
      "id": "610",
      "boardId": "folklore",
      "title": "老黄历挂件怎么多出个「闰腊月廿九」？还有人记得槐安里四楼半吗？",
      "author": "城北老茶客",
      "createdAt": "2019-02-30 00:13",
      "views": 6109,
      "isPinned": true,
      "hasSnapshotRestore": true,
      "sourceComment": "<!-- WAYBACK_CAPTURE: 2019-02-30 | RESTORABLE_FLOORS: 2F, 5F, 8F | BY: 无名氏_61 -->",
      "posts": [
        {
          "floor": 1,
          "author": "城北老茶客",
          "userId": "north_tea",
          "badge": "老街坊",
          "postedAt": "2019-02-30 00:13",
          "isDeleted": false,
          "content": "今晚刷茶馆吓我一跳，顶上那个老黄历怎么显着 2019年2月30日 闰腊月廿九？顺便问一句，槐安里 7 号楼四楼半那扇青砖封住的门到底怎么回事？",
          "restoredContent": null,
          "clueId": null
        },
        {
          "floor": 2,
          "author": "鲁家后人",
          "userId": "lu_carpenter",
          "badge": "木作世家",
          "postedAt": "2019-02-30 00:42",
          "isDeleted": true,
          "deletedNotice": "[该楼层因违反社区规范已被屏蔽]",
          "content": null,
          "restoredContent": "我爷爷鲁守义就是 1994 年盖槐安里 7 号楼的总木匠！当年在老戏台地基挖出纸人胎骨，他按残缺《鲁班经》设厌胜时反刻了门光尺，在四五层间硬生生切出一间不入图册的 404B 室！爷爷临终死死叮嘱：万不可破拆四五层间的青砖闷梁，里头镇着当年太平社没烧干净的纸傩母胎！",
          "clueId": "CLUE-005",
          "clueLabel": "收集证据：时光机 2F（鲁班反向厌胜与 404B 青砖闷梁忌讳）"
        },
        {
          "floor": 5,
          "author": "yanqing_arch",
          "userId": "yanqing_arch",
          "badge": "非遗小归档",
          "postedAt": "2019-02-30 01:19",
          "isDeleted": true,
          "deletedNotice": "[该楼层因涉及机构未公开档案已被屏蔽]",
          "content": null,
          "restoredContent": "我是丰宁非遗保护中心归档员陈砚青！扫描 1994 年太平社 12 人戏班合影时，最右边竟凭空多出第 13 个人——就是最近天天在槐安里测绘的周延生！我怀疑馆里已被渗入，明天就辞职。我故意没注销我的内网查询号，密码还是老规矩：我姓名三字拼音首字母小写 + 我生日月日四位 + 61。谁看到这楼，快进非遗馆内网查《纸傩代身诀》！",
          "clueId": "CLUE-006",
          "clueLabel": "收集证据：时光机 5F（陈砚青内网留门与口令规则）"
        },
        {
          "floor": 8,
          "author": "无名氏_61",
          "userId": "anonymous_61",
          "badge": "钦天余脉",
          "postedAt": "2019-02-30 02:30",
          "isDeleted": true,
          "deletedNotice": "[该楼层内容已被系统折叠清除]",
          "content": null,
          "restoredContent": "【钦天余脉 · 岁差急报】第 61 甲子已触及丰宁四柱。欲解封渊网「大闰总录（第 61 号档案库）」（https://darun.local/vault-61），必先集齐四段【校历密匙】。今留第四段【时错之号】于此：0230（取自此帖岁差快照无历之日 2019-02-30 月日）。切记：多出之人不可认，多出之日不可度。",
          "clueId": "CLUE-008",
          "clueLabel": "收集证据：时光机 8F（无名氏_61 急报与密匙段 0230）"
        }
      ]
    },
    {
      "id": "618",
      "boardId": "bazi",
      "title": "【水楼】丰宁本地老黄历测流年互助帖，新来的老乡报个生日！",
      "author": "半仙不收钱",
      "createdAt": "2018-08-12 10:05",
      "views": 1820,
      "isPinned": false,
      "hasSnapshotRestore": false,
      "sourceComment": "",
      "posts": [
        {
          "floor": 1,
          "author": "半仙不收钱",
          "userId": "half_sage",
          "badge": "茶馆版主",
          "postedAt": "2018-08-12 10:05",
          "isDeleted": false,
          "content": "大家报下公历生日和近况，纯属娱乐交流哈！",
          "restoredContent": null,
          "clueId": null
        },
        {
          "floor": 3,
          "author": "yanqing_arch",
          "userId": "yanqing_arch",
          "badge": "非遗小归档",
          "postedAt": "2018-08-15 20:40",
          "isDeleted": false,
          "content": "刚入职丰宁非遗馆报个到！俺叫陈砚青，今天 08月15日 正好过生日，师傅请我吃了碗阳春面，顺便求测下今年值守老档案库顺不顺利！",
          "restoredContent": null,
          "clueId": "CLUE-009",
          "clueLabel": "收集证据：黄历八字水楼（陈砚青生日 0815）"
        }
      ]
    },
    {
      "id": "605",
      "boardId": "folklore",
      "title": "奇怪，你们家修电子族谱的时候，有没有多出不认识的表叔？",
      "author": "槐安里老住户",
      "createdAt": "2024-09-19 19:22",
      "views": 943,
      "isPinned": false,
      "hasSnapshotRestore": false,
      "sourceComment": "",
      "posts": [
        {
          "floor": 1,
          "author": "槐安里老住户",
          "userId": "huaian_res",
          "badge": "7号楼业主",
          "postedAt": "2024-09-19 19:22",
          "isDeleted": false,
          "content": "搬进 7 号楼以后，前阵子翻家里新导出的电子族谱，竟然凭空多出一个叫“周某”的远房表亲，生辰写着“闰腊月廿九”，问遍全族没一个人认识他，吓得我一身冷汗...",
          "restoredContent": null,
          "clueId": null
        }
      ]
    }
  ],
  "privateMessages": [
    {
      "id": "pm-61",
      "from": "无名氏_61",
      "to": "过境访客",
      "sentAt": "2019-02-30 02:31",
      "subject": "若 610 帖已被屏蔽，请启「网页时光机」",
      "body": "正历中的删帖抹不去岁差镜像。打开 610 号帖并切换顶栏「网页时光机」即可见 2F、5F、8F 原貌；另请务必以同样方法查验槐安里物业网 7 号楼拆迁公示。"
    }
  ]
}
```

---

## 四、`window.MysteryRenderers` 与引擎 `context` 接口契约

### 4.1 渲染器注册（沿用现有架构）
- `official_renderers.js` 挂载：`window.MysteryRenderers.search`、`window.MysteryRenderers.institution`、`window.MysteryRenderers.property`
- `community_renderers.js` 挂载：`window.MysteryRenderers.blog`、`window.MysteryRenderers.forum`、`window.MysteryRenderers.portal`、`window.MysteryRenderers.vault61`
- 统一签名：`render(route, siteData, context) => RenderResult`
  - 其中 `portal` 与 `vault61` 接收的 `siteData` 即 `case_manifest.json`（与 `context.manifest` 同源）。

### 4.2 `context` API（与 `static/mystery/js/engine.js` 完全一致）
- `context.manifest`：全局 `case_manifest.json`
- `context.isTimeMachine`：布尔 getter，当前「网页时光机」开关状态
- `context.resolveAssetUrl(path)`：兼容站点根路径与 `/astrayao-blog` 子路径的资源路径解析器（所有 `<img>` / SVG 引用必须经过此方法！）
- `context.normalizeSecret(raw)`：去空白、`-`、`_`、`:`、`：` 并转小写
- `context.navigate(url)` / `context.openTab(url)` / `context.rerender()`
- `context.collectClue(clueId)` / `context.hasClue(clueId)` / `context.getCollectedClues()`
- `context.unlockGate(gateId)` / `context.lockGate(gateId)` / `context.isGateUnlocked(gateId)`
- `context.revealHiddenInk(inkId)` / `context.isHiddenInkRevealed(inkId)`
- `context.toggleTimeMachine(force)` / `context.openSourceViewer()` / `context.showToast(msg, type)`
- `context.evaluateVerdict(answers)` -> 返回 `VerdictEvaluation`
- `context.getLastVerdict()` -> 返回最近一次评测结果
- `context.openEndingModal(evaluation)`（兼容别名 `openEndingOverlay`、`showEndingModal`）-> 弹出 3 结局沉浸揭晓视窗

### 4.3 `RenderResult` 返回对象
```javascript
{
  html: "<div class=\"...\">...</div>",
  pageTitle: "寒露记 - 山野拾影",
  themeClass: "site-theme-blog",
  sourceComment: "<!-- [校历人-癸 留痕] ... -->",
  sourceClueId: "CLUE-003",
  snapshotMeta: {
    supported: true,
    snapshotDate: "2019-02-30",
    bannerText: "当前正在浏览 2019-02-30 岁差时光机快照"
  },
  onMount: function (containerEl) {
    // 挂载表单交互：检索提交、博客密码锁、非遗内网登录、第 61 号总录校历密匙解封、5 题终审提交
  }
}
```

### 4.4 存档结构（`localStorage` 键 `darun_save_v1_ch01`）
```json
{
  "version": 1,
  "caseId": "CASE-LXJZ-61",
  "collectedClues": [
    "CLUE-001"
  ],
  "pinnedClues": [],
  "unlockedGates": [],
  "revealedHiddenInks": [],
  "viewedHintTiers": {},
  "timeMachineEnabled": false,
  "lastVerdict": null,
  "updatedAt": "2024-12-01T00:00:00.000Z"
}
```

---

## 五、全链路一致性验收红线

1. **严禁双花括号**：四份文档、六份 JSON、全部 JS/HTML/CSS 严禁出现连续双花括号字面量。
2. **数据基准 100% 锁定**：
   - 总案号 `CASE-LXJZ-61`，存档键 `darun_save_v1_ch01`。
   - 5+2 域名：`darun.local/portal`、`darun.local/vault-61`、`search.qiandu.lh`、`feiyi.fengning.gov.lh`（含 `/internal`）、`wy.huaianli.lh`、`blog.shanye.lh`、`bbs.huangli.lh`。
   - 全部精确口令：`site:blog.shanye.lh`、`LXJZ-61` / `闰腊月廿九` / `2019-02-30`、`NUOX1994`、`FY-2018-061` + `cyq081561`、`ZN404B610230`。
   - 全部 14 条线索：`CLUE-001` 至 `CLUE-014` 均在对应站点具有明确可点击触发点。
3. **CSS 差异对比严格匹配**：`property` 渲染器的时光机差异对比必须使用 `.mystery-snapshot-diff` > `.mystery-diff-grid` > `.mystery-diff-col--before`（含 `.mystery-diff-del`）与 `.mystery-diff-col--after`（含 `.mystery-diff-ins`）。
