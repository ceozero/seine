"""Host health counters for bounded native experiments."""
from pathlib import Path

def counters():
    vm = dict(line.split() for line in Path("/proc/vmstat").read_text().splitlines())
    cpu = [int(v) for v in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
    return {k: int(vm[k]) for k in ("pswpin", "pswpout", "oom_kill")} | {
        "cpu_total": sum(cpu[:8]), "cpu_steal": cpu[7]}
