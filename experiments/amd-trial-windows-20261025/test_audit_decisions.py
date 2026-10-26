import unittest

from audit_decisions import audit


def line(message, samples):
    raw = ','.join(f'{hashes}/{seconds}' for hashes, seconds in samples)
    return f'1.0s INFO MINER cpu-autotune | {message} (rates | raw_hashes_secs=[{raw}] H/s)'


class DecisionTests(unittest.TestCase):
    def test_variable_duration_promotions_and_losses_are_recomputed(self):
        triple = [(320, 10), (440, 11), (384, 12)]
        log = line('confirmed faster avx2 path in two comparisons', triple * 2)
        log += '\n' + line('keeping current kernel; no confirmed gain', [(960, 30)] * 3)
        result = audit(log, short_trials=True)
        self.assertEqual(result['promotion_count'], 1)
        self.assertEqual(result['decision_count'], 2)
        self.assertEqual(result['early_samples'], 6)

    def test_a_single_win_cannot_be_reported_as_two_confirmations(self):
        triple = [(320, 10), (440, 11), (384, 12)]
        with self.assertRaises(AssertionError):
            audit(line('confirmed faster avx2 path in two comparisons', triple), short_trials=True)

    def test_drift_and_nonrepeated_gain_cannot_be_promoted(self):
        first = [(320, 10), (400, 10), (320, 10)]
        for second in ([(320, 10), (400, 10), (400, 10)], [(320, 10)] * 3):
            with self.subTest(second=second), self.assertRaises(AssertionError):
                audit(line('confirmed faster avx2 path in two comparisons', first + second),
                      short_trials=True)
        result = audit(line('keeping avx512; gain did not repeat', first + [(320, 10)] * 3),
                       short_trials=True)
        self.assertEqual(result['promotion_count'], 0)

    def test_short_samples_are_not_allowed_in_control_or_below_thresholds(self):
        for short, samples in ((False, [(320, 10)] * 3),
                               (True, [(255, 10)] * 3), (True, [(400, 9)] * 3)):
            with self.subTest(short=short, samples=samples), self.assertRaises(AssertionError):
                audit(line('keeping current kernel; no confirmed gain', samples), short_trials=short)

    def test_rounded_rates_cannot_substitute_for_raw_counts(self):
        with self.assertRaises(AssertionError):
            audit('INFO cpu-autotune | confirmed faster avx2 path in two comparisons (32 / 40 H/s)',
                  short_trials=True)


if __name__ == '__main__':
    unittest.main()
