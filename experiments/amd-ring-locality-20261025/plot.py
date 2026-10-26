#!/usr/bin/env python3
"""Render screening deltas without presenting them as confirmed improvements."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
results = json.loads((root / 'results.json').read_text())
fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
screens = [v for v in results['comparisons'] if v['phase'] == 'screen']
maximum = max(abs(d) for v in screens for d in v['summary']['paired_deltas_pct'])
limit = max(2, maximum * 1.4)
for ax, workers in zip(axes, (32, 64)):
    values = [v for v in screens if v['workers'] == workers]
    for i, value in enumerate(values):
        delta = value['summary']['paired_geometric_delta_pct']
        ax.bar(i, delta, color='#aaff00', edgecolor='black', width=.6)
        pairs = value['summary']['paired_deltas_pct']
        ax.scatter([i - .08, i + .08], pairs, color='black', s=25, zorder=3)
        ax.annotate(f'{delta:+.2f}%', (i, delta), xytext=(0, 9 if delta >= 0 else -17),
                    textcoords='offset points', ha='center')
    ax.set_xticks([0, 1], ['32-block ring', '16-block ring'])
    ax.set_title(f'{workers} workers')
    ax.set_ylim(-limit, limit)
    ax.axhline(0, color='black', linewidth=1)
    ax.grid(axis='y', alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
axes[0].set_ylabel('Completed backend H/s change vs 64-block ring (%)')
fig.suptitle('EPYC 9355P · streaming-buffer screen · experimental', fontsize=14)
fig.text(.5, .065, 'Two opposite-order pairs; dots show each pair. 15 s warmup + 2 × 15 s measured rounds.', ha='center', fontsize=9)
fig.text(.5, .025, 'Explicit streaming · 2 MiB pages · stock 280 W cap · power unmeasured · screening is not confirmation', ha='center', fontsize=8)
fig.tight_layout(rect=(0, .12, 1, .93))
for extension in ('png', 'svg'):
    fig.savefig(root / ('screen.' + extension), dpi=160)
