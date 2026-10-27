"""Serial, resumable benchmark campaigns. Commands are trusted local argv lists."""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time

import benchctl as lab

SCHEMA = "seine-benchmark-campaign/v1"
STAGES = ("build", "correctness", "screen", "confirm")
TERMINAL = ("accepted", "rejected", "failed")


class CampaignError(ValueError):
    pass


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CampaignError(f"cannot read {path}: {exc}") from exc


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def require_keys(value, allowed, where):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise CampaignError(f"invalid or unknown fields in {where}")


def positive(value, where, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0
            or (integer and not isinstance(value, int))):
        raise CampaignError(f"{where} must be a finite positive {'integer' if integer else 'number'}")


def load_plan(path):
    plan = read_json(path)
    require_keys(plan, ("schema", "experiments"), "campaign")
    if plan.get("schema") != SCHEMA or not isinstance(plan.get("experiments"), list):
        raise CampaignError(f"expected schema {SCHEMA} and an experiments array")
    if not plan["experiments"]:
        raise CampaignError("campaign must contain experiments")
    seen = set()
    for experiment in plan["experiments"]:
        require_keys(experiment, ("id", "hypothesis", "cwd", "inputs", "artifacts", "stages"), "experiment")
        name = experiment.get("id")
        if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", name):
            raise CampaignError("experiment id must be 1-80 letters, digits, underscores or hyphens")
        if name.casefold() in seen:
            raise CampaignError(f"duplicate experiment id: {name}")
        seen.add(name.casefold())
        if not isinstance(experiment.get("hypothesis"), str) or not experiment["hypothesis"].strip():
            raise CampaignError(f"{name}: hypothesis is required")
        if not isinstance(experiment.get("cwd"), str):
            raise CampaignError(f"{name}: cwd is required (relative to the plan)")
        cwd = (path.parent / experiment["cwd"]).resolve()
        if not cwd.is_dir():
            raise CampaignError(f"working directory does not exist: {cwd}")
        experiment["cwd"] = str(cwd)
        for key in ("inputs", "artifacts"):
            paths = experiment.get(key)
            if not isinstance(paths, list) or not paths or any(not isinstance(p, str) or not p for p in paths):
                raise CampaignError(f"{name}: {key} must be a nonempty list of file paths")
            experiment[key] = [str((cwd / p).resolve()) for p in paths]
        stages = experiment.get("stages")
        require_keys(stages, STAGES, f"{name} stages")
        if not {"correctness", "screen", "confirm"} <= stages.keys():
            raise CampaignError(f"{name}: correctness, screen and confirm stages are required")
        for stage, spec in stages.items():
            allowed = ["argv", "timeout_seconds"]
            if stage in ("screen", "confirm"):
                allowed += ["pairs", "metric", "max_regression_pct" if stage == "screen" else "require_improvement_pct"]
            require_keys(spec, allowed, f"{name}/{stage}")
            argv = spec.get("argv")
            if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or "\0" in a for a in argv) or not argv[0]:
                raise CampaignError(f"{name}/{stage}: argv must be a nonempty string array")
            positive(spec.get("timeout_seconds"), f"{name}/{stage} timeout_seconds")
            if stage in ("screen", "confirm"):
                spec.setdefault("pairs", 2 if stage == "screen" else 4)
                positive(spec["pairs"], f"{name}/{stage} pairs", integer=True)
                if spec["pairs"] < (2 if stage == "screen" else 3):
                    raise CampaignError(f"{name}/{stage}: too few pairs")
                spec.setdefault("metric", "avg_hps")
                if not isinstance(spec["metric"], str) or not spec["metric"]:
                    raise CampaignError("metric must be a nonempty column name")
                gate = "max_regression_pct" if stage == "screen" else "require_improvement_pct"
                spec.setdefault(gate, 2.0 if stage == "screen" else 1.0)
                value = spec[gate]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise CampaignError(f"{gate} must be finite and nonnegative")
    return plan


def identities(paths):
    result = {}
    for filename in paths:
        path = Path(filename)
        if not path.is_file():
            raise CampaignError(f"required file is missing: {path}")
        result[str(path)] = lab.sha256_file(path)
    return result


