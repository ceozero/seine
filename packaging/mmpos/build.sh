#!/usr/bin/env bash
# Builds the mmpOS custom miner package from a seine Linux x86_64 release.
#
#   packaging/mmpos/build.sh --archive seine-linux-x86_64.tar.gz --version v0.2.46
#
# Writes <out-dir>/seine-mmpos-<version>.tar.gz. mmpOS unpacks a custom miner
# into its own directory, so the files sit at the archive root (as ./name).
set -euo pipefail

usage() {
	cat <<'EOF'
Usage: build.sh --archive PATH --version VERSION [options]

  --archive PATH        seine-linux-x86_64.tar.gz from a release (or a directory
                        or file holding the Linux x86_64 seine binary)
  --version VERSION     release version, for example v0.2.46
  --out-dir DIR         where to write the package (default: current directory)
  --nvrtc-archive PATH  CUDA NVRTC redistributable archive already downloaded
                        (cuda_nvrtc-linux-x86_64-12.8.61-archive.tar.xz)
  --no-nvrtc            leave NVRTC out (for tests; NVIDIA rigs need it)
  --jq PATH             jq 1.7.1 linux-amd64 binary already downloaded
EOF
}

JQ_VERSION=1.7.1
JQ_URL="https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/jq-linux-amd64"
JQ_SHA256=5942c9b0934e510ee61eb3e30273f1b3fe2590df93933a93d7c58b81d19c8ff5

archive=""
version=""
out_dir=$PWD
nvrtc_archive=""
with_nvrtc=1
jq_binary=""
while [[ $# -gt 0 ]]; do
	case $1 in
	--archive) archive=$2; shift 2 ;;
	--version) version=$2; shift 2 ;;
	--out-dir) out_dir=$2; shift 2 ;;
	--nvrtc-archive) nvrtc_archive=$2; shift 2 ;;
	--no-nvrtc) with_nvrtc=0; shift ;;
	--jq) jq_binary=$2; shift 2 ;;
	-h | --help) usage; exit 0 ;;
	*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
	esac
done
[[ -n $archive && -n $version ]] || { usage >&2; exit 2; }

version=${version#v}
[[ $version =~ ^[0-9A-Za-z._+-]+$ ]] || { echo "invalid version: $version" >&2; exit 2; }

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
# shellcheck source=../lib/package.sh
. "$repo/packaging/lib/package.sh"
name=seine-mmpos
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
stage="$work/stage"
mkdir -p "$out_dir"

package_release "$archive" "$work" "$stage" "$repo"
install -m 0644 "$repo/docs/guides/mmpos.md" "$stage/README.md"

for script in mmp-launch.sh mmp-stats.sh; do
	package_script "$here/$script" "$stage/$script"
done
tr -d '\r' <"$here/mmp-external.conf" | sed "s/@SEINE_VERSION@/$version/" >"$stage/mmp-external.conf"
chmod 0644 "$stage/mmp-external.conf"

# mmp-stats.sh needs jq, which mmpOS's Docker agent image doesn't include.
if [[ -z $jq_binary ]]; then
	jq_binary="$work/jq-linux-amd64"
	curl --fail --silent --show-error --location --retry 3 -o "$jq_binary" "$JQ_URL"
	echo "$JQ_SHA256  $jq_binary" | sha256sum --check --quiet -
fi
mkdir -p "$stage/bin"
install -m 0755 "$jq_binary" "$stage/bin/jq"
install -m 0644 "$here/JQ-LICENSE.txt" "$stage/JQ-LICENSE.txt"

if [[ $with_nvrtc -eq 1 ]]; then
	package_nvrtc "$work" "$stage" "$nvrtc_archive"
fi
package_finish "$stage"

package="$out_dir/$name-$version.tar.gz"
package_tar "$stage" . "$package"
echo "$package"
