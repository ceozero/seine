# shellcheck shell=bash
# Shared steps for the mining OS packages (packaging/hiveos, packaging/mmpos).
# The build scripts source this file; it defines functions only.

SEINE_NVRTC_VERSION=12.8.61
SEINE_NVRTC_ARCHIVE_NAME="cuda_nvrtc-linux-x86_64-${SEINE_NVRTC_VERSION}-archive.tar.xz"
SEINE_NVRTC_URL="https://developer.download.nvidia.com/compute/cuda/redist/cuda_nvrtc/linux-x86_64/${SEINE_NVRTC_ARCHIVE_NAME}"
SEINE_NVRTC_SHA256=df1df922d6af3a01ccfbf4db9125b2c20b9b23bbd4a737be9d2261b241ae77c0

# package_release ARCHIVE WORK STAGE REPO
# Copies the seine binary and its license from a release archive (or a
# directory or a bare binary) into STAGE, plus the privacy notice.
package_release() {
	local archive=$1 work=$2 stage=$3 repo=$4 binary
	mkdir -p "$work/release" "$stage"
	if [[ -d $archive ]]; then
		cp -R "$archive/." "$work/release/"
	elif [[ $archive == *.tar.gz || $archive == *.tgz ]]; then
		tar -xzf "$archive" -C "$work/release"
	else
		cp "$archive" "$work/release/seine"
	fi
	binary=$(find "$work/release" -type f -name seine | head -n 1)
	[[ -n $binary ]] || { echo "no seine binary in $archive" >&2; return 1; }
	install -m 0755 "$binary" "$stage/seine"
	if [[ -f $work/release/SEINE-LICENSE.txt ]]; then
		install -m 0644 "$work/release/SEINE-LICENSE.txt" "$stage/SEINE-LICENSE.txt"
	else
		install -m 0644 "$repo/LICENSE" "$stage/SEINE-LICENSE.txt"
	fi
	install -m 0644 "$repo/PRIVACY.md" "$stage/PRIVACY.md"
}

# package_script SOURCE DEST [MODE]
# Mining OSes need Unix line endings.
package_script() {
	tr -d '\r' <"$1" >"$2"
	chmod "${3:-0755}" "$2"
}

# package_nvrtc WORK STAGE [ARCHIVE]
# NVRTC compiles seine's NVIDIA kernels at startup and mining OSes don't ship
# it. Downloads the CUDA redistributable unless ARCHIVE is given.
package_nvrtc() {
	local work=$1 stage=$2 nvrtc_archive=${3:-}
	local root="cuda_nvrtc-linux-x86_64-${SEINE_NVRTC_VERSION}-archive"
	if [[ -z $nvrtc_archive ]]; then
		nvrtc_archive="$work/$SEINE_NVRTC_ARCHIVE_NAME"
		curl --fail --silent --show-error --location --retry 3 -o "$nvrtc_archive" "$SEINE_NVRTC_URL"
	fi
	echo "$SEINE_NVRTC_SHA256  $nvrtc_archive" | sha256sum --check --quiet - || return 1
	tar -xJf "$nvrtc_archive" -C "$work" \
		"$root/LICENSE" \
		"$root/lib/libnvrtc.so.${SEINE_NVRTC_VERSION}" \
		"$root/lib/libnvrtc-builtins.so.${SEINE_NVRTC_VERSION}"
	mkdir -p "$stage/lib"
	install -m 0755 "$work/$root/lib/libnvrtc.so.${SEINE_NVRTC_VERSION}" "$stage/lib/"
	install -m 0755 "$work/$root/lib/libnvrtc-builtins.so.${SEINE_NVRTC_VERSION}" "$stage/lib/"
	ln -s "libnvrtc.so.${SEINE_NVRTC_VERSION}" "$stage/lib/libnvrtc.so.12"
	ln -s "libnvrtc-builtins.so.${SEINE_NVRTC_VERSION}" "$stage/lib/libnvrtc-builtins.so.${SEINE_NVRTC_VERSION%.*}"
	install -m 0644 "$work/$root/LICENSE" "$stage/NVIDIA-CUDA-NVRTC-LICENSE.txt"
}

# package_finish STAGE
# Writes SHA256SUMS.txt over every file and normalises directory modes.
package_finish() {
	local stage=$1 sums
	sums=$(mktemp)
	(cd "$stage" && find . -type f -printf '%P\n' | LC_ALL=C sort | xargs sha256sum) >"$sums"
	mv "$sums" "$stage/SHA256SUMS.txt"
	chmod 0644 "$stage/SHA256SUMS.txt"
	find "$stage" -type d -exec chmod 0755 {} +
}

# package_tar DIR MEMBER OUTPUT
# Reproducible tar.gz of MEMBER (a path relative to DIR).
package_tar() {
	local dir=$1 member=$2 output=$3
	tar -C "$dir" --sort=name --owner=0 --group=0 --numeric-owner \
		--mtime="@${SOURCE_DATE_EPOCH:-$(date +%s)}" -czf "$output.tmp" "$member"
	mv "$output.tmp" "$output"
}
