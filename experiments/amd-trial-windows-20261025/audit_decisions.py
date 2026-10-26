#!/usr/bin/python3
"""Recompute every instrumented kernel decision from raw hashes and durations."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re


def comparison(samples):
    a, b, c = samples
    if abs((c[0] / c[1]) / (a[0] / a[1]) - 1) > 0.05:
        return 'inconclusive'
    baseline = (a[0] + c[0]) / (a[1] + c[1])
    quantization = sum(1 / sample[1] for sample in samples)
    return 'gain' if b[0] / b[1] > baseline * 1.02 + quantization else 'no_gain'


def audit(text, *, short_trials):
    decisions = []
    durations = Counter()
    for lineno, line in enumerate(text.splitlines(), 1):
        if 'cpu-autotune |' not in line:
            continue
        message = line.split('cpu-autotune |', 1)[1].strip()
        if message.startswith('confirmed faster '):
            expected = ['gain', 'gain']
        elif message.startswith('keeping current kernel; no confirmed gain'):
            expected = ['no_gain']
        elif message.startswith('keeping current kernel; baseline drifted'):
            expected = ['inconclusive']
        elif message.startswith('keeping ') and '; gain did not repeat' in message:
            expected = ['gain', 'no_gain']
        elif message.startswith('keeping ') and '; confirmation was noisy' in message:
            expected = ['gain', 'inconclusive']
        else:
            continue
        raw = re.search(r'raw_hashes_secs=\[([0-9/,]+)\]', message)
        assert raw, f'line {lineno}: missing exact samples'
        samples = [tuple(map(int, item.split('/'))) for item in raw[1].split(',')]
        assert len(samples) == 3 * len(expected), f'line {lineno}: incomplete comparison'
        for hashes, seconds in samples:
            assert ((seconds >= 30 and hashes >= 32) or
                    (short_trials and seconds >= 10 and hashes >= 256)), \
                f'line {lineno}: sample did not satisfy its policy'
            durations[seconds] += 1
        outcomes = [comparison(samples[offset:offset + 3])
                    for offset in range(0, len(samples), 3)]
        assert outcomes == expected, f'line {lineno}: logged decision disagrees with raw samples'
        decisions.append({'line': lineno, 'samples_hashes_seconds': samples,
                          'outcomes': outcomes, 'promoted': expected == ['gain', 'gain']})
    return {'sample_policy': 'turin-10s-256-v1' if short_trials else 'original-30s-32',
            'decisions': decisions, 'decision_count': len(decisions),
            'promotion_count': sum(row['promoted'] for row in decisions),
            'sample_duration_seconds_histogram': dict(sorted(durations.items())),
            'early_samples': sum(count for seconds, count in durations.items() if seconds < 30)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--short-trials', action='store_true')
    args = parser.parse_args()
    result = audit(args.log.read_text(), short_trials=args.short_trials)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'decisions'}, indent=2))
