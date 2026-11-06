#!/usr/bin/env bash
# HiveOS runs this from the package directory inside its miner screen session
# and restarts it when it exits. h-config.sh has already written the arguments.

cd "$(dirname "$0")" || exit 1
# shellcheck source=h-manifest.conf
. ./h-manifest.conf

if [[ ! -s $CUSTOM_CONFIG_FILENAME ]]; then
	echo "seine: $CUSTOM_CONFIG_FILENAME is missing; check the flight sheet" >&2
	exit 1
fi
mapfile -t args <"$CUSTOM_CONFIG_FILENAME"

mkdir -p "$(dirname "$CUSTOM_LOG_BASENAME")" "$SEINE_DATA_DIR"

# The package ships the CUDA NVRTC libraries that NVIDIA mining needs.
export LD_LIBRARY_PATH="$SEINE_HOME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# NVIDIA GPU indexes follow PCI bus order, matching nvidia-smi and HiveOS.
export CUDA_DEVICE_ORDER=PCI_BUS_ID

echo "seine ${args[*]}"
# HiveOS stops the miner with Ctrl+C. tee ignores it so seine can still log
# while it shuts down; tee exits once seine closes the pipe.
./seine "${args[@]}" 2>&1 | (
	trap '' INT
	exec tee -a "$CUSTOM_LOG_BASENAME.log"
)
exit "${PIPESTATUS[0]}"
