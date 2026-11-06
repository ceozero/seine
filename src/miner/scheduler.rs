use crate::backend::PowAlgorithm;

/// Smallest BLAKE2b round reservation, across all lanes.
const BLAKE2B_MIN_ROUND_SPAN: u64 = 1 << 46;

#[derive(Debug, Clone, Copy)]
pub struct NonceReservation {
    pub start_nonce: u64,
    pub max_iters_per_lane: u64,
    pub reserved_span: u64,
}

#[derive(Debug, Clone)]
pub struct NonceScheduler {
    next_start_nonce: u64,
    max_iters_per_lane: u64,
}

impl NonceScheduler {
    pub fn new(start_nonce: u64, max_iters_per_lane: u64) -> Self {
        Self {
            next_start_nonce: start_nonce,
            max_iters_per_lane: max_iters_per_lane.max(1),
        }
    }

    pub fn reserve(&mut self, total_lanes: u64) -> NonceReservation {
        self.reserve_iters(total_lanes, self.max_iters_per_lane)
    }

    /// Like `reserve`, sized for the round's proof of work: a BLAKE2b round
    /// reserves at least `BLAKE2B_MIN_ROUND_SPAN` across all lanes.
    pub fn reserve_for(&mut self, total_lanes: u64, pow: PowAlgorithm) -> NonceReservation {
        match pow {
            PowAlgorithm::Argon2id => self.reserve(total_lanes),
            PowAlgorithm::Blake2b512 => {
                let per_lane = BLAKE2B_MIN_ROUND_SPAN.div_ceil(total_lanes.max(1));
                self.reserve_iters(total_lanes, self.max_iters_per_lane.max(per_lane))
            }
        }
    }

    fn reserve_iters(&mut self, total_lanes: u64, max_iters_per_lane: u64) -> NonceReservation {
        let lanes = total_lanes.max(1);
        let reserved_span = lanes.saturating_mul(max_iters_per_lane).max(lanes);
        let reservation = NonceReservation {
            start_nonce: self.next_start_nonce,
            max_iters_per_lane,
            reserved_span,
        };
        self.next_start_nonce = self.next_start_nonce.wrapping_add(reserved_span);
        reservation
    }

    pub fn consume_additional_span(&mut self, span: u64) {
        if span == 0 {
            return;
        }
        self.next_start_nonce = self.next_start_nonce.wrapping_add(span);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blake2b_rounds_reserve_gpu_sized_spans_without_overlap() {
        let mut scheduler = NonceScheduler::new(10, 1 << 36);
        let argon2 = scheduler.reserve_for(1, PowAlgorithm::Argon2id);
        assert_eq!(argon2.reserved_span, 1 << 36);
        let blake2b = scheduler.reserve_for(1, PowAlgorithm::Blake2b512);
        assert_eq!(blake2b.start_nonce, 10 + (1 << 36));
        assert_eq!(blake2b.reserved_span, BLAKE2B_MIN_ROUND_SPAN);
        assert_eq!(blake2b.max_iters_per_lane, BLAKE2B_MIN_ROUND_SPAN);
        let many_lanes = scheduler.reserve_for(16, PowAlgorithm::Blake2b512);
        assert_eq!(
            many_lanes.start_nonce,
            blake2b.start_nonce + BLAKE2B_MIN_ROUND_SPAN
        );
        assert_eq!(many_lanes.max_iters_per_lane, BLAKE2B_MIN_ROUND_SPAN / 16);
        // A larger configured span is kept.
        let mut wide = NonceScheduler::new(0, 1 << 50);
        assert_eq!(
            wide.reserve_for(1, PowAlgorithm::Blake2b512).reserved_span,
            1 << 50
        );
    }

    #[test]
    fn reservation_is_deterministic_and_non_overlapping() {
        let mut scheduler = NonceScheduler::new(100, 10);
        let first = scheduler.reserve(4);
        let second = scheduler.reserve(4);
        assert_eq!(first.start_nonce, 100);
        assert_eq!(first.max_iters_per_lane, 10);
        assert_eq!(first.reserved_span, 40);
        assert_eq!(second.start_nonce, 140);
    }

    #[test]
    fn reservation_stays_non_overlapping_when_lane_count_changes() {
        let mut scheduler = NonceScheduler::new(50, 10);
        let first = scheduler.reserve(4);
        let second = scheduler.reserve(1);
        let third = scheduler.reserve(8);

        assert_eq!(first.start_nonce, 50);
        assert_eq!(second.start_nonce, 90);
        assert_eq!(third.start_nonce, 100);
    }

    #[test]
    fn additional_span_consumption_skips_retry_windows() {
        let mut scheduler = NonceScheduler::new(1_000, 10);
        let first = scheduler.reserve(4);
        scheduler.consume_additional_span(40);
        let second = scheduler.reserve(4);

        assert_eq!(first.start_nonce, 1_000);
        assert_eq!(second.start_nonce, 1_080);
    }
}
