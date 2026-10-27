#!/bin/bash
# Page-backing screen for the candidate build at one worker count: THP (no
# HugeTLB pool) vs explicit 2 MiB HugeTLB vs 1 GiB pages, interleaved.
# Usage (root, /opt/cohort): remote_pages_ab.sh <kernel> <threads>
set -u
KERNEL=$1 T=$2
R=/opt/cohort/results/pages-t$T
SECS=${SECS:-20}
mkdir -p "$R"; chown -R bench:bench /opt/cohort
pool2m() { echo "$1" > /proc/sys/vm/nr_hugepages; }
pool1g() { echo "$1" > /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages; }
one() { # one <mode> <tag>
  case $1 in
    thp) pool1g 0; pool2m 0; MODE=auto ;;
    2m) pool1g 0; sync; echo 3 > /proc/sys/vm/drop_caches; echo 1 > /proc/sys/vm/compact_memory; pool2m $((T * 1024 + 64)); MODE=large ;;
    1g) pool2m 0; sync; echo 3 > /proc/sys/vm/drop_caches; echo 1 > /proc/sys/vm/compact_memory; pool1g $((T * 2)); MODE=large-1g ;;
  esac
  echo "$2 pool2m=$(cat /proc/sys/vm/nr_hugepages) pool1g=$(cat /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages)" >> "$R/pools.txt"
  unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- env HOME=/home/bench \
    bash -c 'cd /opt/cohort/candidate && exec ./seine --bench --bench-kind backend --backend cpu --ui plain \
      --data-dir /home/bench/pages --threads "$0" --disable-cpu-autotune-threads --bench-cpu-kernel "$1" \
      --cpu-page-mode "$2" --bench-secs "$3" --bench-rounds 1 --bench-warmup-rounds 1 --bench-output "$4"' \
    "$T" "$KERNEL" "$MODE" "$SECS" "$R/$2.json" > "$R/$2.log" 2>&1
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], round(d['avg_hps'], 3))" "$R/$2.json" "$2" 2>/dev/null || echo "$2 FAILED"
}
{
  one thp 1-thp; one 2m 2-2m; one 1g 3-1g
  one 1g 4-1g; one 2m 5-2m; one thp 6-thp
} | tee "$R/summary.txt"
pool1g 0; pool2m 0
