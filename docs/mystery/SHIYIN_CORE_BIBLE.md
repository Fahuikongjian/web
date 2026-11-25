# 《十音簿》系列核心设定与勘校圣经（Series 03 Core Bible）

## 1. 系列元信息与统一规范（Series Contract）

| 字段 | 规范值 | 说明 |
| :--- | :--- | :--- |
| `seriesKey` | `"shiyin"` | 与 `darun` / `suojiang` 完全隔离 |
| `archiveBrand` | `"十音簿声律档案"` | 顶栏与 `<title>` 后缀 |
| `snapshotButtonLabels` | `{"enter": "切至原始母带", "exit": "返回数字转录版"}` | 切换「数字转录版」与「原始母带」 |
| `search.domain` | `"search.shiyin.lh"` | 系列独立检索引擎（仅单标签「全部网页」） |
| `storageKey` | `shiyin_save_v1_ch01` .. `shiyin_save_v1_ch05`, `shiyin_save_v1_finale` | 各卷独立存档 |
| `caseId` | `CASE-SY-01` .. `CASE-SY-05`, `CASE-SY-00`（校音间）, `CASE-SY-FINALE` | 卷宗编号 |
| HTML `source` 署名 | `审音人-癸` | 复核备注署名，提示下一步站内检索线索 |
| 异常母带信道 / 编目号 | `SY-10` | 全戏路声学母带总录通道 |
| 失联人物 | `陆闻笙`（省音像技术档案组，工牌号 `YS-10`） | 循青溪戏路五站重测后于省馆封盘室前失去音讯 |
| 结案音签格式 | `本卷工尺音签：XX。` | 分别位于 1–5 幕 `conclusion.receipt` 末句：`GG` / `SH` / `JU` / `ZH` / `YU` |
| 终卷隐藏约束 | `星环手记` / `vault-61` 严禁出现在 `shiyin-act-1..5.json` 与 `shiyin-reading-room.json` | 仅允许在 `shiyin-finale-dossier.json` 快照/回执中出现 |

### 核心民俗母题：「正乐九音，留一禁声」
- 沿「青溪戏路」流传的地方《十番乐社旧约》《梨园封箱规》及古钟楼声律旧制相传：**正乐备九音，第十音名「煞音 / 留声」，唯大丧或重修定磬之际启封一响，平时封而不奏**。
- 1998–2008 年地方广电、非遗作坊与剧团音像室抢救性数字化转录时，人为降噪、删剪并抽掉底噪里的第十音；2008 年冬季全省并网校音之际，五地母带接连渗出被抹去的「第十声」异常残响。

### 权威古典引文库（方志馆 `library` 站点须引原文 + 白话考释）
1. 《礼记·乐记》：「凡音之起，由人心生也。人心之动，物使之然也。」——白话考释：器物与声腔之所以发声应和，必有外物与人为之因。
2. 宋·沈括《梦溪笔谈·乐律》：「凡宫音为主，弦长而声宏；商、角、徵、羽相次应和，隔八相生。」——白话考释：传统五声相承须守固定音高与弦数比例，不可擅易。
3. 清·地方《青溪十番乐社成规》（虚构地方规约）：「九板正奏以安四邻，第十煞声入匣封签，非社祭定磬不得轻动。」——白话考释：地方乐社惯例只奏九音，第十音专门留存封签，不随常规演凑。
4. 清·地方《戏码渡梨园封箱记》（虚构碑抄）：「老腔既煞，藻井藏音；封箱之后，生人不得借腔代口。」——白话考释：封箱后的戏台禁腔旨在止息回响，后人不得借用旧名号重录顶替。
5. 清·《青溪城厢更鼓定宵约》（虚构方志）：「五更落定，打点收板；禁更之后，巷坊毋得复敲暗梆。」——白话考释：五更收板后即止夜巡响器，若暗敲五更外暗点，便算违约。

---

## 2. 真实网页架构与防剧透铁律

- **9 类 `style` 必须混合搭配使用**：每幕至少覆盖 `directory` + `public` + `library` + `community` + `office` (`kind:"review"`)，并配合 `hydro`（声学/播控遥测台）、`maritime`（调度通告站）或常规 `office`（琴坊/剧团官网）。
- **零提示暗示**：正文、`table`、`notes` 中**严禁使用 `⚠` / `⏱` 或红橙预警框**，严禁写出 `【未平账】` 等元数据剧透标签；所有 `sites[0].intro` 必须自然给出「第一步去哪个站、看哪篇档」，所有 `checks` 严格按调查时间/因果顺序排列，且每个 `accept[0]` 必须逐字原文出现在可访问或已解锁的 `records` 中。

---

## 3. 五幕独立档案、校音间与终卷总录矩阵