def provenance(experiment):
    cwd = Path(experiment["cwd"])
    head, _ = lab.run_capture(["git", "rev-parse", "HEAD"], cwd=cwd)
    patch = ""
    if head:
        patch, error = lab.run_capture(["git", "diff", "--binary", "HEAD", "--"], cwd=cwd)
        if error:
            raise CampaignError(f"cannot capture source patch: {error}")
    return {"head": head, "tracked_patch": patch, "inputs": identities(experiment["inputs"])}


@contextlib.contextmanager
def exclusive_lock(path):
    """OS lock is released after termination; never delete a shared lock inode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0)
        if not handle.read(1):
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise CampaignError(f"another campaign owns {path}") from exc
        try:
            yield handle.fileno()
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def admission():
    """Do not measure or collect optional GPU telemetry during Gaming Mode."""
    if shutil.which("gpuq"):
        try:
            result = subprocess.run(["gpuq", "gaming", "check", "--quiet"], timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CampaignError(f"cannot check benchmark admission: {exc}") from exc
        if result.returncode:
            raise CampaignError(f"benchmark host unavailable: gpuq gaming check exited {result.returncode}; resume later")


def stop_child(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        # Also terminate descendants if the group leader exited first.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


@contextlib.contextmanager
def bounded_cleanup():
    # A second Ctrl-C must not abandon a benchmark while cleanup is in flight.
    previous = {sig: signal.signal(sig, signal.SIG_IGN) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def run_command(argv, cwd, directory, timeout, lock_fd):
    started = time.monotonic()
    result = {"argv": argv, "cwd": cwd, "started_at_utc": lab.utc_now()}
    process = None
    with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
        try:
            kwargs = {"start_new_session": True, "pass_fds": (lock_fd,)} if os.name != "nt" else {
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, shell=False, **kwargs)
            code = process.wait(timeout=timeout)
            result.update(status="completed" if code == 0 else "failed", exit_code=code)
        except subprocess.TimeoutExpired:
            result.update(status="timed_out", exit_code=124)
        except KeyboardInterrupt:
            result.update(status="interrupted", exit_code=130)
        except OSError as exc:
            result.update(status="failed", exit_code=127, error=str(exc))
        finally:
            if process is not None and result.get("status") in ("timed_out", "interrupted"):
                with bounded_cleanup():
                    stop_child(process)
    result.update(ended_at_utc=lab.utc_now(), duration_seconds=time.monotonic() - started)
    return result


def compare_stage(stage, spec, directory):
    results = directory / "results.tsv"
    try:
        paired = lab.load_paired_results(results, spec["metric"], "baseline", "candidate", spec["pairs"])
        if len(paired) != spec["pairs"]:
            raise CampaignError(f"expected exactly {spec['pairs']} pairs, got {len(paired)}")
        orders = {"first": 1, "second": 2, "1": 1, "2": 2}
        first_count = 0
        for pair in paired:
            baseline_order = orders.get(pair.baseline_order)
            candidate_order = orders.get(pair.candidate_order)
            if {baseline_order, candidate_order} != {1, 2}:
                raise CampaignError("each pair must record first/second (or 1/2) order")
            first_count += baseline_order == 1
        if abs(2 * first_count - len(paired)) > 1:
            raise CampaignError("baseline/candidate order must be balanced across pairs")
        comparison = lab.summarize_pairs(paired, spec["metric"], lab.DEFAULT_BOOTSTRAP_SAMPLES, lab.DEFAULT_BOOTSTRAP_SEED)
        _, rejected = lab.evaluate_gates(
            comparison, spec.get("max_regression_pct"), spec.get("require_improvement_pct"), "confidence")
        comparison["source"] = str(results)
        lab.atomic_write_json(directory / "comparison.json", comparison)
        return {"status": "rejected" if rejected else "completed",
                "reason": f"{stage} {rejected} gate not met" if rejected else f"{stage} gate passed",
                "results_sha256": lab.sha256_file(results), "comparison": comparison}
    except (lab.BenchctlError, OSError) as exc:
        raise CampaignError(f"invalid {stage} evidence: {exc}") from exc


def totals(state):
    return {stage: round(sum(attempt.get("duration_seconds", 0)
                            for entry in state["experiments"].values()
                            for attempt in entry["stages"].get(stage, [])), 3)
            for stage in STAGES}


def check_artifacts(experiment, entry):
    current = identities(experiment["artifacts"])
    if "artifacts" in entry and entry["artifacts"] != current:
        raise CampaignError(f"{experiment['id']}: benchmark artifacts changed; use a new campaign")
    entry["artifacts"] = current


def save_state(path, state):
    state["updated_at_utc"] = lab.utc_now()
    state["phase_seconds"] = totals(state)
    state["bookkeeping_seconds"] = round(sum(
        attempt.get("preflight_seconds", 0) + attempt.get("analysis_seconds", 0)
        for entry in state["experiments"].values()
        for attempts in entry["stages"].values() for attempt in attempts), 3)
    lab.atomic_write_json(path, state)


def summary(state):
    for name, entry in state["experiments"].items():
        print(f"{name}: {entry['status']} — {entry.get('reason', 'queued')}")
    print("Phase wall time: " + ", ".join(f"{name}={value:.3f}s" for name, value in totals(state).items()))


def run_campaign(plan_path, output_dir, resume=False, status_only=False):
    output_dir = output_dir.expanduser().resolve()
    state_path = output_dir / "campaign.json"
    if status_only:
        saved = read_json(state_path)
        if not isinstance(saved, dict) or saved.get("schema") != SCHEMA:
            raise CampaignError("invalid campaign state schema")
        summary(saved)
        return 0
    plan = load_plan(plan_path.expanduser().resolve())
    # Lock across campaigns, not just within this output directory.
    lock_path = Path.home() / ".cache" / "seine-benchctl" / "campaign.lock"
    with exclusive_lock(lock_path) as lock_fd:
        return execute_campaign(plan, output_dir, state_path, resume, lock_fd)


def execute_campaign(plan, output_dir, state_path, resume, lock_fd):
    identity = {"hostname": platform.node(), "system": platform.system(),
                "release": platform.release(), "machine": platform.machine(),
                "environment": lab.selected_environment(),
                "rustc": lab.tool_version("rustc"), "cargo": lab.tool_version("cargo"),
                "python": sys.version, "python_executable": sys.executable,
                "controller": identities([str(Path(__file__).resolve()), str(Path(lab.__file__).resolve())])}
    sources = {e["id"]: provenance(e) for e in plan["experiments"]}
    if resume:
        state = read_json(state_path)
        if state.get("schema") != SCHEMA or state.get("plan_digest") != digest(plan):
            raise CampaignError("campaign plan changed; use a new output directory")
        if state["host"] != identity or state["source_digests"] != {k: digest(v) for k, v in sources.items()}:
            raise CampaignError("host, toolchain, environment or source changed; start a new campaign")
        for experiment in plan["experiments"]:
            entry = state["experiments"][experiment["id"]]
            if "artifacts" in entry:
                check_artifacts(experiment, entry)
            for attempts in entry["stages"].values():
                for attempt in attempts:
                    if attempt["status"] == "running":
                        raise CampaignError(
                            "previous attempt ended without cleanup; inspect its logs and stop any "
                            "remaining workload before starting a new campaign")
                    if "results_sha256" in attempt:
                        result_path = Path(attempt["directory"]) / "results.tsv"
                        if not result_path.is_file() or lab.sha256_file(result_path) != attempt["results_sha256"]:
                            raise CampaignError("saved benchmark evidence changed; start a new campaign")
    else:
        if output_dir.exists() and any(output_dir.iterdir()):
            raise CampaignError("output directory is not empty; use --resume or a new directory")
        output_dir.mkdir(parents=True, exist_ok=True)
        state = {"schema": SCHEMA, "plan_digest": digest(plan), "plan": plan, "host": identity,
                 "source_digests": {k: digest(v) for k, v in sources.items()},
                 "started_at_utc": lab.utc_now(), "experiments": {}}
        for experiment in plan["experiments"]:
            name = experiment["id"]
            directory = output_dir / name
            directory.mkdir()
            lab.atomic_write_json(directory / "provenance.json", sources[name])
            inputs_dir = directory / "inputs"
            inputs_dir.mkdir()
            for index, filename in enumerate(experiment["inputs"]):
                shutil.copyfile(filename, inputs_dir / f"{index}-{Path(filename).name}")
            state["experiments"][name] = {"status": "pending", "stages": {}}
        save_state(state_path, state)
    previous = {}
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    for sig in (signal.SIGTERM, signal.SIGINT):
        previous[sig] = signal.signal(sig, interrupt)
    try:
        for experiment in plan["experiments"]:
            name = experiment["id"]
            entry = state["experiments"][name]
            if entry["status"] in TERMINAL:
                continue
            for stage in STAGES:
                if stage not in experiment["stages"]:
                    continue
                attempts = entry["stages"].setdefault(stage, [])
                if attempts and attempts[-1]["status"] == "completed":
                    continue
                if attempts and attempts[-1]["status"] in ("rejected", "failed", "timed_out"):
                    last = attempts[-1]
                    entry.update(status="rejected" if last["status"] == "rejected" else "failed",
                                 reason=last.get("reason", f"{stage} {last['status']}"))
                    save_state(state_path, state)
                    break
                admission()
                if digest(provenance(experiment)) != state["source_digests"][name]:
                    raise CampaignError(f"{name}: source changed during campaign")
                if stage != "build":
                    check_artifacts(experiment, entry)
                spec = experiment["stages"][stage]
                directory = output_dir / name / stage / f"attempt-{len(attempts) + 1}"
                directory.mkdir(parents=True)
                replacements = {"{stage_dir}": str(directory), "{experiment_dir}": str(output_dir / name),
                                "{python}": sys.executable, "{cwd}": experiment["cwd"]}
                argv = list(spec["argv"])
                for token, value in replacements.items():
                    argv = [arg.replace(token, value) for arg in argv]
                attempt = {"status": "running", "directory": str(directory), "argv": argv,
                           "started_at_utc": lab.utc_now(), "timeout_seconds": spec["timeout_seconds"]}
                attempts.append(attempt)
                entry.update(status="running", reason=stage)
                save_state(state_path, state)
                print(f"{name}: {stage} (budget {spec['timeout_seconds']}s); logs={directory}", flush=True)
                try:
                    if stage in ("screen", "confirm"):
                        capture_started = time.monotonic()
                        lab.atomic_write_json(directory / "preflight.json", lab.collect_preflight(
                            Path(experiment["cwd"]), [Path(p) for p in experiment["artifacts"]]))
                        attempt["preflight_seconds"] = time.monotonic() - capture_started
                    command_result = run_command(argv, experiment["cwd"], directory, spec["timeout_seconds"], lock_fd)
                    command_status = command_result.pop("status")
                    attempt.update(command_result, command_status=command_status,
                                   status="validating" if command_status == "completed" else command_status)
                except (OSError, lab.BenchctlError) as exc:
                    attempt.update(status="failed", exit_code=127, reason=f"capture/launch failed: {exc}")
                if attempt["status"] == "validating":
                    analysis_started = time.monotonic()
                    try:
                        check_artifacts(experiment, entry)
                        if digest(provenance(experiment)) != state["source_digests"][name]:
                            raise CampaignError("source changed during command")
                        if stage in ("screen", "confirm"):
                            admission()
                            attempt.update(compare_stage(stage, spec, directory))
                        else:
                            attempt["status"] = "completed"
                    except CampaignError as exc:
                        attempt.update(status="failed", reason=str(exc))
                    attempt["analysis_seconds"] = time.monotonic() - analysis_started
                status = attempt["status"]
                if status == "interrupted":
                    entry.update(status="interrupted", reason=f"{stage} interrupted; resume reruns this stage")
                elif status != "completed":
                    entry.update(status="rejected" if status == "rejected" else "failed",
                                 reason=attempt.get("reason", f"{stage} {status} (exit {attempt['exit_code']})"))
                elif stage == "confirm":
                    entry.update(status="accepted", reason="independent confirmation improvement gate passed")
                save_state(state_path, state)
                if status == "interrupted":
                    summary(state)
                    return 130
                if status != "completed":
                    break
            else:
                entry.update(status="accepted", reason="independent confirmation improvement gate passed")
                save_state(state_path, state)
    except KeyboardInterrupt:
        for entry in state["experiments"].values():
            for stage, attempts in entry["stages"].items():
                if attempts and attempts[-1]["status"] in ("running", "validating"):
                    attempts[-1].update(status="interrupted", exit_code=130, ended_at_utc=lab.utc_now())
                    entry.update(status="interrupted", reason=f"{stage} interrupted; resume reruns this stage")
        save_state(state_path, state)
        print("Campaign interrupted; resume with the same plan and output directory.", file=sys.stderr)
        return 130
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    summary(state)
    return 1 if any(e["status"] == "failed" for e in state["experiments"].values()) else 0
