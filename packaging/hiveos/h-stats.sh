#!/usr/bin/env bash
# shellcheck disable=SC2154,SC2034
# The HiveOS agent sources this every few seconds and reads $khs (total kH/s)
# and $stats (JSON). Figures come from seine's local control API; GPU
# temperatures and fans come from HiveOS's own $gpu_stats.

seine_hiveos_stats() {
	local dir token raw gpus cpu_temp
	dir=$(dirname "${BASH_SOURCE[0]}")
	# shellcheck source=h-manifest.conf
	. "$dir/h-manifest.conf"

	khs=0
	stats=null
	# The cookie exists only while seine runs.
	[[ -r $SEINE_API_COOKIE ]] || return 0
	token=$(<"$SEINE_API_COOKIE")
	raw=$(curl --silent --fail --noproxy '*' --connect-timeout 2 --max-time 5 \
		-H "Authorization: Bearer $token" \
		"http://127.0.0.1:$SEINE_API_PORT/v1/miner/stats") || return 0

	gpus=${gpu_stats:-}
	[[ -z $gpus && -n ${GPU_STATS_JSON:-} && -r $GPU_STATS_JSON ]] && gpus=$(<"$GPU_STATS_JSON")
	# jq 1.6 (HiveOS) exits 0 on empty input, so check for that first.
	[[ -n $gpus ]] && jq -e 'type == "object"' <<<"$gpus" >/dev/null 2>&1 || gpus='{}'
	cpu_temp=null
	if command -v cpu-temp >/dev/null 2>&1; then
		cpu_temp=$(cpu-temp 2>/dev/null)
		[[ $cpu_temp =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || cpu_temp=null
	fi

	# Map each seine device to HiveOS's GPU list by PCI bus number, falling
	# back to the Nth GPU of the same brand when seine has no PCI address.
	# shellcheck disable=SC2016
	stats=$(jq -c \
		--argjson gpu "$gpus" \
		--argjson cpu_temp "$cpu_temp" \
		--arg algo "${CUSTOM_ALGO:-blocknet}" '
		def hex: ascii_downcase | explode
			| reduce .[] as $c (0; . * 16 + (if $c >= 97 then $c - 87 else $c - 48 end));
		def rate: (. // 0) * 100 | floor / 100;
		($gpu.busids // []) as $busids
		| ($gpu.brand // []) as $brands
		| [$busids[] | split(":")[0] | hex] as $bus_list
		| def slot($dev):
			if $dev.pci_address != null then
				($dev.pci_address | split(":") | .[-2] | hex) as $bus
				| [range($bus_list | length) | select($bus_list[.] == $bus)][0]
			elif $dev.device_index != null then
				[range($brands | length) | select($brands[.] == $dev.kind)][$dev.device_index]
			else null end;
		.mining as $m
		| [($m.devices // [])[] | . as $dev
			| if .kind == "cpu" then
				{hs: (.hashrate_hps | rate), temp: $cpu_temp, fan: null, bus: null}
			else
				slot($dev) as $i
				| {hs: (.hashrate_hps | rate),
				   temp: (if $i == null then null else $gpu.temp[$i] end),
				   fan: (if $i == null then null else $gpu.fan[$i] end),
				   bus: (if $i == null then null else $bus_list[$i] end)}
			end] as $devices
		| {
			hs: [$devices[].hs],
			hs_units: "hs",
			temp: [$devices[].temp],
			fan: [$devices[].fan],
			bus_numbers: [$devices[].bus],
			uptime: (($m.uptime_secs // 0) | floor),
			ar: [($m.accepted // 0), ($m.rejected // 0)],
			total_khs: (($m.hashrate_hps // 0) / 1000),
			algo: $algo,
			ver: .version
		}' <<<"$raw" 2>/dev/null) || stats=null
	if [[ -z $stats || $stats == null ]]; then
		stats=null
		return 0
	fi
	khs=$(jq -r '.total_khs' <<<"$stats")
}

seine_hiveos_stats
