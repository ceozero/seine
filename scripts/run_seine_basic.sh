#!/usr/bin/env bash
# 在 Debian/Ubuntu 上下载并启动最新版 Seine（不使用 HugeTLB）。
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/root/seine}"
TMUX_SESSION="${TMUX_SESSION:-seine}"
POOL_URL="${POOL_URL:-stratum+tcp://bntpool.com:3333}"
WALLET_ADDRESS="${WALLET_ADDRESS:-N1uHhvgf3bg8X8hS9qrS6iqbSCemrYVTMNCMPyfrGAwoGcJcKg15YXPgfj4a98R3pjcSzTyJnrVj5PTDBVoyRqzM47Bc1}"
RELEASE_BASE_URL="https://github.com/ceozero/seine/releases/latest/download"
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

remove_grub_hugepage_settings() {
    [[ -f "$GRUB_DEFAULT_FILE" ]] || return 0
    if ! grep -Eq '^[[:space:]]*GRUB_CMDLINE_LINUX(_DEFAULT)?=.*(hugepages|hugepagesz|default_hugepagesz)=' "$GRUB_DEFAULT_FILE"; then
        return 0
    fi

    cp -p "$GRUB_DEFAULT_FILE" "${GRUB_DEFAULT_FILE}.seine.bak"
    sed -i -E '/^[[:space:]]*GRUB_CMDLINE_LINUX(_DEFAULT)?=/ {
        s/(^|[[:space:]\"])(hugepages|hugepagesz|default_hugepagesz)=[^[:space:]\"]*/\1/g
    }' "$GRUB_DEFAULT_FILE"

    if command -v update-grub >/dev/null 2>&1; then
        update-grub
    elif command -v grub-mkconfig >/dev/null 2>&1 && [[ -d /boot/grub ]]; then
        grub-mkconfig -o /boot/grub/grub.cfg
    else
        die "已清理 ${GRUB_DEFAULT_FILE}，但未找到可用的 update-grub 或 grub-mkconfig。请手动生成 GRUB 配置。"
    fi
    echo "已清理 GRUB HugeTLB 参数，并备份原文件为 ${GRUB_DEFAULT_FILE}.seine.bak。"
}

restore_hugetlb_pages() {
    local counter current
    local found=0

    for counter in /sys/kernel/mm/hugepages/hugepages-*kB/nr_hugepages; do
        [[ -e "$counter" ]] || continue
        found=1
        current="$(<"$counter")"
        [[ "$current" =~ ^[0-9]+$ ]] || die "读取到无效的 HugeTLB nr_hugepages 值: ${counter}=${current}"
        if ((current > 0)); then
            echo "释放 HugeTLB 页: ${counter}（当前 ${current} 页）..."
            printf '0\n' >"$counter" || die "无法将 ${counter} 恢复为 0。"
            current="$(<"$counter")"
            [[ "$current" =~ ^[0-9]+$ ]] || die "读取到无效的 HugeTLB nr_hugepages 值: ${counter}=${current}"
            ((current == 0)) || die "${counter} 仍有 ${current} 个 HugeTLB 页，无法完全释放。"
        fi
    done

    if ((found == 0)); then
        echo "内核未提供 HugeTLB nr_hugepages 接口，无需释放。"
    else
        echo "HugeTLB nr_hugepages 已恢复为 0。"
    fi
}
printf '3\n' >/proc/sys/vm/drop_caches || die "无法释放页缓存。"
printf '1\n' >/proc/sys/vm/compact_memory || die "无法整理内存碎片。"
if ((EUID != 0)); then
    die "此脚本需要 root 权限，请使用 sudo bash $0 运行。"
fi

if ! command -v apt-get >/dev/null 2>&1; then
    die "仅支持带 apt-get 的 Debian/Ubuntu 系统。"
fi

echo "安装 tmux..."
apt-get install -y tmux

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "发现已有 tmux 会话 ${TMUX_SESSION}；先关闭旧会话后重建。"
    tmux kill-session -t "$TMUX_SESSION" || die "无法关闭已有 tmux 会话 ${TMUX_SESSION}。"
fi

remove_grub_hugepage_settings
restore_hugetlb_pages

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
printf -v tmux_command 'exec %q --pool-url %q --pool-worker %q --address %q --cpu-memory-reserve-percent 0' \
    "${INSTALL_DIR}/seine" "$POOL_URL" "$worker_name" "$WALLET_ADDRESS"
tmux new-session -d -s "$TMUX_SESSION" "$tmux_command"
echo "tmux new-session -d -s "$TMUX_SESSION" "$tmux_command""
echo "已启动 Seine：架构=${release_arch}，未启用 HugeTLB。"
echo "将在 5 秒后进入 tmux 会话；按 Ctrl+C 可取消自动进入。手动查看运行窗口：tmux attach -t ${TMUX_SESSION}"
sleep 5
exec tmux attach -t "$TMUX_SESSION"
