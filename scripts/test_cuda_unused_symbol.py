#!/usr/bin/env python3
"""Reproduce the telemetry cuCtxGetId loader failure without GPU work (Linux)."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

# cudarc 0.19.2 resolves these names before cuCtxGetId. Provide all of them so
# the old loader fails at the exact production location, not an earlier symbol.
# None is callable: abort if a test accidentally tries real CUDA operations.
BEFORE_CONTEXT_ID = """
cuArray3DCreate_v2 cuArray3DGetDescriptor_v2 cuArrayCreate_v2 cuArrayDestroy
cuArrayGetDescriptor_v2 cuArrayGetMemoryRequirements cuArrayGetPlane cuArrayGetSparseProperties
cuCoredumpGetAttribute cuCoredumpGetAttributeGlobal cuCoredumpSetAttribute cuCoredumpSetAttributeGlobal
cuCtxAttach cuCtxCreate_v2 cuCtxCreate_v3 cuCtxDestroy_v2 cuCtxDetach cuCtxDisablePeerAccess
cuCtxEnablePeerAccess cuCtxFromGreenCtx cuCtxGetApiVersion cuCtxGetCacheConfig cuCtxGetCurrent
cuCtxGetDevResource cuCtxGetDevice cuCtxGetDevice_v2 cuCtxGetExecAffinity cuCtxGetFlags
""".split()

with tempfile.TemporaryDirectory(prefix='seine-unused-cuda-symbol-') as directory:
    root = Path(directory)
    source = root / 'driver.c'
    source.write_text('#include <stdlib.h>\n'
                      'int cuInit(unsigned int flags) { (void)flags; return 100; }\n' +
                      '\n'.join(f'int {name}(void) {{ abort(); }}' for name in BEFORE_CONTEXT_ID))
    subprocess.run(['cc', '-shared', '-fPIC', str(source), '-o', str(root / 'libcuda.so')], check=True)
    env = dict(os.environ, SEINE_TEST_UNUSED_CUDA_SYMBOL='1',
               LD_LIBRARY_PATH=str(root) + os.pathsep + os.environ.get('LD_LIBRARY_PATH', ''))
    subprocess.run([sys.argv[1], '--exact', 'backend::nvidia::library_tests::unused_driver_symbol_probe',
                    '--ignored', '--nocapture'], env=env, check=True, timeout=30)
    print('PASS: missing unused cuCtxGetId does not panic; cuInit returns the fake driver error')