### 第一幕：`shiyin-act-1.json` — 《第一幕 哑钟楼》（钟潭镇）
- `caseId`: `"CASE-SY-01"`, `storageKey`: `"shiyin_save_v1_ch01"`, `homeUrl`: `"https://index.zhongtan.lh/"`
- 站点组合：
  1. `index.zhongtan.lh` (`directory`, 钟潭广电与古钟旧网目录)
  2. `gongshi.zhongtan.lh` (`public`, 钟潭古钟楼修缮公示栏)
  3. `zhizhi.zhongtan.lh` (`library`, 钟潭地方志与声律碑馆)
  4. `bobao.zhongtan.lh` (`hydro`, 钟潭广播播控遥测站 — **含 `snapshot` 原始母带切换**)
  5. `zhongsheng.zhongtan.lh` (`community`, 钟潭老街坊听音论坛)
  6. `jiaoyin.zhongtan.lh` (`office`, `kind:"review"`, 钟潭跨年报时校音复核处)
- 核心线索流（6 `checks` 线性链 + `accept[0]` 精确值）：
  1. `bell-strike`（跨年报时第十声异常）→ `accept[0]`: `"2008-12-31"`
  2. `resonator-removal`（擅拆地坑共鸣瓮工单追责）→ `accept[0]`: `"ZT-108"`
  3. `gazetteer-pitch`（古钟九音铭文核验）→ `accept[0]`: `"黄钟大吕"`
  4. `tuner-badge`（失联调音员工号追寻）→ `accept[0]`: `"陆闻笙"`
  5. `hidden-tape`（站内隐藏母带批文，`index:"site"`）→ 关键词 `"共鸣瓮"` @ `gongshi.zhongtan.lh`，`accept[0]`: `"九瓮留一"`
  6. `bell-restore`（恢复古制留空定案）→ `accept[0]`: `"重砌九瓮"`
- 结案：`conclusion.receipt` 末句 `本卷工尺音签：GG。`；`snapshot` URL：`https://bobao.zhongtan.lh/newyear-tape`；`source`（含 `审音人-癸`）URL：`https://gongshi.zhongtan.lh/tower-repair`。

### 第二幕：`shiyin-act-2.json` — 《第二幕 断弦坊》（桐荫街）
- `caseId`: `"CASE-SY-02"`, `storageKey`: `"shiyin_save_v1_ch02"`, `homeUrl`: `"https://index.tongyin.lh/"`
- 站点组合：`index.tongyin.lh` (`directory`)、`qinfang.tongyin.lh` (`office` 常规官网，含 `snapshot`)、`yueqi.tongyin.lh` (`library`)、`shengxue.tongyin.lh` (`hydro`)、`yueyou.tongyin.lh` (`community`)、`fuhe.tongyin.lh` (`office` `kind:"review"`)
- 6 `checks` 与 `accept[0]`：
  1. `empty-string`（频谱多出未绷弦共振峰）→ `"第七空弦"`
  2. `wood-swap`（私换琴底阴沉木变更单）→ `"TY-204"`
  3. `scale-rule`（十番丝竹弦制古谱）→ `"隔八相生"`
  4. `upstream-tag`（上游寄件琴码标号）→ `"YS-10"`
  5. `secret-spec`（隐藏作坊质检底表，`index:"site"` @ `qinfang.tongyin.lh`，关键词 `"阴沉木"`）→ `"桐木原材"`
  6. `string-seal`（丝竹复原与空弦封弦）→ `"留空不绷"`
- 结案：`本卷工尺音签：SH。`；`snapshot`：`https://shengxue.tongyin.lh/spectrum-log`；`source`：`https://yueyou.tongyin.lh/night-hum`。

### 第三幕：`shiyin-act-3.json` — 《第三幕 借腔台》（戏码渡）
- `caseId`: `"CASE-SY-03"`, `storageKey`: `"shiyin_save_v1_ch03"`, `homeUrl`: `"https://index.xima.lh/"`
- 站点组合：`index.xima.lh` (`directory`)、`jutuan.xima.lh` (`office` 常规官网)、`liyuan.xima.lh` (`library`)、`wenbao.xima.lh` (`public` 政务公示)、`ximi.xima.lh` (`community`)、`hecha.xima.lh` (`office` `kind:"review"`)
- 6 `checks` 与 `accept[0]`：
  1. `forbidden-aria`（封箱带多出的末段唱腔）→ `"1986-11-18"`
  2. `caisson-seal`（古戏台藻井涂封工程批号）→ `"XM-309"`
  3. `guild-edict`（梨园封箱禁腔碑记）→ `"生人勿代"`
  4. `stage-notebook`（戏台后台寻获的调音簿主）→ `"YS-10"`
  5. `hidden-dub`（隐藏补录混音工单，`index:"site"` @ `jutuan.xima.lh`，关键词 `"补录"`）→ `"二号棚借声"`
  6. `caisson-reopen`（清拆藻井腻子复原声腔）→ `"揭封清井"`
- 结案：`本卷工尺音签：JU。`；`snapshot`：`https://jutuan.xima.lh/tape-1986`；`source`：`https://ximi.xima.lh/backstage-echo`。

