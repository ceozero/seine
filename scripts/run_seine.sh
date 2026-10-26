#!/usr/bin/env bash
# 在 Debian/Ubuntu 上下载并启动最新版 Seine（CPU + 1 GiB HugeTLB）。
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/root/seine}"
TMUX_SESSION="${TMUX_SESSION:-seine}"
POOL_URL="${POOL_URL:-stratum+tcp://bntpool.com:3333}"
WALLET_ADDRESS="${WALLET_ADDRESS:-N1uHhvgf3bg8X8hS9qrS6iqbSCemrYVTMNCMPyfrGAwoGcJcKg15YXPgfj4a98R3pjcSzTyJnrVj5PTDBVoyRqzM47Bc1}"
RELEASE_BASE_URL="https://github.com/zpalmtree/seine/releases/latest/download"
HUGEPAGE_PATH="/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages"
GRUB_DEFAULT_FILE="/etc/default/grub"

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

grub_has_1g_hugepages() {
    local grub_line

    [[ -f "$GRUB_DEFAULT_FILE" ]] || return 1
    grub_line="$(grep -E '^[[:space:]]*GRUB_CMDLINE_LINUX_DEFAULT=' "$GRUB_DEFAULT_FILE" || true)"
    [[ "$grub_line" == *"hugepagesz=1G"* ]] && [[ "$grub_line" =~ (^|[[:space:]])hugepages=[0-9]+([[:space:]]|\"|$) ]]
}

configure_grub_1g_hugepages() {
    [[ -f "$GRUB_DEFAULT_FILE" ]] || die "未找到 ${GRUB_DEFAULT_FILE}，无法写入 GRUB 启动参数。"

    cp -p "$GRUB_DEFAULT_FILE" "${GRUB_DEFAULT_FILE}.seine.bak"
    if grep -qE '^[[:space:]]*GRUB_CMDLINE_LINUX_DEFAULT=' "$GRUB_DEFAULT_FILE"; then
        sed -i -E "/^[[:space:]]*GRUB_CMDLINE_LINUX_DEFAULT=/ s/\"[[:space:]]*$/ hugepagesz=1G hugepages=${requested_pages}\"/" "$GRUB_DEFAULT_FILE"
    else
        printf '\nGRUB_CMDLINE_LINUX_DEFAULT="quiet hugepagesz=1G hugepages=%s"\n' "$requested_pages" >>"$GRUB_DEFAULT_FILE"
    fi

    if command -v update-grub >/dev/null 2>&1; then
        update-grub
    elif command -v grub-mkconfig >/dev/null 2>&1 && [[ -d /boot/grub ]]; then
        grub-mkconfig -o /boot/grub/grub.cfg
    else
        die "已修改 ${GRUB_DEFAULT_FILE}，但未找到可用的 update-grub 或 grub-mkconfig。请手动生成 GRUB 配置后再重启。"
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
        release_arch="x86_64"
        ;;
    aarch64|arm64)
        release_arch="aarch64"
        ;;
    *)
        die "不支持的 CPU 架构: $(uname -m)（仅支持 amd64 和 arm64）。"
        ;;
esac

echo "安装 tmux..."
apt-get install -y tmux

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "发现已有 tmux 会话 ${TMUX_SESSION}；先关闭旧会话后重建。"
    tmux kill-session -t "$TMUX_SESSION" || die "无法关闭已有 tmux 会话 ${TMUX_SESSION}。"
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
actual_pages="$(<"$HUGEPAGE_PATH")"
[[ "$actual_pages" =~ ^[0-9]+$ ]] || die "读取到无效的 nr_hugepages 值: $actual_pages"

echo "当前有 ${actual_pages} 个 1 GiB HugeTLB 页；整理内存碎片并释放页缓存..."
printf '3\n' >/proc/sys/vm/drop_caches || die "无法释放页缓存。"
printf '1\n' >/proc/sys/vm/compact_memory || die "无法整理内存碎片。"
echo "检测到 ${cpu_count} 个 CPU、$((mem_total_kib / 1024 / 1024)) GiB 内存；设置 ${requested_pages} 个 1 GiB HugeTLB 页。"
printf '%s\n' "$requested_pages" >"$HUGEPAGE_PATH" || die "无法设置 1 GiB HugeTLB 页。"
actual_pages="$(<"$HUGEPAGE_PATH")"
[[ "$actual_pages" =~ ^[0-9]+$ ]] || die "读取到无效的 nr_hugepages 值: $actual_pages"

if ((actual_pages != requested_pages)); then
    echo "警告: 仅实际分配到 ${actual_pages}/${requested_pages} 个 1 GiB HugeTLB 页。"
    if grub_has_1g_hugepages; then
        echo "已检测到 GRUB 的 1 GiB HugeTLB 配置；将使用当前实际页数。"
    else
        configure_grub_1g_hugepages
        echo "已写入 GRUB 参数 hugepagesz=1G hugepages=${requested_pages}，并备份原文件为 ${GRUB_DEFAULT_FILE}.seine.bak。"
        echo "请重启服务器后重新运行此脚本，使所需的 1 GiB HugeTLB 页数在启动时预留。"
        exit 0
    fi
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
echo "tmux new-session -d -s "$TMUX_SESSION" "$tmux_command""
echo "已启动 Seine：架构=${release_arch}，threads=${threads}，1 GiB HugeTLB=${actual_pages} 页。"
echo "将在 5 秒后进入 tmux 会话；按 Ctrl+C 可取消自动进入。手动查看运行窗口：tmux attach -t ${TMUX_SESSION}"
sleep 5
exec tmux attach -t "$TMUX_SESSION"
