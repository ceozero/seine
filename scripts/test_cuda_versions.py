#!/usr/bin/env python3
"""Query disposable CUDA libraries, including missing/failed version symbols; no GPU work."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix='seine-cuda-versions-') as directory:
    root = Path(directory)
    for mode in ('present', 'missing', 'error', 'invalid'):
        case = root / mode
        case.mkdir()
        driver_version = -1 if mode == 'invalid' else 12080
        result = 1 if mode == 'error' else 0
        functions = {
            'cuda': f'int cuDriverGetVersion(int *v) {{ *v = {driver_version}; return {result}; }}',
            'nvrtc': f'int nvrtcVersion(int *major, int *minor) {{ *major = 12; *minor = {100 if mode == "invalid" else 9}; return {result}; }}',
        }
        for name, function in functions.items():
            source = case / f'{name}.c'
            source.write_text('int unused_placeholder(void) { return 0; }' if mode == 'missing' else function)
            subprocess.run(['cc', '-shared', '-fPIC', str(source), '-o', str(case / f'lib{name}.so')], check=True)
        env = dict(os.environ, SEINE_TEST_CUDA_VERSIONS=mode,
                   LD_LIBRARY_PATH=str(case) + os.pathsep + os.environ.get('LD_LIBRARY_PATH', ''))
        subprocess.run([sys.argv[1], '--exact', 'backend::nvidia::library_tests::software_version_probe',
                        '--ignored', '--nocapture'], env=env, check=True, timeout=30)
        print(f'PASS: CUDA version metadata {mode}')
