#!/usr/bin/env bash
# Builds the HiveOS custom miner package from a seine Linux x86_64 release.
#
#   packaging/hiveos/build.sh --archive seine-linux-x86_64.tar.gz --version v0.2.46
#
# Writes <out-dir>/seine-hiveos-<version>.tar.gz. HiveOS takes the miner name
# and version from that file name (the version is the text after the last
# dash), and the archive holds one top-level directory with the same name.
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
EOF
}

archive=""
version=""
out_dir=$PWD
nvrtc_archive=""
with_nvrtc=1
while [[ $# -gt 0 ]]; do
	case $1 in
	--archive) archive=$2; shift 2 ;;
	--version) version=$2; shift 2 ;;
	--out-dir) out_dir=$2; shift 2 ;;
	--nvrtc-archive) nvrtc_archive=$2; shift 2 ;;
	--no-nvrtc) with_nvrtc=0; shift ;;
	-h | --help) usage; exit 0 ;;
	*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
	esac
done
[[ -n $archive && -n $version ]] || { usage >&2; exit 2; }

# HiveOS reads the version after the last dash, so the version itself can't
# contain one (v0.3.0-rc1 becomes 0.3.0_rc1).
version=${version#v}
version=${version//-/_}
[[ $version =~ ^[0-9A-Za-z._+]+$ ]] || { echo "invalid version: $version" >&2; exit 2; }

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
# shellcheck source=../lib/package.sh
. "$repo/packaging/lib/package.sh"
name=seine-hiveos
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
stage="$work/stage/$name"
mkdir -p "$out_dir"

package_release "$archive" "$work" "$stage" "$repo"
install -m 0644 "$repo/docs/guides/hiveos.md" "$stage/README.md"

# The HiveOS scripts. HiveOS needs executable scripts.
for script in h-config.sh h-run.sh h-stats.sh; do
	package_script "$here/$script" "$stage/$script"
done
tr -d '\r' <"$here/h-manifest.conf" | sed "s/@SEINE_VERSION@/$version/" >"$stage/h-manifest.conf"
chmod 0644 "$stage/h-manifest.conf"

if [[ $with_nvrtc -eq 1 ]]; then
	package_nvrtc "$work" "$stage" "$nvrtc_archive"
fi
package_finish "$stage"

# One top-level directory named like the package.
package="$out_dir/$name-$version.tar.gz"
package_tar "$work/stage" "$name" "$package"
echo "$package"
