# GitHub Pages 零成本自动托管与阿里云域名绑定指南（ASTRA YAO · 星环手记）

本指南适用于将 **ASTRA YAO · 星环手记（astrayao）** 纯静态站点首发托管至 **GitHub Pages**，通过仓库内置的 GitHub Actions 工作流（`.github/workflows/deploy-pages.yml`）实现**推送即自动构建、质量校验与上线**，并支持绑定你在阿里云注册的 `astrayao` 域名与免费 HTTPS 证书。

> [!TIP]
> **为什么首发推荐 GitHub Pages？**
> - 托管在 GitHub Pages 海外节点期间，**无需等待中国大陆 ICP 备案即可直接对外访问与自动签发 HTTPS 证书**。
> - 无论部署在项目子路径（`https://<用户名>.github.io/<仓库名>/`）还是根域名/自定义域名（`https://astrayao.com/`），构建流水线都会自动适配全部链接与站内搜索索引，零 404 死链。
> - 将来若想迁回阿里云华东 2（上海）ECS 以获得国内极速访问，只需按 [deploy/DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) 切换 DNS 与备案号即可，内容源文件零改动。

---

## 一、环境准备与代码推送到 GitHub

> [!NOTE]
> 当前本地 Windows 环境尚未安装 `git` 命令行工具，下面提供「命令行（推荐）」与「图形界面」两种方式将 `d:\网页运营` 上传到 GitHub。

### 方式 A：使用 `winget` 安装 Git 并命令行推送（推荐）

1. 在 Windows **PowerShell** 中安装 Git：
   ```powershell
   winget install --id Git.Git -e --source winget
   ```
   安装完成后**重新打开一个新的 PowerShell 窗口**，确认生效：
   ```powershell
   git --version
   ```
2. 首次配置 Git 身份信息：
   ```powershell
   git config --global user.name "Astra Yao"
   git config --global user.email "你的GitHub绑定邮箱@example.com"
   ```
3. 在 GitHub 网页端新建一个公开仓库（Public）：
   - 若希望默认地址为 `https://<用户名>.github.io/`（根路径），仓库名请命名为 `<你的GitHub用户名>.github.io`；
   - 若使用普通仓库名（如 `astrayao-blog`），未绑定自定义域名时将自动部署到子路径 `https://<你的GitHub用户名>.github.io/astrayao-blog/`。
   - **不要**在 GitHub 新建仓库页面勾选 README 或 `.gitignore`（本地仓库已经自带）。
4. 在本地项目目录 `d:\网页运营` 初始化并推送至 `main` 分支：
   ```powershell
   cd d:\网页运营
   git init -b main
   git add .
   git status   # 确认 dist/ 已被 .gitignore 自动忽略，仅提交源码与静态资产
   git commit -m "feat: initial ASTRA YAO static blog for GitHub Pages"
   git remote add origin https://github.com/<你的GitHub用户名>/<仓库名>.git
   git push -u origin main
   ```

### 方式 B：使用 GitHub Desktop 或网页上传
- **GitHub Desktop**（免记命令）：下载安装 GitHub Desktop -> 登录账号 -> `File -> Add local repository` 选择 `d:\网页运营` -> 初始化仓库并 `Publish repository`（注意取消勾选 Keep private，GitHub 免费版 Pages 需公开仓库，除非是 GitHub Pro）。
- **网页端手动上传**：在新建的 GitHub 空仓库点击 `uploading an existing file`，将除 `dist/` 和 `__pycache__/` 以外的所有目录（含隐藏文件 `.github/`、`.gitignore`）拖入提交到 `main` 分支。

---

## 二、开启 GitHub Pages（GitHub Actions 模式）

1. 打开你的 GitHub 仓库页面 -> 点击顶部 **Settings** -> 左侧菜单找到 **Pages**。
2. 在 **Build and deployment** 下方的 **Source** 下拉框中，选择 **GitHub Actions**（**不要**选 Deploy from a branch）。
3. 随后进入仓库顶部的 **Actions** 标签页：
   - 由于仓库中已包含 `.github/workflows/deploy-pages.yml`，每次向 `main` 分支 `push` 代码都会自动触发构建，你也可以点击 **Deploy Static Site to GitHub Pages -> Run workflow** 手动触发一次。
4. 工作流将自动执行以下流水线：
   - 安装 Python 3.13 与 `requirements.txt`（`Pygments`）
   - 调用 `actions/configure-pages@v5` 自动探测当前仓库的 `base_path`（子路径或根路径）与 `origin`
   - 运行 `python scripts/check.py` 完成构建、`dist/.nojekyll` 生成、JSON/XML 校验与全站链接门禁检查
   - 上传 `dist/` 并自动发布上线
