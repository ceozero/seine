#!/usr/bin/env python3
"""Render real controller output with synthetic data; never mines or probes GPUs."""
import argparse
import contextlib
import hashlib
import html
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock

import bench_campaign as campaign
import benchctl

ROOT = Path(__file__).resolve().parents[1]


def stage(extra=""):
    return {"argv": ["{python}", "-c", "from pathlib import Path\n" + extra], "timeout_seconds": 10}


def measurement(pairs, rate):
    rows = "variant\tpair\torder\tavg_hps\n"
    for pair in range(pairs):
        rows += f"baseline\t{pair}\t{'first' if pair % 2 == 0 else 'second'}\t100\n"
        rows += f"candidate\t{pair}\t{'second' if pair % 2 == 0 else 'first'}\t{rate}\n"
    return {**stage(f"Path('{{stage_dir}}/results.tsv').write_text({rows!r})"), "pairs": pairs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/showcases/benchctl-campaign")
    args = parser.parse_args()
    cards = []
    with tempfile.TemporaryDirectory(prefix="seine-campaign-demo-") as temp:
        root = Path(temp)
        (root / "fixture").write_text("Synthetic test artifact; not a miner.")
        experiment = {"id": "example", "hypothesis": "Synthetic throughput improvement",
                      "cwd": ".", "inputs": ["fixture"], "artifacts": ["fixture"],
                      "stages": {"build": stage(), "correctness": stage(),
                                 "screen": measurement(2, 110), "confirm": measurement(4, 110)}}
        def run(title, note, spec, *, interrupt=False, resume=False):
            plan = root / "plan.json"
            plan.write_text(json.dumps({"schema": campaign.SCHEMA, "experiments": spec}))
            output = root / ("interrupted" if interrupt or resume else f"run-{len(cards)}")
            captured = io.StringIO()
            real_run = campaign.run_command
            def interrupted(argv, cwd, directory, timeout, lock_fd):
                if directory.parent.name == "confirm":
                    raise KeyboardInterrupt
                return real_run(argv, cwd, directory, timeout, lock_fd)
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                try:
                    if interrupt:
                        with mock.patch("bench_campaign.run_command", side_effect=interrupted):
                            code = benchctl.main(["campaign", str(plan), "--output-dir", str(output)])
                    else:
                        code = benchctl.main(["campaign", str(plan), "--output-dir", str(output)] + (["--resume"] if resume else []))
                except campaign.CampaignError as exc:
                    code = 2
                    captured.write(str(exc))
            text = captured.getvalue().replace(str(root), "<fixture>")
            cards.append((title, note, code, text))
        # Host data is explicitly a fixture. Execute commands, gates, persistence,
        # timeout cleanup and CLI reporting through the actual controller.
        with mock.patch("bench_campaign.lab.collect_preflight", return_value={"fixture": True}), \
             mock.patch("bench_campaign.lab.tool_version", return_value="fixture-toolchain"), \
             mock.patch("bench_campaign.admission"), \
             mock.patch("bench_campaign.Path.home", return_value=root):
            run("Empty queue", "Invalid plans stop before any command runs.", [])
            run("Accepted", "Independent confirmation clears the configured improvement bound.", [experiment])
            rejected = json.loads(json.dumps(experiment))
            rejected["stages"]["screen"] = measurement(2, 90)
            run("Screen rejected", "Confirmation is skipped; no extra benchmark budget is spent.", [rejected])
            tied = json.loads(json.dumps(experiment))
            tied["stages"]["confirm"] = measurement(4, 100)
            run("Confirmation inconclusive", "A valid run without the required gain is rejected, not retried.", [tied])
            failed = json.loads(json.dumps(experiment))
            failed["stages"]["correctness"] = stage("raise SystemExit(7)")
            run("Correctness failed", "Measurement stages are skipped after a correctness failure.", [failed])
            timed = json.loads(json.dumps(experiment))
            timed["stages"]["build"] = stage("import time; time.sleep(10)")
            timed["stages"]["build"]["timeout_seconds"] = 0.05
            run("Budget exhausted", "Timeout is a failed experiment, not a performance rejection.", [timed])
            run("Interrupted", "Fixture interruption during confirmation retains completed stages.", [experiment], interrupt=True)
            run("Resumed", "Only confirmation runs again, in attempt-2; prior work is preserved.", [experiment], resume=True)
    revision = subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, text=True).strip()
    source_hash = hashlib.sha256(b"".join((ROOT / "scripts" / name).read_bytes()
                                       for name in ("benchctl.py", "bench_campaign.py", "showcase_bench_campaign.py"))).hexdigest()[:16]
    sections = "\n".join(
        f'<section><div class="heading"><h2>{html.escape(title)}</h2><span>exit {code}</span></div>'
        f'<p>{html.escape(note)}</p><pre>{html.escape(output.strip())}</pre></section>'
        for title, note, code, output in cards)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Seine benchmark campaigns · workflow showcase</title>
