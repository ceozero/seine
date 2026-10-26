#!/usr/bin/env python3
"""Render the published finite-window records; no interpolation or power estimate."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
records = json.loads((root / 'benchmark-records.json').read_text())['records']
fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
for ax, phase, title in zip(axes, ('cold_discovery', 'cached_restart'),
                           ('Cold discovery · 900 s', 'Cached restart · 180 s')):
    selected = [r for r in records if r['phase'] == phase]
    for i, row in enumerate(selected):
        ax.bar(i, row['hps'], width=0.6, color=('#b3b3b3', '#aaff00')[i], edgecolor='black')
        rates = [r['completed_hps_lower_bound'] for r in row['observations']]
        ax.scatter([i - .08, i + .08], rates, s=24, color='black', zorder=3)
        ax.text(i, max(rates) + .6, f"{row['hps']:.2f}", ha='center', fontsize=11)
    ax.set_xticks([0, 1], ['Control', 'Streaming eligible'])
    ax.set_title(title)
    ax.set_ylim(0, 35)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', alpha=.2)
    ax.set_axisbelow(True)
axes[0].set_ylabel('Completed-hash lower bound (H/s)')
fig.suptitle('AMD EPYC 9R14 · AWS c7a.8xlarge', fontsize=15)
fig.text(.5, .075, 'Automatic count and kernel · 24-worker ceiling · explicit 2 MiB pages', ha='center', fontsize=10)
fig.text(.5, .03, 'Two runs per bar; dots are individual runs. VM session, startup through shutdown; power unmeasured.', ha='center', fontsize=9)
fig.tight_layout(rect=(0, .12, 1, .92))
for extension in ('png', 'svg'):
    fig.savefig(root / ('productive.' + extension), dpi=160)
