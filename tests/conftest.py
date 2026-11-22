"""Temporary site fixtures for tests that exercise article publication."""

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
    return root


@pytest.fixture(scope="session")
def populated_site_root(empty_site_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("populated-site")
    shutil.copytree(empty_site_root, root, dirs_exist_ok=True)
    posts = root / "content" / "posts"
    posts.mkdir()
    (posts / "build-fixture.md").write_text(
        "---\ntitle: 测试样例（设计）\nslug: build-fixture\ndate: 2025-02-02\n"
        "category: 测试\ntags: [设计, Python]\nsummary: 浏览器测试样例\n"
        "cover: /static/images/cover-01.svg\nfeatured: true\n---\n\n"
        "## 安装\n\n```python\nprint('test')\n```\n\n## 使用\n\n"
        + "测试段落。\n\n" * 12,
        encoding="utf-8",
    )
    (posts / "deployment-fixture.md").write_text(
        "---\ntitle: 测试样例（服务器）\nslug: deployment-fixture\ndate: 2025-02-01\n"
        "category: 测试\ntags: [部署]\nsummary: 子路径测试样例\n"
        "cover: /static/images/cover-02.svg\n---\n\n"
        "## 路径\n\n```sh\ncd /var/www/test-site/dist\n```\n",
        encoding="utf-8",
    )
    project_file = root / "content" / "projects.json"
    project = {
        "name": "测试项目",
        "status": "测试",
        "year": "2025",
        "summary": "项目列表测试样例",
        "stack": ["Python"],
        "url": "/articles/build-fixture/",
    }
    project_file.write_text(json.dumps([project], ensure_ascii=False), encoding="utf-8")
    return root
