#!/usr/bin/env python3
"""Linux loader regression test; takes a compiled Seine Rust test binary, no GPU work."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SHIM = r'''
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>
void *dlopen(const char *name, int flags) {
    void *(*real_open)(const char *, int) = dlsym(RTLD_NEXT, "dlopen");
    const char *kind = getenv("SEINE_TEST_MISSING_CUDA_LIBRARY");
    if (name && kind && ((strcmp(kind, "driver") == 0 && strstr(name, "libcuda.")) ||
                       (strcmp(kind, "nvrtc") == 0 && strstr(name, "libnvrtc")))) {
        return real_open("/seine-test-nonexistent-library.so", flags);
    }
    return real_open(name, flags);
}
'''

with tempfile.TemporaryDirectory(prefix='seine-loader-test-') as directory:
    root = Path(directory)
    source = root / 'missing.c'
    source.write_text(SHIM)
    library = root / 'missing.so'
    subprocess.run(['cc', '-shared', '-fPIC', str(source), '-ldl', '-o', str(library)], check=True)
    for kind in ('driver', 'nvrtc'):
        env = dict(os.environ, LD_PRELOAD=str(library), SEINE_TEST_MISSING_CUDA_LIBRARY=kind)
        subprocess.run([sys.argv[1], '--exact', 'backend::nvidia::library_tests::missing_library_probe',
                        '--ignored', '--nocapture'], env=env, check=True, timeout=30)
        print(f'PASS: missing {kind} returns a typed error without a panic')
