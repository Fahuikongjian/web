# 阿里云华东 2（上海）ECS 部署与运维保姆级指南（ASTRA YAO · 星环手记）

本指南针对**阿里云华东 2（上海）ECS + 阿里云域名（如 `astrayao.com`，若你的实际域名后缀为 `.cn` / `.me` 等请自行替换）+ 云解析 DNS + 中国大陆 ICP 备案**场景编写，帮助你将 **ASTRA YAO · 星环手记** 静态站点从本地零依赖构建并稳定上线到生产环境。

---

## 一、上线全景流程图

```text
[1] 域名购买与实名认证 (阿里云万网)
         │
         ▼
[2] 提交 ICP 备案申请 (关联上海 ECS 的备案服务号)
         │  ※ 提示：等待管局审核期间，域名不可解析并对外提供公开网站访问
         ▼
[3] 云解析 DNS 添加 A 记录 (@ 与 www -> ECS 公网 IP)
         │
         ▼
[4] 阿里云 ECS 安全组放行 80 / 443 端口
         │
         ▼
[5] ECS 安装 Caddy 2（推荐）或 Nginx，并配置本项目的 Caddyfile / nginx.conf
         │
         ▼
[6] 本地运行 python scripts/check.py && bash deploy/deploy.sh 一键发布上线
         │
         ▼
[7] 填写正式 ICP 备案号到 content/site.json，重新发布并完成公安联网备案
```

---

## 二、阿里云账号与合规准备（域名、实名与 ICP 备案）

### 1. 域名实名认证
1. 登录**阿里云控制台 -> 域名控制台**。
2. 确认你的域名已完成**域名持有者实名认证**（个人使用身份证即可，通常 1~3 个工作日内生效；未实名域名无法解析与备案）。

### 2. 申请 ICP 备案（中国大陆服务器必须）
因为你的 ECS 位于**华东 2（上海）**，根据工信部及上海市通信管理局规定，**必须完成 ICP 备案后，域名才能通过 80/443 端口对外访问**（未备案域名绑定上海 ECS 会被阿里云拦截页阻断）。

1. **检查 ECS 备案资格**：包年包月且购买时长 >= 3 个月的中国大陆 ECS 实例可免费申请备案服务号（按量付费或短期实例需先续费满足条件）。
2. **提交备案**：在阿里云顶部导航进入 **备案控制台** -> 开始备案：
   - 填写主办单位信息（个人性质）及上海/当前居住地证件。
   - 网站服务内容选择「个人博客 / 个人技术记录」（不要写经营性、论坛、新闻、电商类词汇，避免驳回）。
   - 验证阿里云系统自动生成的「备案服务号」。
3. **管局审核期间（约 5~15 个工作日）重要注意事项**：
   - **不要将未备案的域名指向 ECS 并公开对外访问**（部分管局核查时若发现域名已指向可打开的站点或网页标题不符，会导致退回）。
   - **此时如何提前在 ECS 上调试？** 请看下文「备案前临时调试方案」——仅通过 **ECS 公网 IP** 或 **SSH 本地端口转发** 调试，待备案号正式下发后再开启域名正式解析与 HTTPS。
4. **备案通过后更新正式域名与页脚备案号**：
   - 打开 `content/site.json`，核对并将 `site_url` 更新为你的真实域名与实际后缀（当前示例默认为 `"https://astrayao.com"`，如实际为 `.cn` 请改为 `"https://astrayao.cn"`，确保 `rss.xml`、`sitemap.xml`、`robots.txt` 与 canonical 链接正确），并将 `icp_number` 从 `"沪ICP备XXXXXXXX号-1（备案中）"` 修改为真实备案号（如 `"沪ICP备2026012345号-1"`），保留 `icp_url` 为 `"https://beian.miit.gov.cn/"`。
   - 重新运行构建与部署脚本即可全站生效。
5. **公安联网备案（可选但建议按规定办理）**：ICP 备案通过并上线后 30 日内，登录「全国互联网安全管理服务平台」提交公安联网备案登记。

---

## 三、阿里云 ECS 安全组与云解析 DNS 配置

### 1. 配置 ECS 安全组（放行 80 / 443）
1. 登录 **ECS 控制台（华东 2 上海）** -> 选择你的实例 -> **安全组** -> **配置规则** -> **入方向**。
2. 确认并添加以下入方向规则：

| 授权策略 | 协议类型 | 目的端口范围 | 授权对象 | 说明 |
| --- | --- | --- | --- | --- |
| 允许 | SSH (22) | `22/22` | 建议填写你的本地公网 IP（或临时 `0.0.0.0/0`） | 远程管理与 `deploy.sh` 上传 |
| 允许 | HTTP (80) | `80/80` | `0.0.0.0/0` | 网页访问、HTTPS 跳转与 ACME 证书验证 |
| 允许 | HTTPS (443) | `443/443` | `0.0.0.0/0` | 生产环境 HTTPS 加密访问 |

