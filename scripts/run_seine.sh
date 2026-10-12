#!/usr/bin/env bash
# 在 Debian/Ubuntu 上下载并启动最新版 Seine（CPU + 1 GiB HugeTLB）。
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/root/seine}"
TMUX_SESSION="${TMUX_SESSION:-seine}"
POOL_URL="${POOL_URL:-stratum+tcp://bntpool.com:3333}"
WALLET_ADDRESS="${WALLET_ADDRESS:-N1uHhvgf3bg8X8hS9qrS6iqbSCemrYVTMNCMPyfrGAwoGcJcKg15YXPgfj4a98R3pjcSzTyJnrVj5PTDBVoyRqzM47Bc1}"
RELEASE_BASE_URL="https://github.com/ceozero/seine/releases/latest/download"
HUGEPAGE_PATH="/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages"

die() {
    echo "错误: $*" >&2
    exit 1
}

download() {
    local url="$1"
    local output="$2"

    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --retry 3 --output "$output" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget --https-only --tries=3 --output-document="$output" "$url"
    else
        die "未找到 curl 或 wget，请先安装其中一个下载工具。"
    fi
}

if ((EUID != 0)); then
    die "此脚本需要 root 权限，请使用 sudo bash $0 运行。"
fi

if ! command -v apt-get >/dev/null 2>&1; then
    die "仅支持带 apt-get 的 Debian/Ubuntu 系统。"
fi

case "$(uname -m)" in
    x86_64|amd64)
        release_arch="amd64"
        ;;
    aarch64|arm64)
        release_arch="arm64"
        ;;
    *)
        die "不支持的 CPU 架构: $(uname -m)（仅支持 amd64 和 arm64）。"
        ;;
esac

echo "安装 tmux..."
apt-get install -y tmux

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    die "tmux 会话 ${TMUX_SESSION} 已存在；请先执行 tmux attach -t ${TMUX_SESSION} 查看，或手动停止后再运行脚本。"
fi

cpu_count="$(nproc)"
mem_total_kib="$(awk '/^MemTotal:/ { print $2; exit }' /proc/meminfo)"
((mem_total_kib > 0)) || die "无法读取系统内存。"

# 每个线程需要 1 个 CPU 核心和 2 GiB 内存（即两个 1 GiB HugeTLB 页）。
memory_limited_threads=$((mem_total_kib / 2 / 1024 / 1024))
requested_threads="$cpu_count"
if ((memory_limited_threads < requested_threads)); then
    requested_threads="$memory_limited_threads"
fi
((requested_threads >= 1)) || die "可用内存不足 2 GiB，无法以 large-1g 模式启动。"

[[ -e "$HUGEPAGE_PATH" ]] || die "内核未提供 1 GiB HugeTLB 接口: $HUGEPAGE_PATH"

requested_pages=$((requested_threads * 2))
echo "检测到 ${cpu_count} 个 CPU、$((mem_total_kib / 1024 / 1024)) GiB 内存；申请 ${requested_pages} 个 1 GiB HugeTLB 页。"
printf '%s\n' "$requested_pages" >"$HUGEPAGE_PATH" || die "无法设置 1 GiB HugeTLB 页。"

actual_pages="$(<"$HUGEPAGE_PATH")"
[[ "$actual_pages" =~ ^[0-9]+$ ]] || die "读取到无效的 nr_hugepages 值: $actual_pages"

if ((actual_pages != requested_pages)); then
    echo "警告: 仅实际分配到 ${actual_pages}/${requested_pages} 个 1 GiB HugeTLB 页。"
fi

# HugeTLB 不足时以实际页数决定线程数；同时保留 CPU/内存计算出的上限。
hugepage_limited_threads=$((actual_pages / 2))
threads="$requested_threads"
if ((hugepage_limited_threads < threads)); then
    threads="$hugepage_limited_threads"
fi
((threads >= 1)) || die "实际 1 GiB HugeTLB 页少于 2 个，无法启动。请释放内存后重试。"

archive="seine-linux-${release_arch}.tar.gz"
checksum_file="SHA256SUMS.txt"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

echo "下载 Seine 最新 ${release_arch} 发行版..."
download "${RELEASE_BASE_URL}/${archive}" "${work_dir}/${archive}"
download "${RELEASE_BASE_URL}/${checksum_file}" "${work_dir}/${checksum_file}"

(
    cd "$work_dir"
    grep -F "  ${archive}" "$checksum_file" | sha256sum -c -
) || die "发行包 SHA-256 校验失败。"

mkdir -p "$INSTALL_DIR"
tar -xzf "${work_dir}/${archive}" -C "$INSTALL_DIR"
chmod +x "${INSTALL_DIR}/seine"

worker_name="$(hostname)"
printf -v tmux_command 'exec %q --pool-url %q --pool-worker %q --address %q --cpu-page-mode large-1g --threads %q' \
    "${INSTALL_DIR}/seine" "$POOL_URL" "$worker_name" "$WALLET_ADDRESS" "$threads"
tmux new-session -d -s "$TMUX_SESSION" "$tmux_command"

echo "已启动 Seine：架构=${release_arch}，threads=${threads}，1 GiB HugeTLB=${actual_pages} 页。"
echo "查看运行窗口：tmux attach -t ${TMUX_SESSION}"
echo "注意：HugeTLB 设置和 tmux 会话在重启后不会自动恢复；重启后请再次运行此脚本。"
