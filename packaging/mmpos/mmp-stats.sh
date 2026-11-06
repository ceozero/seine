#!/usr/bin/env bash
# The mmpOS agent runs this as `mmp-stats.sh DEVICE_COUNT LOG_FILE` every few
# seconds and sends the JSON it prints to the dashboard. Figures come from
# seine's local control API, so the log file isn't needed. mmpOS reads GPU
# temperatures and fans itself.

cd "$(dirname "$0")" || exit 1
# shellcheck source=mmp-external.conf
. ./mmp-external.conf

seine_mmpos_jq() {
	if [[ -x $SEINE_HOME/bin/jq ]]; then
		"$SEINE_HOME/bin/jq" "$@"
	else
		jq "$@"
	fi
}

# The value of FLAG in the seine arguments mmp-launch.sh wrote.
seine_mmpos_arg() {
	local flag=$1 line take=0
	[[ -r $SEINE_ARGS_FILE ]] || return 1
	while IFS= read -r line; do
		if [[ $take -eq 1 ]]; then
			printf '%s' "$line"
			return 0
		fi
		[[ $line == "$flag" ]] && take=1
		if [[ $line == "$flag="* ]]; then
			printf '%s' "${line#*=}"
			return 0
		fi
	done <"$SEINE_ARGS_FILE"
	return 1
}

seine_mmpos_stats() {
	local bind host token cookie raw gpus
	bind=$(seine_mmpos_arg --api-bind) || bind="127.0.0.1:$SEINE_API_PORT"
	host=${bind%:*}
	[[ -z $host || $host == 0.0.0.0 || $host == "[::]" ]] && host=127.0.0.1
	if ! token=$(seine_mmpos_arg --api-token); then
		cookie=$(seine_mmpos_arg --api-cookie) || cookie=$SEINE_API_COOKIE
		# The cookie exists only while seine runs.
		[[ -r $cookie ]] && token=$(<"$cookie")
	fi
	if [[ -z $token ]] || ! raw=$(curl --silent --fail --noproxy '*' --connect-timeout 2 \
		--max-time 5 -H "Authorization: Bearer $token" "http://$host:${bind##*:}/v1/miner/stats"); then
		echo "Miner API connection failed"
		return 0
	fi

	gpus='{}'
	[[ -r $SEINE_GPU_INFO ]] && gpus=$(<"$SEINE_GPU_INFO")
	seine_mmpos_jq -e 'type == "object"' <<<"$gpus" >/dev/null 2>&1 || gpus='{}'

	# One entry per device: the CPU first as "cpu", then each GPU by PCI bus
	# number. A GPU without a PCI address takes the bus of the Nth GPU of its
	# brand in mmpOS's list.
	# shellcheck disable=SC2016
	seine_mmpos_jq -c --argjson info "$gpus" --arg name "$EXTERNAL_NAME" '
		def hex: ascii_downcase | explode
			| reduce .[] as $c (0; . * 16 + (if $c >= 97 then $c - 87 else $c - 48 end));
		def bus: split(":") | .[-2] | hex;
		def rate: (. // 0) * 100 | floor / 100;
		($info.device.GPU // {}) as $known
		| {nvidia: ($known.nvidia_details.busid // []),
		   amd: ($known.amd_sysfs_details.busid // [])} as $busids
		| (.mining // {}) as $m
		| ($m.devices // []) as $devices
		| [$devices[] | select(.kind == "cpu") | .hashrate_hps // 0] as $cpu
		| [$devices[] | select(.kind != "cpu")
			| {hash: (.hashrate_hps | rate),
			   bus: (if .pci_address != null then .pci_address | bus
				elif .device_index != null and $busids[.kind][.device_index] != null
				then $busids[.kind][.device_index] | bus
				else null end)}] as $gpus
		| {
			busid: ((if ($cpu | length) > 0 then ["cpu"] else [] end) + [$gpus[].bus]),
			hash: ((if ($cpu | length) > 0 then [$cpu | add | rate] else [] end) + [$gpus[].hash]),
			units: "hs",
			air: [($m.accepted // 0 | tostring), "0", ($m.rejected // 0 | tostring)],
			miner_name: $name,
			miner_version: .version
		}' <<<"$raw" 2>/dev/null || echo "Miner API connection failed"
}

seine_mmpos_stats
