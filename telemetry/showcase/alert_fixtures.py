"""Actual webhook formatter output with synthetic aggregates; never sends messages."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alerts import evaluate, format_message, issue


def messages():
    now = 1792965060
    quality, _ = evaluate({'quality': {'versions': [
        {'version': 'v0.2.24', 'sustained_inventory_only_installations': 99},
        {'version': 'v0.2.26', 'sustained_inventory_only_installations': 5},
    ]}})
    cases = {
        'legacy': ('FIRING', quality[0]),
        'warning': ('FIRING', quality[1]),
        'reminder': ('REMINDER', quality[0]),
        'cleared': ('CLEARED', quality[0]),
        'critical': ('FIRING', issue('infrastructure', 'fixture', 'Collector infrastructure check failed.')),
        'setup': ('SETUP TEST', issue('setup', 'fixture', 'Delivery test only; this is not an incident.')),
        'old-state': ('CLEARED', issue('quality', 'fixture', 'Previously reported missing samples.')),
    }
    return {name: format_message(transition, record, now)
            for name, (transition, record) in cases.items()}
