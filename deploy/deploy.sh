#!/usr/bin/env bash
# ==============================================================================
# 一键构建、全量校验并发布静态站点到阿里云 ECS 的脚本
#
# 功能说明：
#   1. 自动执行 `python scripts/check.py`（重建 dist/ 并完成全链路质量门禁校验）
#   2. 支持两种上传方式：
#      - tar  （默认，无需远程安装 rsync：本地 tar.gz -> scp 上传 -> 远程原子解压切换并保留回滚备份）
#      - rsync（增量同步，适合频繁更新且本地与 ECS 均已安装 rsync 的环境）
#   3. 可选自动重载远程 Web 服务（nginx / caddy / none）
#
# 使用前配置（任选一种方式）：
#   方式 A：在 deploy/.deploy.env 中配置变量（已加入 .gitignore，不会泄露服务器 IP）
#   方式 B：通过环境变量直接传参：
#     ECS_HOST="47.100.xx.xx" ECS_USER="deploy" bash deploy/deploy.sh
#
# 常用参数：
#   --dry-run   仅本地执行校验与打包演练，不连接远程 ECS
#   -h, --help  查看完整参数说明
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 若存在本地私密部署配置 deploy/.deploy.env，则自动加载
ENV_FILE="${SCRIPT_DIR}/.deploy.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

# ------------------------------------------------------------------------------
# 默认配置（均可通过环境变量或 deploy/.deploy.env 覆盖）
# ------------------------------------------------------------------------------
ECS_HOST="${ECS_HOST:-}"
ECS_USER="${ECS_USER:-root}"
ECS_PORT="${ECS_PORT:-22}"
SSH_KEY="${SSH_KEY:-}"
REMOTE_BASE="${REMOTE_BASE:-/var/www/blog}"
DEPLOY_MODE="${DEPLOY_MODE:-tar}"         # 可选: tar | rsync
RELOAD_SERVICE="${RELOAD_SERVICE:-none}"  # 可选: caddy | nginx | none
KEEP_RELEASES="${KEEP_RELEASES:-5}"       # tar 模式下保留最近几份历史发布用于快速回滚
DRY_RUN="false"

