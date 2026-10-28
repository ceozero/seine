#!/usr/bin/env python3
"""Collect all-target Stratum work for independent, offline PoW verification.

This is a local benchmark receiver, not a production pool. Replies acknowledge
receipt only: cryptographic acceptance is established by a separate verifier.
Run inside an isolated network namespace with the miner under test.
Copied from the Oct 2026 competitor-parity campaign; driven by remote_live_compete.sh.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import threading
import time


def fixture_address():
    payload = bytes(64)  # Two public identity points; no real wallet credentials.
    checksum = hashlib.sha3_256(
        b"blocknet_stealth_address_checksumblocknet_testnet" + payload
    ).digest()[:4]
    raw = payload + checksum
    number = int.from_bytes(raw, "big")
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + encoded


def miner_command(args, address, port):
    tls = args.tls_cert is not None
    command = [args.executable]
    if args.miner != "ntmminer":
        command += ["--mode", "pool"]
    command += ["--address", address, "--pool-url",
                f"stratum+{'ssl' if tls else 'tcp'}://127.0.0.1:{port}",
                "--pool-worker", "fixture"]
    if args.miner == "ntmminer":
        command += ["--tls-name", args.tls_name]
    extra = args.args[1:] if args.args[:1] == ["--"] else args.args
    return command + extra


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--warmup", type=float, default=15)
    parser.add_argument("--startup-timeout", type=float, default=180)
    parser.add_argument("--listen-port", type=int, default=0,
                        help="Use 3333 with a sandbox-only bntpool.com hosts mapping to capture Seine developer work")
    parser.add_argument("--job-secs", type=float, default=0,
                        help="Replace each connection's job at this interval; 0 keeps the static baseline")
    parser.add_argument("--stale-grace", type=float, default=0,
                        help="Accept superseded work for this many seconds in job-change tests")
    parser.add_argument("--window-origin", choices=["launch", "first-share"], default="first-share")
    parser.add_argument("--seed", default="seine-longhorn-parity-v1")
    parser.add_argument("--miner", choices=["seine", "seine-base", "longhorn", "ntmminer"], required=True)
    parser.add_argument("--tls-cert", type=Path,
                        help="Fixture certificate chain; listener remains loopback-only")
    parser.add_argument("--tls-key", type=Path,
                        help="Private key for the disposable fixture certificate, never a production key")
    parser.add_argument("--tls-name", default="localhost",
                        help="Expected certificate identity passed to NTMminer")
    parser.add_argument("--executable", required=True)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if (args.tls_cert is None) != (args.tls_key is None):
        parser.error("TLS requires both --tls-cert and --tls-key")
    if args.miner == "ntmminer" and args.tls_cert is None:
        parser.error("NTMminer requires a local TLS fixture")
    if args.seconds <= 0 or args.warmup < 0 or args.startup_timeout <= 0:
        parser.error("invalid timing bounds")
    if not 0 <= args.listen_port <= 65535:
        parser.error("invalid listening port")
    if (not math.isfinite(args.job_secs) or not math.isfinite(args.stale_grace)
            or args.job_secs < 0 or args.stale_grace < 0):
        parser.error("job interval and stale grace must be nonnegative")
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "wire.jsonl").exists():
        parser.error("output already contains a run; use a new directory")
    tls_context = None
    if args.tls_cert is not None:
        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls_context.minimum_version = ssl.TLSVersion.TLSv1_3
        tls_context.maximum_version = ssl.TLSVersion.TLSv1_3
        tls_context.load_cert_chain(args.tls_cert, args.tls_key)
    header = hashlib.shake_256(args.seed.encode()).digest(92).hex()
    address = fixture_address()
    started = time.monotonic()
    stop = threading.Event()
    teardown = threading.Event()
    lock = threading.Lock()
    first_share = []
    shares = []
    connections = []
    errors = []
    connection_events = []
    generations = {"user": 0, "fee": 0}
    server = socket.socket()
    server.bind(("127.0.0.1", args.listen_port))
    server.listen(16)
    server.settimeout(0.25)
    port = server.getsockname()[1]
    wire = (args.output / "wire.jsonl").open("w", buffering=1)

    def record(value):
        with lock:
            wire.write(json.dumps({"elapsed": time.monotonic()-started, **value}) + "\n")

    def serve(conn, connection_id):
        identity = None
        job_header = header
        job = None
        issued = {}
        retired = {}
        next_job_at = None
        buffer = b""
        conn.settimeout(0.25)
        def connection_event(kind, error=None):
            event = {"connection": connection_id, "elapsed": time.monotonic()-started,
                     "kind": kind, "phase": "teardown" if teardown.is_set() else "measurement",
                     "role": None if identity is None else ("user" if identity == address else "fee"),
                     "buffered_bytes": len(buffer), "error": str(error) if error else None}
            with lock:
                connection_events.append(event)

        def send(value):
            record({"connection": connection_id, "direction": "out", "message": value})
            conn.sendall((json.dumps(value) + "\n").encode())

        def issue_job(now):
            nonlocal job, job_header, next_job_at
            kind = "user" if identity == address else "fee"
            with lock:
                generation = generations[kind]
                generations[kind] += 1
            if job is not None:
                retired[job['job_id']] = now-started
            seed = args.seed if kind == "user" else args.seed + "/fee"
            if args.job_secs and generation:
                seed += f"/change/{generation}"
            job_header = hashlib.shake_256(seed.encode()).digest(92).hex()
            job = {
                "job_id": f"fixture-{kind}-{generation}",
                "template_id": f"fixture-template-{kind}-{generation}" if args.job_secs else "fixture-template-"+kind,
                "header_base": job_header, "target": "ff"*32,
                "network_target": "00"*32, "difficulty": 1, "height": generation+1 if args.job_secs else 1,
                "nonce_start": generation * (1 << 40),
                "nonce_end": (generation+1) * (1 << 40)-1}
            issued[job['job_id']] = job
            next_job_at = now + args.job_secs if args.job_secs else None
            send({"method": "job", "params": job})

        def rotate_due():
            if not teardown.is_set() and next_job_at is not None and time.monotonic() >= next_job_at:
                issue_job(time.monotonic())

        try:
            if tls_context is not None:
                conn.settimeout(5)
                conn = tls_context.wrap_socket(conn, server_side=True)
                record({"connection": connection_id, "direction": "transport",
                        "tls_version": conn.version(), "cipher": conn.cipher()})
                conn.settimeout(0.25)
            while not stop.is_set():
                rotate_due()
                try:
                    data = conn.recv(65536)
                except socket.timeout:
                    continue
                if not data:
                    connection_event("peer_eof")
                    break
                buffer += data
                if len(buffer) > 1024 * 1024:
                    raise ValueError("oversized protocol buffer")
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    record({"connection": connection_id, "direction": "in", "message": msg})
                    method, params = msg.get("method"), msg.get("params", {})
                    if method == "login":
                        identity = params.get("address")
                        if not isinstance(identity, str) or not identity:
                            raise ValueError("login requires an address")
                        send({"id": msg.get("id"), "status": "ok", "result": {
                            "protocol_version": 2, "capabilities": ["submit_claimed_hash"],
                            "required_capabilities": []}})
                        issue_job(time.monotonic())
                    elif method == "submit":
                        rotate_due()
                        now = time.monotonic()
                        submitted = issued.get(params.get('job_id'))
                        retired_at = retired.get(params.get('job_id'))
                        stale = submitted is not None and retired_at is not None
                        eligible = submitted is not None and (not stale or now-started < retired_at + args.stale_grace)
                        rejection = None if eligible else ('stale job' if stale else 'unknown job')
                        with lock:
                            if not first_share:
                                first_share.append(now)
                            shares.append({"elapsed": now-started, "connection": connection_id,
                                           "user_work": identity == address,
                                           "header_base": submitted['header_base'] if submitted else job_header,
                                           "job": submitted, "params": params,
                                           "stale": stale, "eligible": eligible,
                                           "job_retired_elapsed": retired_at, "reject_reason": rejection})
                        send({"id": msg.get("id"), "status": "ok", "result": {
                            "accepted": eligible, "verified": False,
                            "status": "accepted" if eligible else "rejected",
                            "error": rejection, "difficulty": 1}})
                    elif msg.get("id") is not None:
                        send({"id": msg["id"], "status": "ok"})
        except ConnectionError as error:
            # A peer can reset its old socket when rotating fee destinations.
            # Retain the interruption for review; it is not malformed Stratum.
            # Lost/unreceived work never enters the measured share count.
            connection_event("peer_reset", error)
        except (OSError, ValueError, TypeError) as error:
            with lock:
                errors.append({"connection": connection_id, "elapsed": time.monotonic()-started,
                               "error": str(error)})
        finally:
            conn.close()

    def accept():
        while not stop.is_set():
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            thread = threading.Thread(target=serve, args=(conn, len(connections)), daemon=True)
            connections.append(thread)
            thread.start()

    listener = threading.Thread(target=accept, daemon=True)
    listener.start()
    command = miner_command(args, address, port)
    output = (args.output / "miner.log").open("w")
    if os.name == "nt":
        from windows_job import WindowsJobProcess
        process = WindowsJobProcess(command, output)
    else:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    reason = "measurement_complete"
    try:
        while True:
            now = time.monotonic()
            if process.poll() is not None:
                reason = "miner_exited"
                break
            anchor = started if args.window_origin == "launch" else (first_share[0] if first_share else None)
            if anchor is not None and now >= anchor + args.warmup + args.seconds:
                break
            if not first_share and now-started > args.startup_timeout:
                reason = "startup_timeout"
                break
            time.sleep(0.05)
    finally:
        teardown.set()
        if process.poll() is None:
            if os.name == "nt":
                process.terminate()
            else:
                os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if os.name == "nt":
            # The native launcher may have exited before its mining child.
            process.close()
        stop.set()
        server.close()
        listener.join(timeout=2)
        for thread in connections:
            # A client may still be inside the bounded TLS handshake when the
            # measurement ends. Finish recording its outcome before closing wire.
            thread.join(timeout=6 if tls_context else 2)
        output.close()
        wire.close()
    anchor = started if args.window_origin == "launch" else (first_share[0] if first_share else None)
    window_start = anchor-started+args.warmup if anchor is not None else None
    window_end = window_start+args.seconds if window_start is not None else None
    measured = [s for s in shares if window_start is not None and window_start <= s["elapsed"] < window_end]
    result = {"schema": 1, "miner": args.miner, "command": command, "header_base": header,
              "window_origin": args.window_origin,
              "listen_port": port,
              "transport": {"tls": tls_context is not None,
                            "tls_version": "TLSv1.3" if tls_context else None,
                            "certificate_sha256": hashlib.sha256(args.tls_cert.read_bytes()).hexdigest()
                            if args.tls_cert else None},
              "job_interval_seconds": args.job_secs, "stale_grace_seconds": args.stale_grace,
              "target": "ff"*32, "seed": args.seed, "termination_reason": reason,
              "exit_code": process.returncode, "launch_to_first_share_seconds": first_share[0]-started if first_share else None,
              "measurement_start_seconds": window_start, "measurement_end_seconds": window_end,
              "measurement_duration_seconds": args.seconds, "received_in_window": len(measured),
              "received_hps_unverified": len(measured)/args.seconds,
              "received_eligible_user_hps_unverified": sum(s['eligible'] and s['user_work'] for s in measured)/args.seconds,
              "stale_receipts_in_window": sum(s['stale'] for s in measured),
              "rejected_receipts_in_window": sum(not s['eligible'] for s in measured),
              "verification": "pending; receipt acknowledgements are not cryptographic validation",
              "shares": shares, "protocol_errors": errors,
              "connection_events": connection_events,
              "connection_review_required": any(event['kind'] == 'peer_reset' and event['phase'] == 'measurement'
                                                for event in connection_events)}
    (args.output / "work.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k: v for k,v in result.items() if k not in {"shares", "command", "header_base"}}))
    return 0 if reason == "measurement_complete" and shares else 1


if __name__ == "__main__":
    raise SystemExit(main())
