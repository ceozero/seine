#!/usr/bin/env python3
"""Verify captured Stratum hashes with the independent libargon2 implementation.

Run after measurement: full 2 GiB reference hashing is deliberately excluded
from timed mining. A persistent cache avoids rehashing identical work, but its
entries must be created by this verifier, never supplied by either miner.
"""
import argparse
import ctypes
import ctypes.util
import hashlib
import json
import math
from pathlib import Path
import time


def lock_cache(path):
    """Keep the returned handle alive until all cache reads/writes finish."""
    import os
    handle = path.with_suffix('.lock').open('a+')
    if os.name == 'nt':
        import msvcrt
        handle.seek(0)
        handle.write('0')
        handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return handle


def reference_hasher(library_path=None):
    name = str(Path(library_path).resolve(strict=True)) if library_path else ctypes.util.find_library("argon2")
    if not name:
        raise RuntimeError("libargon2 is required for independent verification")
    library = ctypes.CDLL(name)
    function = library.argon2id_hash_raw
    function.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
                         ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                         ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    function.restype = ctypes.c_int
    def hash_nonce(header, nonce):
        password = ctypes.create_string_buffer(nonce.to_bytes(8, "little"))
        salt = ctypes.create_string_buffer(header)
        output = ctypes.create_string_buffer(32)
        code = function(1, 2*1024*1024, 1, password, 8, salt, len(header), output, 32)
        if code:
            raise RuntimeError(f"argon2id_hash_raw returned {code}")
        return output.raw.hex()
    return name, hash_nonce


def reference_key(work, share):
    nonce = share['params']['nonce']
    if type(nonce) is not int or not 0 <= nonce < (1 << 64):
        raise ValueError('invalid nonce')
    header = bytes.fromhex(share.get('header_base', work['header_base']))
    if len(header) != 92:
        raise ValueError('wrong header length')
    return header, nonce, header.hex() + ':' + str(nonce)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--reference-library", type=Path,
                        help="Explicit independently built libargon2, when it is not installed system-wide")
    parser.add_argument("--cache-only", action="store_true",
                        help="Require all independent reference values in the cache; never compute missing hashes")
    args = parser.parse_args()
    raw = args.work.read_bytes()
    work = json.loads(raw)
    duration = work['measurement_duration_seconds']
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('invalid measurement duration')
    start, end = work['measurement_start_seconds'], work['measurement_end_seconds']
    if start is not None and (not math.isfinite(start) or not math.isfinite(end)
                             or not math.isclose(end-start, duration, abs_tol=1e-6)):
        raise ValueError('measurement bounds do not match duration')
    cache_guard = lock_cache(args.cache)
    cache_raw = args.cache.read_bytes() if args.cache.exists() else b'{}'
    cache = json.loads(cache_raw)
    if args.cache_only:
        missing = {reference_key(work, share)[2] for share in work['shares']} - cache.keys()
        if missing:
            parser.error(f'cache-only verification requires {len(missing)} missing independent reference values')
        name, hash_nonce = 'independent libargon2 cache (no hashing performed)', None
    else:
        name, hash_nonce = reference_hasher(args.reference_library)
    seen = set()
    results = []
    started = time.monotonic()
    for index, share in enumerate(work["shares"]):
        params = share["params"]
        header, nonce, key = reference_key(work, share)
        if key not in cache:
            assert hash_nonce is not None, 'Cache-only verification must not hash'
            cache[key] = hash_nonce(header, nonce)
            temp = args.cache.with_suffix(".tmp")
            temp.write_text(json.dumps(cache, sort_keys=True)+"\n")
            temp.replace(args.cache)
        valid = params.get("claimed_hash", "").lower() == cache[key]
        job = share.get("job")
        if job is not None:
            valid = (valid and params.get("job_id") == job["job_id"]
                     and job['header_base'] == header.hex()
                     and job["nonce_start"] <= nonce <= job["nonce_end"])
        else:
            valid = False
        eligible = share.get('eligible', True)
        retired_at = share.get('job_retired_elapsed')
        if retired_at is not None:
            expected = share['elapsed'] < retired_at + work.get('stale_grace_seconds', 0)
            valid = valid and eligible is expected and share.get('stale') is True
        start, end = work["measurement_start_seconds"], work["measurement_end_seconds"]
        in_window = start is not None and start <= share["elapsed"] < end
        results.append({"index": index, "valid": valid, "duplicate": key in seen,
                        "in_window": in_window, "user_work": share["user_work"],
                        "eligible": eligible, "stale": share.get('stale', False)})
        seen.add(key)
        print(f"verified {index+1}/{len(work['shares'])} valid={valid}", flush=True)
    counted = [r for r in results if r["valid"] and not r["duplicate"] and r["in_window"]]
    useful = [r for r in counted if r['eligible']]
    summary = {"schema": 1, "work_sha256": hashlib.sha256(raw).hexdigest(),
               "cache_only": args.cache_only,
               "initial_cache_sha256": hashlib.sha256(cache_raw).hexdigest(),
               "measurement_complete": work["termination_reason"] == "measurement_complete",
               "reference": name, "argon2": {"type": "id", "version": 19, "memory_kib": 2097152,
                                            "iterations": 1, "parallelism": 1, "output_bytes": 32},
               "verification_seconds": time.monotonic()-started, "verified_shares": len(results),
               "invalid": sum(not r["valid"] for r in results),
               "duplicates": sum(r["duplicate"] for r in results),
               "verified_unique_in_window": len(counted),
               "verified_unique_hps": len(counted)/work["measurement_duration_seconds"],
               "verified_useful_hps": len(useful)/work["measurement_duration_seconds"],
               "verified_user_hps": sum(r["user_work"] for r in useful)/work["measurement_duration_seconds"],
               "verified_stale_in_window": sum(r['stale'] for r in counted),
               "verified_rejected_in_window": len(counted)-len(useful),
               "results": results}
    args.work.with_name("verification.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k != "results"}))
    return 0 if (results and summary["measurement_complete"]
                 and not summary["invalid"] and not summary["duplicates"]
                 and not work.get("protocol_errors")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