5. 等待 `build` 与 `deploy` 两个任务全部变绿后，在 **Settings -> Pages** 顶部即可看到可点击的线上访问地址。

---

## 三、绑定阿里云 `astrayao` 自定义域名与 HTTPS

如果你希望通过自己的域名（例如 `astrayao.com` 或实际注册后缀 `astrayao.cn` / `astrayao.me` 等）访问托管在 GitHub Pages 上的博客，请按以下步骤操作：

### 1. 在阿里云「云解析 DNS」添加解析记录
登录 **阿里云控制台 -> 云解析 DNS -> 解析设置 -> 添加记录**（以下示例均以 `astrayao.com` 为例，请按实际后缀对应替换）：

| 记录类型 | 主机记录 | 解析请求来源 | 记录值 | TTL | 说明 |
| --- | --- | --- | --- | --- | --- |
| `A` | `@` | 默认 | `185.199.108.153` | `10分钟` | GitHub Pages 官方 IP #1 |
| `A` | `@` | 默认 | `185.199.109.153` | `10分钟` | GitHub Pages 官方 IP #2 |
| `A` | `@` | 默认 | `185.199.110.153` | `10分钟` | GitHub Pages 官方 IP #3 |
| `A` | `@` | 默认 | `185.199.111.153` | `10分钟` | GitHub Pages 官方 IP #4 |
| `CNAME` | `www` | 默认 | `<你的GitHub用户名>.github.io` | `10分钟` | 将 `www` 指向 GitHub Pages |

> [!IMPORTANT]
> 请确保 `@` 主机记录下**没有冲突的旧 `A` 记录或 `CNAME` 记录**；仅保留上述 4 条指向 GitHub Pages 的 `A` 记录即可。

验证解析是否生效（在本地 PowerShell 执行）：
```powershell
nslookup astrayao.com 223.5.5.5
nslookup www.astrayao.com 223.5.5.5
```

### 2. 在 GitHub Pages 绑定 Custom Domain 并开启 Enforce HTTPS
1. 确认 DNS 解析已返回上述 IP 后，回到 GitHub 仓库 **Settings -> Pages -> Custom domain**。
2. 输入你的主域名（如 `astrayao.com`），点击 **Save**。
3. （可选但推荐）为防止日后部署覆盖自定义域名记录，可任选以下方式之一固化 `dist/CNAME`：
   - **方式 1（GitHub 仓库变量）**：进入 **Settings -> Secrets and variables -> Actions -> Variables -> New repository variable**，新增变量名 `PAGES_CNAME`，值为 `astrayao.com`（工作流会自动传参 `--cname`）。
   - **方式 2（配置文件）**：编辑 `content/site.json`，将 `"custom_domain": ""` 设为 `"astrayao.com"`，并同步确认 `"site_url"` 为 `"https://astrayao.com"` 后提交推送。
4. 等待 GitHub 自动完成域名校验与 Let's Encrypt SSL 证书签发（通常 1~5 分钟）后，勾选 **Enforce HTTPS**。

---

## 四、本地子路径联调与后续迁移阿里云 ECS 说明

### 1. 本地模拟 GitHub Pages 子路径构建与校验
如果你准备将站点先发布到 `https://<用户名>.github.io/astrayao-blog/`，可以在本地用以下命令提前验证子路径构建全绿：

```powershell
# 测试子路径构建与门禁校验
python scripts/check.py --base-path /astrayao-blog --site-url https://example.github.io/astrayao-blog

# 测试完成后恢复默认根目录 dist/ 以便本地直接预览
python scripts/check.py
python scripts/serve.py --port 8000
```

### 2. 将来迁回阿里云上海 ECS
当你的域名完成中国大陆 **ICP 备案** 并准备迁移至阿里云华东 2（上海）ECS 时，无需修改任何文章或模板代码：
1. 在 `content/site.json` 中重新填入真实 `icp_number`（如 `"沪ICP备2026012345号-1"`），将 `custom_domain` 清空（或保留），确认 `site_url` 为你的正式域名。
2. 在阿里云云解析 DNS 中将 `@` 和 `www` 的记录改回上海 ECS 的公网 IP。
3. 按照 [阿里云上海 ECS 部署指南](DEPLOY_GUIDE.md) 配置 Caddy 2 或 Nginx，并运行 `bash deploy/deploy.sh` 一键上线即可。
