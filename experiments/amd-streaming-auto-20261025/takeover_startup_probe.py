"""Claude takeover launcher: resolve this gpuq job's own id, then run daemon_probe unchanged."""
import json, runpy, subprocess, sys
from pathlib import Path
GPUQ = r'D:\AI\gpuq\gpuq.exe'
root = Path(__file__).resolve().parent
status = json.loads(subprocess.check_output([GPUQ, 'status'], text=True, timeout=10))
job = status['activeJobId']
spec = json.loads(subprocess.check_output([GPUQ, 'show', job], text=True, timeout=10))['spec']
assert spec['source'] == 'seine-ryzen-startup-probe-claude-20261025', spec['source']
sys.argv = ['daemon_probe_startup.py', '--root', str(root), '--job', job]
sys.path.insert(0, str(root))
runpy.run_path(str(root / 'daemon_probe_startup.py'), run_name='__main__')
