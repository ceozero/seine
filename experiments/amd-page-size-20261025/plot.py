#!/usr/bin/env python3
"""Plot only completed, verified page-size measurements."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
data = json.loads((root / 'benchmark-records.json').read_text())
assert data['status'] == 'COMPLETE', 'Unavailable experiments have no numeric plot'
records = data['records']
assert [r['role'] for r in records] == ['baseline', 'candidate']
fig, axes = plt.subplots(1, 3, figsize=(12, 4.8))
panels = [('hps', 'Completed hashes / second', 'completed_hashes', 'invocation_seconds'),
          ('package_watts', 'Measured CPU package watts', 'package_joules', 'invocation_seconds'),
          ('package_joules_per_hash', 'Package joules / hash · lower is better', 'package_joules', 'completed_hashes')]
for ax, (metric, title, numerator, denominator) in zip(axes, panels):
    all_values = []
    for i, row in enumerate(records):
        values = [v[numerator] / v[denominator] for v in row['observations']]
        all_values.extend(values)
        ax.bar(i, row[metric], width=.6, color=('#b3b3b3', '#aaff00')[i], edgecolor='black')
        ax.scatter([i - .15, i - .05, i + .05, i + .15], values, s=20, color='black', zorder=3)
        ax.annotate(f'{row[metric]:.2f}', (i, max(values)), xytext=(0, 7),
                    textcoords='offset points', ha='center')
    ax.set_title(title, fontsize=11)
    ax.set_xticks([0, 1], ['2 MiB pages', '1 GiB pages'])
    ax.set_ylim(0, max(all_values) * 1.2)
    ax.grid(axis='y', alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
fig.suptitle('EPYC 9355P · same binary · explicit page-size comparison', fontsize=14)
fig.text(.5, .075, '64 streaming workers · 12 × DDR5-4800 · stock 280 W cap · four alternating pairs · 120 s windows', ha='center', fontsize=9)
fig.text(.5, .03, 'Whole invocation including allocation/fences/teardown; pool setup excluded. CPU package energy excludes unmeasured DRAM and wall losses.', ha='center', fontsize=8)
fig.tight_layout(rect=(0, .12, 1, .93))
for extension in ('png', 'svg'):
    fig.savefig(root / ('page-size.' + extension), dpi=160)
