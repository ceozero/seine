#!/usr/bin/env python3
"""Render audited productive windows and coarse first-confirmation observations."""
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
records = json.loads((root / 'benchmark-records.json').read_text())['records']
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
for ax, phase, title in zip(axes[:2], ('cold_discovery', 'cached_restart'),
                           ('Cold discovery · 1,200 s', 'Cached restart · 180 s')):
    selected = [r for r in records if r['phase'] == phase]
    for i, row in enumerate(selected):
        ax.bar(i, row['hps'], width=.6, color=('#b3b3b3', '#aaff00')[i], edgecolor='black')
        rates = [r['completed_hps_lower_bound'] for r in row['observations']]
        ax.scatter([i - .15, i - .05, i + .05, i + .15], rates, s=20, color='black', zorder=3)
        ax.text(i, max(rates) + 1.2, f"{row['hps']:.2f}", ha='center')
    ax.set_ylim(0, 80)
    ax.set_title(title)
    ax.set_ylabel('Completed-hash lower bound (H/s)')
for i, row in enumerate(r for r in records if r['phase'] == 'cold_discovery'):
    values = [r['first_streaming_confirmation_observed_seconds'] for r in row['observations']]
    assert all(v is not None for v in values)
    median = statistics.median(values)
    axes[2].bar(i, median, width=.6, color=('#b3b3b3', '#aaff00')[i], edgecolor='black')
    axes[2].scatter([i - .15, i - .05, i + .05, i + .15], values, s=20, color='black', zorder=3)
    axes[2].text(i, max(values) + 8, f'{median:.0f} s', ha='center')
axes[2].set_ylim(0, 350)
axes[2].set_title('First streaming confirmation')
axes[2].set_ylabel('First observed seconds · lower is faster')
for ax in axes:
    ax.set_xticks([0, 1], ['Control', 'Streaming first'])
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', alpha=.2)
    ax.set_axisbelow(True)
fig.suptitle('AMD EPYC 9355P · automatic challenger ordering', fontsize=15)
fig.text(.5, .075, 'Balanced profile · automatic count/kernel · 64 logical CPUs · explicit 2 MiB pages · stock 280 W cap', ha='center', fontsize=10)
fig.text(.5, .03, 'Four runs per bar; dots are individual runs. Startup through shutdown. Timing sampled every 10 s. Power unmeasured.', ha='center', fontsize=9)
fig.tight_layout(rect=(0, .12, 1, .92))
for extension in ('png', 'svg'):
    fig.savefig(root / ('productive.' + extension), dpi=160)