<style>
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#152b34;background:#f3f5f4}
*{box-sizing:border-box}body{margin:0}main{max-width:1080px;margin:auto;padding:44px 28px 60px}
.eyebrow{font:600 12px ui-monospace,monospace;text-transform:uppercase;letter-spacing:.13em;color:#34625a}
h1{font-size:clamp(30px,5vw,48px);line-height:1.08;letter-spacing:-.035em;margin:14px 0}
.lead{font-size:18px;max-width:760px;line-height:1.6;color:#42565e}
.meta{font:12px/1.7 ui-monospace,monospace;overflow-wrap:anywhere;color:#4f6269}
.notice{border-left:3px solid #517b64;padding:12px 16px;background:#e5ede7;margin:24px 0 30px;line-height:1.6}
section{background:white;border:1px solid #d8e0dc;margin:18px 0;padding:22px;border-radius:8px}
.heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.heading h2{font-size:20px;margin:0}
.heading span{font:12px ui-monospace,monospace;white-space:nowrap;background:#eef2ef;padding:7px 9px;border-radius:4px}
p{line-height:1.6}section p{color:#465c64;margin:12px 0}
pre{background:#142a32;color:#e4eee9;border-radius:5px;padding:16px;font:12px/1.75 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin-bottom:0}
footer{margin-top:30px;font-size:14px;color:#465c64}code{font-family:ui-monospace,monospace}
@media(max-width:600px){main{padding:28px 16px}section{padding:16px}.lead{font-size:16px}pre{padding:12px;font-size:11px}.heading h2{font-size:18px}}
</style><main><div class="eyebrow">Seine / Engineering tools</div><h1>From experiment<br>to measured decision.</h1>
<p class="lead">A serial queue that builds once, screens cheaply, confirms separately, and remembers completed work.</p>
<div class="meta">BASE REVISION: {{REVISION}} · CONTROLLER SOURCE: {{SOURCE_HASH}}</div>
<div class="notice"><strong>Synthetic workflow demonstration.</strong> These transcripts come from the real campaign CLI with fixture data and fixture host capture. No mining hardware was used, and the rates are not performance evidence. Phase-start lines show active work; skipped stages have no launch line. This CLI has no disabled controls.</div>
SECTIONS
<footer>Regenerate: <code>python3 scripts/showcase_bench_campaign.py</code><br>Serve from the repository: <code>python3 -m http.server 8876 --directory docs/showcases</code><br>Open: <code>http://localhost:8876/benchctl-campaign/</code></footer></main></html>'''
    page = page.replace("{{REVISION}}", html.escape(revision)).replace("{{SOURCE_HASH}}", source_hash).replace("SECTIONS", sections)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "index.html").write_text(page, encoding="utf-8")
    print(args.output_dir / "index.html")


if __name__ == "__main__":
    main()
