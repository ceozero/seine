"""Loopback-only pool fixture and task-owned systemd helpers."""
import argparse

import datetime

import json

import hashlib

from pathlib import Path

import socketserver

import re

import subprocess

import threading

import time

ROOT = Path(__file__).resolve().parent

OUT = ROOT / "results/lifecycle"

SERVER_EVENTS = []

class Fixture(socketserver.StreamRequestHandler):
    def handle(self):
        for raw in self.rfile:
            if not raw.strip():
                continue
            request = json.loads(raw)
            SERVER_EVENTS.append({"at": time.time(), "method": request.get("method"), "id": request.get("id")})
            if request.get("method") == "login":
                response = {"id": request["id"], "status": "ok", "result": {"protocol_version": 2,
                            "capabilities": ["login_negotiation", "submit_claimed_hash"]}}
                job = {"method": "job", "params": {"job_id": "campaign-offline", "header_base": "00" * 92,
                       "target": "00" * 32, "network_target": "00" * 32, "height": 1,
                       "nonce_start": 0, "nonce_end": (1 << 63) - 1}}
                self.wfile.write((json.dumps(response) + "\n" + json.dumps(job) + "\n").encode())
                self.wfile.flush()
            elif request.get("method") == "submit":
                raise AssertionError("impossible target unexpectedly produced a solution")

class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

def command(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=30)

def state(unit):
    properties = dict(line.split("=", 1) for line in command([
        "systemctl", "show", unit, "--property=ControlGroup", "--property=MainPID"]).splitlines())
    path = properties["ControlGroup"]
    group = Path("/sys/fs/cgroup") / path.lstrip("/")
    result = {"time": time.time(), "cgroup": path, "pid": int(properties["MainPID"])}
    rollup = Path("/proc") / properties["MainPID"] / "smaps_rollup"
    if rollup.exists():
        result["smaps_rollup"] = {line.split(":")[0]: line.split(":", 1)[1].strip()
                                  for line in rollup.read_text().splitlines() if ":" in line
                                  and line.split(":")[0] in ("Rss", "Anonymous", "AnonHugePages", "Private_Hugetlb", "Shared_Hugetlb")}
    for name in ("memory.current", "memory.peak", "memory.high", "memory.max", "memory.events", "memory.pressure", "cpu.stat", "cpu.pressure"):
        file = group / name
        if file.exists():
            result[name] = file.read_text().strip()
    return result

def fixture_address():
    # Two compressed Ristretto identities are syntactically valid test keys.
    # A literal address avoids the network shortname-resolution startup path.
    payload = bytes(64)
    checksum = hashlib.sha3_256(b"blocknet_stealth_address_checksum" + b"blocknet_mainnet" + payload).digest()[:4]
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    value = int.from_bytes(checksum, "big")
    encoded = ""
    while value:
        value, digit = divmod(value, 58)
        encoded = alphabet[digit] + encoded
    return "1" * 64 + encoded

def stop(unit):
    stopped = subprocess.run(["sudo", "systemctl", "stop", unit], capture_output=True, text=True, timeout=30)
    if stopped.returncode:
        assert "not loaded" in stopped.stderr, stopped.stderr
    active = command(["systemctl", "show", unit, "--property=ActiveState", "--value"]).strip()
    assert active not in ("active", "activating", "deactivating"), (unit, active)