> [!TIP]
> 若你的 ECS 操作系统开启了系统自带防火墙（如 Ubuntu 的 `ufw` 或 Alibaba Cloud Linux 的 `firewalld`），也需同步放行 80/443：
> - Ubuntu/Debian：`sudo ufw allow 80/tcp && sudo ufw allow 443/tcp`
> - CentOS/Alibaba Cloud Linux：`sudo firewall-cmd --permanent --add-service=http --add-service=https && sudo firewall-cmd --reload`

### 2. 配置阿里云云解析 DNS
1. 登录 **云解析 DNS 控制台** -> 找到你的域名 -> **解析设置** -> **添加记录**。
2. 添加两条 `A` 记录（假设你的上海 ECS 公网 IP 为 `47.100.xx.xx`）：
   - **主域名**：记录类型 `A` ｜ 主机记录 `@` ｜ 记录值 `47.100.xx.xx` ｜ TTL `10分钟`
   - **www 子域名**：记录类型 `A` ｜ 主机记录 `www` ｜ 记录值 `47.100.xx.xx` ｜ TTL `10分钟`
3. 验证解析是否生效（在本地终端执行，若域名后缀不同请替换 `astrayao.com`）：
   ```bash
   nslookup astrayao.com 223.5.5.5
   ```
   若返回的 Address 已是你的 ECS 公网 IP，说明 DNS 解析已就绪。

---

## 四、ECS 服务器环境初始化

SSH 登录你的上海 ECS 后，先准备站点目录 `/var/www/blog`：

```bash
sudo mkdir -p /var/www/blog/dist /var/www/blog/releases
# 如使用普通用户（如 deploy）发布，可将其设为目录属主：
# sudo chown -R $USER:$USER /var/www/blog
```

接下来从 **方案 A（Caddy 2，推荐）** 和 **方案 B（Nginx + Certbot）** 中任选其一。

---

## 五、Web 服务器配置（二选一）

### 方案 A：Caddy 2（推荐个人博客与小内存服务器）

**优势**：配置只有几十行，**全自动申请和续期 Let's Encrypt HTTPS 证书**，内置 HTTP/2、HTTP/3、Zstd/Gzip 压缩，几乎零维护成本。

1. **安装 Caddy 2**：
   - **Ubuntu / Debian**：
     ```bash
     sudo apt update && sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
     curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
     curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.tar.gz' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
     sudo apt update && sudo apt install -y caddy
     ```
   - **Alibaba Cloud Linux 3 / RHEL / CentOS 8+**：
     ```bash
     sudo dnf install -y 'dnf-command(copr)'
     sudo dnf copr enable -y @caddy/caddy
     sudo dnf install -y caddy
     ```
2. **部署配置文件**：
   - 将仓库中的 `deploy/Caddyfile` 上传到 ECS 的 `/etc/caddy/Caddyfile`。
   - 核对并将文件中的 `astrayao.com` 替换为你的真实域名及实际后缀，`admin@astrayao.com` 替换为你的邮箱。
   - 创建日志目录并赋权：
     ```bash
     sudo mkdir -p /var/log/caddy
     sudo chown -R caddy:caddy /var/log/caddy
     ```
3. **校验并启动**：
   ```bash
   sudo caddy validate --config /etc/caddy/Caddyfile
   sudo systemctl enable --now caddy
   sudo systemctl reload caddy
   ```

> [!NOTE]
> **备案前（仅 IP 临时调试）如何使用 Caddy？**
> 备案未下发时，无法为域名申请证书。打开 `/etc/caddy/Caddyfile`，临时注释掉 `www.astrayao.com` 和 `astrayao.com` 两个块，取消文件底部 `http://:80 { import blog_site }` 的注释，执行 `sudo systemctl reload caddy`，即可通过 `http://<ECS公网IP>/` 临时预览。备案通过后改回域名块即可自动签发 HTTPS 证书。

---

### 方案 B：Nginx + Certbot（传统经典方案）

**优势**：生态通用，方便与现有多个后端服务共机部署。

1. **安装 Nginx**：
   - Ubuntu / Debian：`sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx`
   - Alibaba Cloud Linux 3：`sudo dnf install -y nginx certbot python3-certbot-nginx`
2. **准备配置文件**：
   - 复制 `deploy/nginx.conf` 到 `/etc/nginx/conf.d/astrayao.conf`（Ubuntu 若启用了默认站点，记得移除 `/etc/nginx/sites-enabled/default` 避免端口冲突）。
   - 核对并将文件中所有 `astrayao.com` 替换为你的真实域名及实际后缀。
