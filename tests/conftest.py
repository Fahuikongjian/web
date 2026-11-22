"""Temporary site fixtures for tests that exercise article, project, and gallery publication."""

import json
from pathlib import Path
import shutil

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def empty_site_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("empty-site")
    shutil.copytree(PROJECT_ROOT / "content", root / "content", ignore=shutil.ignore_patterns("posts"))
    for directory in ("templates", "static"):
        shutil.copytree(PROJECT_ROOT / directory, root / directory)

    (root / "content" / "projects.json").write_text("[]\n", encoding="utf-8")
    (root / "content" / "gallery.json").write_text("[]\n", encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def populated_site_root(empty_site_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("populated-site")
    shutil.copytree(empty_site_root, root, dirs_exist_ok=True)
    posts = root / "content" / "posts"
    posts.mkdir()
    (posts / "build-fixture.md").write_text(
        "---\ntitle: 测试样例（设计）\nslug: build-fixture\ndate: 2025-02-02\n"
        "category: 代码\ntags: [设计, Python]\nsummary: 浏览器测试样例\n"
        "cover: /static/images/cover-01.svg\nfeatured: true\n---\n\n"
        "## 安装\n\n```python\nprint('test')\n```\n\n## 使用\n\n"
        + "测试段落。\n\n" * 12,
        encoding="utf-8",
    )
    (posts / "deployment-fixture.md").write_text(
        "---\ntitle: 测试样例（服务器）\nslug: deployment-fixture\ndate: 2025-02-01\n"
        "category: 工程\ntags: [部署]\nsummary: 子路径测试样例\n"
        "cover: /static/images/cover-02.svg\n---\n\n"
        "## 路径\n\n```sh\ncd /var/www/test-site/dist\n```\n",
        encoding="utf-8",
    )
    project_file = root / "content" / "projects.json"
    project = {
        "name": "测试项目",
        "category": "应用",
        "status": "测试",
        "year": "2025",
        "summary": "项目列表测试样例",
        "stack": ["Python"],
        "url": "/articles/build-fixture/",
    }
    project_file.write_text(json.dumps([project], ensure_ascii=False), encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def categorized_site_root(empty_site_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("categorized-site")
    shutil.copytree(empty_site_root, root, dirs_exist_ok=True)
    posts = root / "content" / "posts"
    posts.mkdir()
    (posts / "01-python-static-pipeline.md").write_text(
        "---\ntitle: 零依赖静态构建管线与 AST 渲染\nslug: python-static-pipeline\ndate: 2026-11-20\n"
        "category: 代码\ntags: [Python, 架构, 设计]\n"
        "summary: 基于 Python 3.13 标准库与 Pygments 构建单遍模板替换、标题锚点提取与静态输出管线。\n"
        "cover: /static/images/cover-01.svg\nfeatured: true\n---\n\n"
        "## 核心构建管线\n\n"
        "围绕纯文本 Markdown 与 JSON 构建无运行时依赖的静态内容系统，兼顾极简维护与确定性输出。\n\n"
        "```python\n"
        "def resolve_category_tabs(categories: list[dict[str, object]]) -> list[str]:\n"
        "    return ['all', *[str(item['name']) for item in categories]]\n"
        "```\n\n"
        "### 语法高亮与目录锚点\n\n"
        "在构建期一次性完成代码块着色与多级标题锚点提取，避免客户端二次解析开销。\n",
        encoding="utf-8",
    )
    (posts / "02-starloop-visual-synthesis.md").write_text(
        "---\ntitle: 星环光影合成与黑胶纹理生成手记\nslug: starloop-visual-synthesis\ndate: 2026-11-18\n"
        "category: 图像生成\ntags: [设计, 渲染, 色彩]\n"
        "summary: 探索暗夜丝绒黑曜石与绯红香槟金舞台光晕的矢量栅格混合管线与色彩标定。\n"
        "cover: /static/images/cover-02.svg\n---\n\n"
        "## 光晕与采样\n\n"
        "通过克制的径向聚光与高对比度暗部过渡，保持画面在暗夜与象牙双主题下的干净层次。\n",
        encoding="utf-8",
    )
    (posts / "03-code-highlighting-tokens.md").write_text(
        "---\ntitle: 双主题语法高亮令牌与排版栅格实现\nslug: code-highlighting-tokens\ndate: 2026-11-15\n"
        "category: 代码\ntags: [Python, CSS, 设计]\n"
        "summary: 将 Pygments 词法标记映射至暗夜丝绒与象牙典藏双套 CSS 自定义属性。\n"
        "cover: /static/images/cover-03.svg\n---\n\n"
        "## 词法着色映射\n\n"
        "以语义令牌统一控制关键字、字符串与注释对比度，并锁定表格与行内代码的折行边界。\n",
        encoding="utf-8",
    )
    (posts / "04-github-pages-edge-deploy.md").write_text(
        "---\ntitle: 静态站点子路径重写与自动化部署门禁\nslug: github-pages-edge-deploy\ndate: 2026-11-10\n"
        "category: 工程\ntags: [部署, 架构, Nginx]\n"
        "summary: 兼容根域名与项目子路径的 HTML 属性重写、死链扫描与零停机静态发布流程。\n"
        "cover: /static/images/cover-04.svg\n---\n\n"
        "## 门禁与链接校验\n\n"
        "在发布前自动扫描全站 HTML 占位符、静态图像资源与内部根相对链接，保障零死链上线。\n",
        encoding="utf-8",
    )

    projects = [
        {
            "name": "Starloop Press 静态出版引擎",
            "category": "应用",
            "status": "已开源",
            "year": "2026",
            "summary": "基于 Python 3.13 标准库与 Pygments 构建的零运行时依赖静态内容管线与双层筛选引擎。",
            "stack": ["Python 3.13", "Pygments", "HTML5"],
            "tags": ["Python", "静态站点", "架构"],
            "url": "/articles/python-static-pipeline/",
        },
        {
            "name": "Starloop Frequency 视觉令牌系统",
            "category": "视觉",
            "status": "进行中",
            "year": "2026",
            "summary": "面向暗夜黑曜石与象牙典藏双主题的色彩、排版网格与 60fps 滑动指示条设计规范。",
            "stack": ["CSS Tokens", "SVG", "设计"],
            "url": "/articles/code-highlighting-tokens/",
        },
        {
            "name": "GitHub Pages 零死链部署门禁",
            "category": "工具",
            "status": "已开源",
            "year": "2026",
            "summary": "支持根域名与项目子路径自动重写、静态资产完整性核验与 XML/JSON 校验的发布套件。",
            "stack": ["Python", "CI/CD"],
            "tags": ["部署", "自动化", "Python"],
            "url": "/articles/github-pages-edge-deploy/",
        },
        {
            "name": "Lyra 声学频谱着色器实验",
            "category": "实验",
            "status": "实验中",
            "year": "2025",
            "summary": "将黑胶唱针律动与天琴座星轨参数映射为轻量 SVG 几何矢量的生成式视觉实验。",
            "stack": ["SVG", "着色器"],
            "url": "/articles/starloop-visual-synthesis/",
        },
    ]
    (root / "content" / "projects.json").write_text(
        json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    gallery_items = [
        {
            "id": "astra-starloop-diva",
            "title": "星环舞台 · 曜石绯金咏叹",
            "category": "角色",
            "image": "/static/images/astra-portrait.jpg",
            "prompt": (
                "solo songstress on starloop velvet stage, obsidian gown with crimson and "
                "champagne gold embroidery, vintage microphone, floating golden musical staff "
                "and four-point stars, cinematic rim lighting, ultra detailed"
            ),
            "negative_prompt": (
                "lowres, blurry, overexposed, neon cyan, purple cyberpunk gradient, "
                "extra fingers, watermark"
            ),
            "model": "Flux.1 Dev",
            "params": {"steps": 28, "cfg": 3.5, "sampler": "Euler", "aspect": "1:1"},
            "tags": ["曜石绯金", "角色设定", "星环舞台"],
            "date": "2026-11-21",
        },
        {
            "id": "starloop-tower-nocturne",
            "title": "天琴座夜幕 · 星环大厦穹顶",
            "category": "场景",
            "image": "/static/images/starloop-cover.jpg",
            "prompt": (
                "grand concert hall beneath starloop dome, golden orbital rings in dark velvet "
                "sky, warm tungsten spotlight on vinyl stage, art deco brass geometry, "
                "atmospheric depth"
            ),
            "negative_prompt": "daylight, flat lighting, noisy texture, deformed architecture",
            "model": "SDXL Lightning",
            "params": "Steps: 24 · CFG: 4.0 · 16:9",
            "tags": ["星环舞台", "建筑空间", "夜幕"],
            "date": "2026-11-19",
        },
        {
            "id": "vinyl-groove-monolith",
            "title": "33⅓ RPM · 黑胶声纹几何母版",
            "category": "视觉",
            "image": "/static/images/cover-01.svg",
            "prompt": (
                "minimalist editorial cover art, concentric vinyl record grooves in champagne "
                "gold hairline on matte obsidian paper, crimson seal accent, swiss typographic grid"
            ),
            "model": "Vector Synth v2",
            "params": "Seed: 4096 · SVG Grid",
            "tags": ["黑胶美学", "几何版画", "曜石绯金"],
            "date": "2026-11-16",
        },
        {
            "id": "lyra-prism-caustics",
            "title": "天琴棱镜 · 焦散星芒实验",
            "category": "光影",
            "image": "/static/images/cover-02.svg",
            "prompt": (
                "abstract optical caustics through crystal prism, warm amber and crimson light "
                "dispersion on dark velvet surface, subtle film grain, macro photography"
            ),
            "negative_prompt": "oversaturated, harsh clipping",
            "model": "Flux.1 Dev",
            "tags": ["光学焦散", "几何版画"],
            "date": "2026-11-12",
        },
    ]
    (root / "content" / "gallery.json").write_text(
        json.dumps(gallery_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return root
