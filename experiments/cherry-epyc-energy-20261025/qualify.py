#!/usr/bin/env python3
"""Read-only host inventory; keep raw DMI identifiers in private evidence."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'qualification'


def capture(name, argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        record = {'argv': argv, 'exit_code': result.returncode,
                  'stdout': result.stdout, 'stderr': result.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        record = {'argv': argv, 'error': str(error)}
    (OUT / name).write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    OUT.mkdir(exist_ok=False)
    captures = {
        'lscpu.json': ['lscpu', '-J'],
        'cpu-topology.json': ['lscpu', '-e=CPU,CORE,SOCKET,NODE,CACHE,ONLINE'],
        'numa.json': ['numactl', '--hardware'],
        'memory-dmi-private.json': ['dmidecode', '--type', 'memory'],
        'kernel.json': ['uname', '-a'],
        'modules.json': ['lsmod'],
        'rapl-module.json': ['modinfo', 'intel_rapl_msr'],
        'virtualization.json': ['systemd-detect-virt'],
        'energy-probe.json': [sys.executable, str(ROOT / 'bench_cpu_energy.py'), 'probe'],
    }
    records = {name: capture(name, argv) for name, argv in captures.items()}
    for source, name in [('/proc/meminfo', 'meminfo.txt'), ('/proc/swaps', 'swaps.txt'),
                         ('/proc/sys/vm/nr_hugepages', 'initial-hugepages.txt'),
                         ('/proc/cmdline', 'kernel-cmdline.txt')]:
        (OUT / name).write_text(Path(source).read_text())
    dimms = []
    for block in records['memory-dmi-private.json'].get('stdout', '').split('\n\n'):
        if not re.search(r'^Memory Device$', block, re.MULTILINE):
            continue
        fields = dict(re.findall(r'^\s+([^:\n]+):\s*(.*)$', block, re.MULTILINE))
        dimms.append({key: fields[key] for key in ('Size', 'Locator', 'Bank Locator', 'Type',
                     'Speed', 'Configured Memory Speed', 'Total Width', 'Data Width', 'Rank')
                     if key in fields})
    (OUT / 'memory-layout.json').write_text(json.dumps(dimms, indent=2) + '\n')
    cpu = json.loads(records['lscpu.json']['stdout'])
    fields = {row['field'].rstrip(':'): row['data'] for row in cpu['lscpu']}
    probe = json.loads(records['energy-probe.json']['stdout'])
    summary = {'cpu': {key: fields.get(key) for key in ('Model name', 'Vendor ID', 'CPU family',
               'Model', 'Socket(s)', 'Core(s) per socket', 'Thread(s) per core', 'NUMA node(s)')},
               'installed_dimms': [d for d in dimms if d.get('Size') not in (None, 'No Module Installed')],
               'energy_probe': probe,
               'virtualization': records['virtualization.json'].get('stdout', '').strip(),
               'scope': 'Inventory only. DIMM locators need review before claiming channel population.'}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}
    (ROOT / 'qualification-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