usage() {
  cat <<'EOF'
用法:
  ECS_HOST=<ECS公网IP或域名> [选项环境变量] bash deploy/deploy.sh [--dry-run]

核心环境变量:
  ECS_HOST        (必填，--dry-run 除外) 阿里云 ECS 公网 IP 或 SSH 域名
  ECS_USER        SSH 登录用户名，默认: root（生产建议用 deploy 普通用户）
  ECS_PORT        SSH 端口，默认: 22
  SSH_KEY         SSH 私钥路径，如 ~/.ssh/id_ed25519（不填则使用默认 SSH 配置）
  REMOTE_BASE     ECS 上的站点根目录父路径，默认: /var/www/blog
                  最终网站文件将部署至 ${REMOTE_BASE}/dist
  DEPLOY_MODE     传输方式: tar（默认，tar+scp 原子切换）或 rsync（增量同步）
  RELOAD_SERVICE  上传后是否重载服务: none（默认，静态文件无需重启）| caddy | nginx
  KEEP_RELEASES   tar 模式下保留历史版本数，默认: 5

本地配置持久化建议:
  复制以下内容保存到 deploy/.deploy.env（已被 .gitignore 忽略）：
    ECS_HOST="47.100.xx.xx"
    ECS_USER="root"
    ECS_PORT="22"
    SSH_KEY="$HOME/.ssh/aliyun_ecs"
    REMOTE_BASE="/var/www/blog"
    DEPLOY_MODE="tar"
    RELOAD_SERVICE="none"

示例:
  bash deploy/deploy.sh --dry-run
  ECS_HOST="47.100.xx.xx" bash deploy/deploy.sh
  ECS_HOST="47.100.xx.xx" DEPLOY_MODE="rsync" bash deploy/deploy.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[错误] 未知参数: $1" >&2
      usage
      exit 1
      ;;
  esac
done

# ------------------------------------------------------------------------------
# 1. 检测 Python 解释器并运行全链路质量门禁 scripts/check.py
# ------------------------------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[错误] 未找到 python3 或 python，请先安装 Python 3。" >&2
  exit 1
fi

echo "==> [1/4] 运行构建与质量门禁: ${PYTHON_BIN} scripts/check.py"
"${PYTHON_BIN}" scripts/check.py

if [[ ! -d "${PROJECT_ROOT}/dist" ]]; then
  echo "[错误] 未找到构建输出目录 dist/，部署中止。" >&2
  exit 1
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "==> [Dry-Run] 本地构建与质量检查已全部通过，跳过远程上传步骤。"
  exit 0
fi

if [[ -z "${ECS_HOST}" ]]; then
  echo "[错误] 必须设置 ECS_HOST（例如 ECS_HOST=47.100.xx.xx），或在 deploy/.deploy.env 中配置。" >&2
  echo "       也可先运行 'bash deploy/deploy.sh --dry-run' 进行本地演练。" >&2
  exit 1
fi

# 组装 SSH / SCP / Rsync 参数
SSH_OPTS=(-p "${ECS_PORT}" -o StrictHostKeyChecking=accept-new)
SCP_OPTS=(-P "${ECS_PORT}" -o StrictHostKeyChecking=accept-new)
if [[ -n "${SSH_KEY}" ]]; then
  SSH_OPTS+=(-i "${SSH_KEY}")
  SCP_OPTS+=(-i "${SSH_KEY}")
fi

REMOTE_TARGET="${ECS_USER}@${ECS_HOST}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

# ------------------------------------------------------------------------------
# 2. 上传产物至阿里云 ECS
# ------------------------------------------------------------------------------
if [[ "${DEPLOY_MODE}" == "rsync" ]]; then
  if ! command -v rsync >/dev/null 2>&1; then
    echo "[错误] DEPLOY_MODE=rsync 但本机未安装 rsync，请改用 DEPLOY_MODE=tar。" >&2
    exit 1
  fi

  RSYNC_RSH="ssh -p ${ECS_PORT} -o StrictHostKeyChecking=accept-new"
  if [[ -n "${SSH_KEY}" ]]; then
    RSYNC_RSH="${RSYNC_RSH} -i ${SSH_KEY}"
  fi

  echo "==> [2/4] 使用 rsync 增量同步 dist/ 到 ${REMOTE_TARGET}:${REMOTE_BASE}/dist/"
  ssh "${SSH_OPTS[@]}" "${REMOTE_TARGET}" "mkdir -p '${REMOTE_BASE}/dist'"
  rsync -avz --delete -e "${RSYNC_RSH}" "${PROJECT_ROOT}/dist/" "${REMOTE_TARGET}:${REMOTE_BASE}/dist/"

elif [[ "${DEPLOY_MODE}" == "tar" ]]; then
  ARCHIVE_NAME="blog-dist-${TIMESTAMP}.tar.gz"
  ARCHIVE_PATH="${PROJECT_ROOT}/${ARCHIVE_NAME}"
  cleanup_archive() {
    rm -f "${ARCHIVE_PATH}"
  }
  trap cleanup_archive EXIT

  echo "==> [2/4] 打包 dist/ 为 ${ARCHIVE_NAME}"
  tar -czf "${ARCHIVE_PATH}" -C "${PROJECT_ROOT}/dist" .

  echo "==> [3/4] 上传至 ${REMOTE_TARGET} 并原子切换版本 (${REMOTE_BASE}/dist)"
  scp "${SCP_OPTS[@]}" "${ARCHIVE_PATH}" "${REMOTE_TARGET}:/tmp/${ARCHIVE_NAME}"

  ssh "${SSH_OPTS[@]}" "${REMOTE_TARGET}" bash -s -- "${REMOTE_BASE}" "${ARCHIVE_NAME}" "${TIMESTAMP}" "${KEEP_RELEASES}" <<'REMOTE_EOF'
set -euo pipefail
REMOTE_BASE="$1"
ARCHIVE_NAME="$2"
TIMESTAMP="$3"
KEEP_RELEASES="$4"

RELEASES_DIR="${REMOTE_BASE}/releases"
NEW_RELEASE="${RELEASES_DIR}/${TIMESTAMP}"
DIST_LINK="${REMOTE_BASE}/dist"

mkdir -p "${RELEASES_DIR}" "${NEW_RELEASE}"
tar -xzf "/tmp/${ARCHIVE_NAME}" -C "${NEW_RELEASE}"
rm -f "/tmp/${ARCHIVE_NAME}"

# 若历史存在普通目录形式的 dist（非软链），先备份为 dist.legacy
if [[ -d "${DIST_LINK}" && ! -L "${DIST_LINK}" ]]; then
  mv "${DIST_LINK}" "${REMOTE_BASE}/dist.legacy.${TIMESTAMP}"
fi

# 原子更新软链接：先创建临时软链再 mv -Tf 替换，避免访问瞬间出现 404
ln -sfn "${NEW_RELEASE}" "${REMOTE_BASE}/dist.next"
mv -Tf "${REMOTE_BASE}/dist.next" "${DIST_LINK}"

# 确保 Web 服务可读权限（兼容 nginx/caddy 用户读取）
chmod -R a+rX "${NEW_RELEASE}"

# 清理过旧的发布版本，保留最近 KEEP_RELEASES 个便于随时回滚
cd "${RELEASES_DIR}"
old_releases="$( (ls -1dt -- */ 2>/dev/null || true) | tail -n +$((KEEP_RELEASES + 1)) )"
if [[ -n "${old_releases}" ]]; then
  echo "${old_releases}" | xargs -r rm -rf --
fi
echo "当前线上软链指向: $(readlink -f "${DIST_LINK}")"
REMOTE_EOF
else
  echo "[错误] 不支持的 DEPLOY_MODE=${DEPLOY_MODE}（仅支持 tar 或 rsync）" >&2
  exit 1
fi

# ------------------------------------------------------------------------------
# 4. 按需重载 Web 服务（纯静态资源切换软链即可生效；若修改了配置可设为 caddy/nginx）
# ------------------------------------------------------------------------------
echo "==> [4/4] 检查服务重载选项: RELOAD_SERVICE=${RELOAD_SERVICE}"
case "${RELOAD_SERVICE}" in
  nginx)
    ssh "${SSH_OPTS[@]}" "${REMOTE_TARGET}" "sudo nginx -t && sudo systemctl reload nginx"
    ;;
  caddy)
    ssh "${SSH_OPTS[@]}" "${REMOTE_TARGET}" "sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy"
    ;;
  none)
    echo "跳过服务重载（静态文件已实时生效）。"
    ;;
  *)
    echo "[警告] 未知 RELOAD_SERVICE=${RELOAD_SERVICE}，未执行服务重载。" >&2
    ;;
esac

echo "✅ 部署完成！站点目录已更新至 ${REMOTE_TARGET}:${REMOTE_BASE}/dist"
