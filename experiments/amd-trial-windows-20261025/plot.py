#!/usr/bin/env python3
"""Plot complete short-sample results; never produce figures from partial windows."""
import argparse
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    rows = json.loads((args.data_dir / 'benchmark-records.json').read_text())['records']
    result = json.loads((args.data_dir / 'results.json').read_text())
    assert result['experiment'] == 'amd-trial-windows-20261025'
    assert len(result['runs']) == 16 and len(rows) == 4
    assert all(row['campaign'] == result['experiment'] and row['repetitions'] == 4 for row in rows)
    assert all([item['pair'] for item in row['observations']] == [1, 2, 3, 4] for row in rows)
    assert result['resource_validation']['status'] == 'COMPLETE_WITH_MEASURED_RECLAIM'
    colors = ('#b3b3b3', '#aaff00')
    labels = ['Control', 'Short samples']
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, phase, key, title in zip(axes[0], ('cold_discovery', 'cached_restart'),
            ('cold', 'warm'), ('Cold discovery · 1,200 s', 'Own-cache restart · 180 s')):
        selected = [next(row for row in rows if row['phase'] == phase and row['role'] == role)
                    for role in ('control', 'candidate')]
        maximum = max(item['completed_hps_lower_bound'] for row in selected for item in row['observations'])
        for index, row in enumerate(selected):
            rates = [item['completed_hps_lower_bound'] for item in row['observations']]
            ax.bar(index, row['hps'], width=.6, color=colors[index], edgecolor='black')
            ax.scatter([index + offset for offset in (-.15, -.05, .05, .15)], rates,
                       s=20, color='black', zorder=3)
            ax.text(index, max(rates) + maximum * .025, f"{row['hps']:.2f}", ha='center')
        comparison = result[key]['comparison']
        gain = comparison['paired_geometric_delta_pct']
        low, high = comparison['paired_geometric_delta_ci95_pct']
        ax.set_title(title + f'\nPaired {gain:+.2f}% · interval [{low:+.2f}, {high:+.2f}]%')
        ax.set_ylabel('Completed-hash lower bound (H/s)')
        ax.set_ylim(0, maximum * 1.17)
        ax.set_xticks([0, 1], labels)
    ax = axes[1, 0]
    cold = [next(row for row in rows if row['phase'] == 'cold_discovery' and row['role'] == role)
            for role in ('control', 'candidate')]
    observed = [item['first_streaming_confirmation_observed_seconds'] for row in cold
                for item in row['observations'] if item['first_streaming_confirmation_observed_seconds'] is not None]
    maximum = max(observed, default=1)
    for index, row in enumerate(cold):
        values = [item['first_streaming_confirmation_observed_seconds'] for item in row['observations']
                  if item['first_streaming_confirmation_observed_seconds'] is not None]
        if values:
            median = statistics.median(values)
            ax.bar(index, median, width=.6, color=colors[index], edgecolor='black')
            ax.scatter([index] * len(values), values, s=20, color='black', zorder=3)
            ax.text(index, max(values) + maximum * .04, f'{median:.0f} s', ha='center')
        if len(values) != 4:
            ax.text(index, maximum * 1.12, f'{4 - len(values)} not observed', ha='center', fontsize=9)
    ax.set_ylim(0, maximum * 1.3)
    ax.set_title('First streaming confirmation · cold runs')
    ax.set_ylabel('Observed seconds · 10 s snapshot resolution')
    ax.set_xticks([0, 1], labels)
    ax = axes[1, 1]
    histograms = []
    for role in ('control', 'candidate'):
        histogram = {}
        for label, run in result['runs'].items():
            if run['binary'] != role:
                continue
            for seconds, count in result['raw_decision_audit'][label]['sample_duration_seconds_histogram'].items():
                histogram[int(seconds)] = histogram.get(int(seconds), 0) + count
        histograms.append(histogram)
    durations = sorted(set().union(*histograms))
    for index, histogram in enumerate(histograms):
        ax.bar([position + (-.19 if index == 0 else .19) for position in range(len(durations))],
               [histogram.get(seconds, 0) for seconds in durations], width=.38,
               color=colors[index], edgecolor='black', label=labels[index])
    ax.set_xticks(range(len(durations)), [str(seconds) for seconds in durations])
    ax.set_xlabel('Sample duration (seconds)')
    ax.set_ylabel('Samples in completed logged comparisons')
    ax.set_title('Raw sample audit · all cold and cached runs')
    ax.legend(frameon=False)
    for ax in axes.flat:
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    fig.suptitle('AMD EPYC 9355P · high-count tuning sample windows', fontsize=15)
    fig.text(.5, .055, 'Balanced profile · automatic count/kernel · 64 logical CPUs · explicit 2 MiB pages · stock 280 W cap',
             ha='center', fontsize=9)
    fig.text(.5, .025, 'Four paired runs per phase. Startup through shutdown. Package and wall power unmeasured.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .1, 1, .94))
    for extension in ('png', 'svg'):
        fig.savefig(args.data_dir / ('productive.' + extension), dpi=160)


if __name__ == '__main__':
    main()
