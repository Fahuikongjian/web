---
title: 零重型依赖的静态站引擎：用 Python 3.13 标准库写透内容构建管线
slug: python-static-architecture
date: 2026-11-11
category: 系统架构
tags: [Python, 静态站点, 架构设计, Pygments]
summary: 在无需 Node 构建链与第三方模板引擎的前提下，如何仅凭 Python 标准库与 Pygments 实现 Frontmatter 解析、目录锚点生成、语法高亮与全站链接门禁。
cover: /static/images/cover-03.svg
featured: false
draft: false
---

构建一个个人技术博客，究竟需要多少依赖？在现代前端生态里，回答往往是令人望而生畏的几百个 `npm` 包、复杂的打包器配置以及半年不升级就会报错的插件矩阵。对于一个核心输入只是几篇 Markdown、核心输出只是几十个静态 HTML 文件的出版系统来说，这种复杂度显然有些过度设计了。

为了确保本站的代码在三年、五年甚至十年后依然能在一台只装有 Python 的机器上秒级重现构建，我们决定彻底做一次减法：**只依赖 Python 3.13 标准库，外加唯一一个专注代码高亮的成熟库 `Pygments`。**

## 构建管线的四层职责划分

好的架构并不在于引入多少抽象模式，而在于模块之间的边界是否清晰、数据流向是否单向且可测试。整套引擎的构建流程可以被清晰地拆解为四个独立模块：

| 模块名称 | 输入数据 | 核心职责 | 产出数据结构或文件 |
| --- | --- | --- | --- |
| `content_loader.py` | `content/*.json` 与 `posts/*.md` | 解析 Frontmatter、过滤草稿、计算阅读时间与上下篇关联 | 标准化的文章列表与站点配置字典 |
| `markdown_engine.py` | Markdown 正文文本 | 渲染标题锚点、围栏代码块（Pygments）、表格、引用与列表 | `(body_html, toc_list)` 二元组 |
| `renderer.py` | `templates/*.html` 与结构化数据 | 单遍安全替换占位符、组装局部模板、写出全站页面并拷贝静态资源 | `dist/` 下的全部 `.html` 与 `static/` |
| `feeds.py` | 已排序的文章元数据列表 | 生成站内检索索引、文章目录 API、RSS 2.0、Sitemap 与 Robots | `api/*.json`、`rss.xml`、`sitemap.xml` |

这种分层带来了一个立竿见影的好处：内容加载与渲染完全解耦。哪怕未来某天需要新增一种输出格式（例如 JSON Feed 或电子书导出），也不必触动 Markdown 解析或模板拼装的核心逻辑。

## 手写解析器的关键边界细节

不使用 `pyyaml` 与 `python-markdown` 并不意味着“简陋”，相反，面对受控的个人博客内容契约，手写解析器反而能把边界条件控制得更加透明和精准。

### Frontmatter 与中文阅读时间估算

文章头部的元数据约定采用简洁的键值对与行内列表（如 `tags: [Python, 架构设计]`），解析器只需在文件首行识别 `---` 起止标记，分别处理布尔值、日期字符串与标签列表即可。在估算阅读时间时，不能简单用 `len(text.split())`——中文没有空格分词，如果按英文空格切分，整篇两千字的长文可能只算出几个词。

正确的做法是分别统计 CJK 汉字字符数与连续的英文/数字词数，再按照中文每分钟约 350 字的舒适阅读速度向上取整，保证最短文章也至少显示 1 分钟。

### 标题锚点唯一性与 Pygments 集成

为了配合文章右侧的粘性目录（TOC）与浏览器内点击跳转，每一级 `h2` 和 `h3` 标题都必须拥有稳定、合法且不重复的 `id` 属性。在中文标题中，直接丢弃非 ASCII 字符会导致纯中文标题生成空锚点；而简单用序号又缺乏语义。一个兼顾可读性与确定性的方案，是在保留中英文字符与数字的同时，结合增量计数器防止同文标题冲突：

```python
import re
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound


def make_heading_id(raw_text: str, seen_ids: dict[str, int]) -> str:
    """为中英文混合标题生成稳定且全篇唯一的锚点 ID。"""
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", raw_text.strip().lower())
    base = re.sub(r"[\s_]+", "-", cleaned).strip("-") or "section"
    count = seen_ids.get(base, 0) + 1
    seen_ids[base] = count
    return base if count == 1 else f"{base}-{count}"


def render_code_block(code: str, lang: str) -> str:
    """使用 Pygments 渲染带语言标识与复制按钮外壳的高亮代码块。"""
    safe_lang = re.sub(r"[^a-zA-Z0-9_+-]", "", lang or "text") or "text"
    try:
        lexer = get_lexer_by_name(safe_lang)
    except ClassNotFound:
        lexer = TextLexer()
    formatter = HtmlFormatter(cssclass="highlight")
    highlighted = highlight(code, lexer, formatter)
    return (
        f'<div class="code-block-wrapper">'
        f'<div class="code-block-header">'
        f'<span class="code-lang">{safe_lang}</span>'
        f'<button type="button" class="code-copy-btn" aria-label="复制代码">复制</button>'
        f"</div>{highlighted}</div>"
    )
```

> 请特别留意代码块内部的 HTML 转义与二次解析防护：先提取并隔离围栏代码块与行内代码，再处理段落中的加粗、斜体与链接语法，最后按占位符回填，能够从根本上避免代码里的 `*` 或 `_` 被误判成斜体标签。

## 为什么坚持全站静态检查门禁

构建成功并不代表站点已经准备好发布。在我们的工作流中，执行 `build.py` 之后紧接着会运行一道全量质量门禁脚本（`scripts/check.py`）：

- 校验所有 `.html` 文件不存在任何漏替换的模板标记；
- 解析全部站内 `href` 与 `src` 链接，确保每一个根相对路径在 `dist/` 产物目录中都有实实在在的目标文件或目录索引对应；
- 用标准库 `json` 与 `xml.etree.ElementTree` 验证 API 与订阅源的语法合法性。

这种“编译期即发现死链与残缺变量”的工程纪律，让单人维护的个人出版物也拥有了接近工业级持续集成的确定性。关于为什么值得选择这种低依赖的技术路线，我在 [慢软件随笔](/articles/notes-on-slow-software/) 中还写了更多长期维护的体会。