### 第四幕：`shiyin-act-4.json` — 《第四幕 漏更鼓》（更鼓巷）
- `caseId`: `"CASE-SY-04"`, `storageKey`: `"shiyin_save_v1_ch04"`, `homeUrl`: `"https://index.gengguxiang.lh/"`
- 站点组合：`index.gengguxiang.lh` (`directory`)、`chengjian.gengguxiang.lh` (`public`)、`minsu.gengguxiang.lh` (`library`)、`zaosheng.gengguxiang.lh` (`hydro`)、`laoju.gengguxiang.lh` (`community`)、`shouli.gengguxiang.lh` (`office` `kind:"review"`)
- 6 `checks` 与 `accept[0]`：
  1. `midnight-beat`（凌晨无巡更人时的异常鼓点）→ `"五更三点"`
  2. `drum-demolish`（违章砌封更楼鼓腔门洞）→ `"GG-412"`
  3. `curfew-rule`（城厢更鼓定宵旧约）→ `"打点收板"`
  4. `courier-case`（巷口更亭留下的调音工具箱）→ `"YS-10"`
  5. `hidden-log`（隐藏夜间噪测原始草稿，`index:"site"` @ `zaosheng.gengguxiang.lh`，关键词 `"暗梆"`）→ `"空楼自鸣"`
  6. `drum-reopen`（重开鼓腔并停用电子代鼓）→ `"停电子更"`
- 结案：`本卷工尺音签：ZH。`；`snapshot`：`https://zaosheng.gengguxiang.lh/night-db`；`source`：`https://laoju.gengguxiang.lh/drum-rumor`。

### 第五幕：`shiyin-act-5.json` — 《第五幕 封盘室》（省音像资料馆）
- `caseId`: `"CASE-SY-05"`, `storageKey`: `"shiyin_save_v1_ch05"`, `homeUrl`: `"https://index.yinxiang.lh/"`
- 站点组合：`index.yinxiang.lh` (`directory`)、`diaodu.yinxiang.lh` (`maritime` 调度通告台)、`jiance.yinxiang.lh` (`hydro`)、`dianji.yinxiang.lh` (`library`)、`jishu.yinxiang.lh` (`community`)、`zhonghe.yinxiang.lh` (`office` `kind:"review"`)
- 6 `checks` 与 `accept[0]`：
  1. `master-leak`（78 转母盘异常并网时刻）→ `"2008-12-31"`
  2. `vault-breach`（私自提调永封母盘批单）→ `"SY-518"`
  3. `shellac-rule`（虫胶母盘定音留空规程）→ `"留一镇煞"`
  4. `vault-note`（封盘室恒温柜前所留手记）→ `"YS-10"`
  5. `hidden-script`（隐藏全省自动并播脚本，`index:"site"` @ `jiance.yinxiang.lh`，关键词 `"并网"`）→ `"SY-10-CAST"`
  6. `disc-reseal`（切断并网并重贴封签）→ `"断网封盘"`
- 结案：`本卷工尺音签：YU。`；`snapshot`：`https://jiance.yinxiang.lh/channel-feed`；`source`：`https://dianji.yinxiang.lh/shellac-ledger`。

### 隐藏校音间与终卷总录：`shiyin-reading-room.json` & `shiyin-finale-dossier.json`
- **校音间**（`/mystery/shiyin/reading-room/`，`CASE-SY-00`，`storageKey: "shiyin_save_v1_finale"`，`robots: noindex`）：
  - `homeUrl`: `"https://yinqian.shiyin.lh/"` (`style: "directory"`, `kind: "entry"`)
  - 5 个输入框按一至五幕顺序接收 `GG` / `SH` / `JU` / `ZH` / `YU`。
  - 核验通过后动态加载 `/static/mystery/data/shiyin-finale-dossier.json` 并展示入口链接 `十音总录 · 律吕密档` (`https://zonglu.shiyin.lh/`)。
- **终卷总录**（`shiyin-finale-dossier.json`，`CASE-SY-FINALE`）：
  - 站点：`zonglu.shiyin.lh` (`style: "registry"`, 密档总录库)、`muban.shiyin.lh` (`style: "library"`, 原版工尺谱与母带库)、`luowang.shiyin.lh` (`style: "office"`, `kind: "review"`, 终审归律收件处)。
  - 4 `checks`：
    1. `five-tones`（青溪戏路五音脉络总核）→ `"九音留一，煞声入匣"`
    2. `tuner-lineage`（审音旧部与失联技术员核对）→ `"YS-10 陆闻笙"`
    3. `master-drift`（`SY-10` 母带自播漂移溯源，快照揭示「星环手记」）→ `"SY-10"`
    4. `tone-reseal`（全戏路停播归律方案核定）→ `"九音归位"`
  - `conclusion` (`receipt` 含 `【十音总录完】` 及 `星环手记` 呼应)，解锁隐藏尾札 `closing-note`（`https://zonglu.shiyin.lh/closing-note`，`requiresGate: "filed:receipt"`）。