3. **先申请 SSL 证书，再启用完整 HTTPS 配置**：
   - 首次部署时，Nginx 若尚未有 `/etc/letsencrypt/live/astrayao.com/fullchain.pem`，直接 `nginx -t` 会报证书文件不存在。
   - 推荐步骤：
     1. 先注释 `deploy/nginx.conf` 中的两个 `443` server 块，并在 `80` 端口块中临时启用文件内注释的 HTTP 调试配置。
     2. 运行 `sudo nginx -t && sudo systemctl enable --now nginx`。
     3. 运行 Certbot 获取免费证书（自动写入续期定时任务，请替换为你的真实域名）：
        ```bash
        sudo certbot certonly --webroot -w /var/www/blog/dist -d astrayao.com -d www.astrayao.com
        ```
     4. 恢复 `deploy/nginx.conf` 完整的 HTTPS 配置（去掉调试注释，恢复 301 跳转与 443 server 块）。
     5. 测试配置并重载：
        ```bash
        sudo nginx -t && sudo systemctl reload nginx
        ```
4. **验证证书自动续期**：
   ```bash
   sudo certbot renew --dry-run
   ```

---

## 六、自动化发布与日常运维

### 1. 日常写文章与本地预览
1. 在 `content/posts/` 下新建 Markdown 文件（如 `06-my-new-essay.md`），遵循 Frontmatter 格式。
2. 本地全链路构建与质量校验（检查产物完整性、JSON/XML 合法性、零模板残留、零死链）：
   ```bash
   python scripts/check.py
   ```
3. 本地启动预览服务器验证页面效果：
   ```bash
   python scripts/serve.py --port 8000
   ```

### 2. 使用 `deploy/deploy.sh` 一键发布到上海 ECS
在 Windows 上可通过 **Git Bash** 或 **WSL** 执行 `deploy/deploy.sh`；在 macOS / Linux 上直接执行即可。

1. 首次创建本地配置 `deploy/.deploy.env`（该文件已被 `.gitignore` 忽略）：
   ```bash
   ECS_HOST="47.100.xx.xx"
   ECS_USER="root"
   ECS_PORT="22"
   SSH_KEY="$HOME/.ssh/id_ed25519"
   REMOTE_BASE="/var/www/blog"
   DEPLOY_MODE="tar"
   RELOAD_SERVICE="none"
   ```
2. 先演练本地校验流程（不连服务器）：
   ```bash
   bash deploy/deploy.sh --dry-run
   ```
3. 正式一键构建、校验、打包上传并原子切换线上目录：
   ```bash
   bash deploy/deploy.sh
   ```
   > `tar` 模式会在 ECS 上保留最近 5 个版本的 `/var/www/blog/releases/<时间戳>`，并通过 `mv -Tf` 原子切换 `/var/www/blog/dist` 软链接，实现**零停机发布**。

### 3. 紧急回滚方法
如果发现某次发布内容有误，只需登录 ECS 将 `/var/www/blog/dist` 软链接指回上一个时间戳目录即可秒级回滚：

```bash
ls -lt /var/www/blog/releases
ln -sfn /var/www/blog/releases/20261121-190000 /var/www/blog/dist.next
mv -Tf /var/www/blog/dist.next /var/www/blog/dist
```

---

## 七、备案前后的安全访问与常见排错清单

### 1. 备案前：如何安全预览生产服务器效果（不触发未备案拦截）
如果你希望在 ICP 备案完成前，就验证 ECS 上 Nginx/Caddy 的真实表现，可以使用 **SSH 本地端口转发**：
```bash
# 在本地电脑执行：将本机 8080 端口安全转发到 ECS 内部的 80 端口
ssh -L 8080:127.0.0.1:80 root@47.100.xx.xx
```
随后在本地浏览器访问 `http://127.0.0.1:8080/`，既无需公网暴露 80 端口，也能完整测试服务器静态资源与路由。

### 2. 常见故障排查

| 现象 | 常见原因 | 排查与解决办法 |
| --- | --- | --- |
| 打开域名提示阿里云「该网站未备案/阻断」 | 域名尚未完成 ICP 备案，或备案刚通过缓存未刷新 | 确认备案控制台状态为「备案成功」，等待约 2~4 小时阿里云阻断库同步 |
| 浏览器无法连接 / 连接超时 | 阿里云 ECS 安全组未放行 80 / 443，或系统防火墙拦截 | 检查 ECS 安全组入方向规则，同时在 ECS 上执行 `ss -tulpn \| grep -E '80\|443'` 确认服务正在监听 |
| Caddy 启动失败 / HTTPS 证书签发失败 | DNS A 记录未生效，或 80/443 端口被旧 Nginx 占用 | 用 `nslookup` 确认域名已解析到当前 ECS；检查是否同时启动了 Nginx 与 Caddy 导致端口冲突 |
| 访问 `/articles/` 返回 403 Forbidden | Nginx/Caddy 进程用户对 `/var/www/blog/dist` 无读/执行权限 | 执行 `chmod -R a+rX /var/www/blog`；确保上级目录至少有 `x` 权限 |
| 发布新文章后页面还是旧内容 | 浏览器强缓存或 CDN 缓存未更新 | 检查 Nginx/Caddy 中 HTML 的 `Cache-Control: no-cache, must-revalidate` 是否生效；本地按 `Ctrl+F5` 强制刷新测试 |
