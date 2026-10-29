//! Register-resident full-width AVX-512 compression for `avx512-stream`.
//!
//! The 1 KiB block lives in sixteen zmm registers for the whole permutation:
//! `r{k}` holds words `8k..8k+8`, so row `i` is `r{2i}` (words 0-7) and
//! `r{2i+1}` (words 8-15). Row rounds process two rows per vector set; column
//! rounds process two columns per set, gathered with two-source permutes. The
//! pre-round value is written to `dst` once and XORed back at the end. Every
//! step is unrolled over named locals so the block never spills to the stack.
//! Every entry point requires AVX-512F.

use std::arch::x86_64::*;

use super::{prefetch_pow_block, reference_index, PowBlock};

#[inline(always)]
unsafe fn blamka(x: __m512i, y: __m512i) -> __m512i {
    let product = _mm512_mul_epu32(x, y);
    _mm512_add_epi64(_mm512_add_epi64(x, y), _mm512_add_epi64(product, product))
}

/// One BLAKE2b-style round on two independent 4x4 word matrices (lanes 0-3 and 4-7).
macro_rules! round {
    ($a:ident, $b:ident, $c:ident, $d:ident) => {
        $a = blamka($a, $b);
        $d = _mm512_ror_epi64::<32>(_mm512_xor_si512($d, $a));
        $c = blamka($c, $d);
        $b = _mm512_ror_epi64::<24>(_mm512_xor_si512($b, $c));
        $a = blamka($a, $b);
        $d = _mm512_ror_epi64::<16>(_mm512_xor_si512($d, $a));
        $c = blamka($c, $d);
        $b = _mm512_ror_epi64::<63>(_mm512_xor_si512($b, $c));
        $b = _mm512_permutex_epi64::<0x39>($b);
        $c = _mm512_permutex_epi64::<0x4e>($c);
        $d = _mm512_permutex_epi64::<0x93>($d);
        $a = blamka($a, $b);
        $d = _mm512_ror_epi64::<32>(_mm512_xor_si512($d, $a));
        $c = blamka($c, $d);
        $b = _mm512_ror_epi64::<24>(_mm512_xor_si512($b, $c));
        $a = blamka($a, $b);
        $d = _mm512_ror_epi64::<16>(_mm512_xor_si512($d, $a));
        $c = blamka($c, $d);
        $b = _mm512_ror_epi64::<63>(_mm512_xor_si512($b, $c));
        $b = _mm512_permutex_epi64::<0x93>($b);
        $c = _mm512_permutex_epi64::<0x4e>($c);
        $d = _mm512_permutex_epi64::<0x39>($d);
    };
}

/// Rows `i` (registers `$x0`, `$x1`) and `i + 1` (`$y0`, `$y1`).
macro_rules! row_pair {
    ($x0:ident, $x1:ident, $y0:ident, $y1:ident) => {{
        let mut a = _mm512_shuffle_i64x2::<0x44>($x0, $y0);
        let mut b = _mm512_shuffle_i64x2::<0xee>($x0, $y0);
        let mut c = _mm512_shuffle_i64x2::<0x44>($x1, $y1);
        let mut d = _mm512_shuffle_i64x2::<0xee>($x1, $y1);
        round!(a, b, c, d);
        $x0 = _mm512_shuffle_i64x2::<0x44>(a, b);
        $y0 = _mm512_shuffle_i64x2::<0xee>(a, b);
        $x1 = _mm512_shuffle_i64x2::<0x44>(c, d);
        $y1 = _mm512_shuffle_i64x2::<0xee>(c, d);
    }};
}

/// Four columns of one register half: rows are `$r0`..`$r7` (that half of each row).
/// Columns 0,1 use 128-bit lanes 0,1; columns 2,3 use lanes 2,3.
macro_rules! column_quad {
    ($r0:ident, $r1:ident, $r2:ident, $r3:ident, $r4:ident, $r5:ident, $r6:ident, $r7:ident, $low:ident, $high:ident, $even:ident, $odd:ident) => {{
        let mut a0 = _mm512_permutex2var_epi64($r0, $low, $r1);
        let mut b0 = _mm512_permutex2var_epi64($r2, $low, $r3);
        let mut c0 = _mm512_permutex2var_epi64($r4, $low, $r5);
        let mut d0 = _mm512_permutex2var_epi64($r6, $low, $r7);
        let mut a1 = _mm512_permutex2var_epi64($r0, $high, $r1);
        let mut b1 = _mm512_permutex2var_epi64($r2, $high, $r3);
        let mut c1 = _mm512_permutex2var_epi64($r4, $high, $r5);
        let mut d1 = _mm512_permutex2var_epi64($r6, $high, $r7);
        round!(a0, b0, c0, d0);
        round!(a1, b1, c1, d1);
        $r0 = _mm512_permutex2var_epi64(a0, $even, a1);
        $r1 = _mm512_permutex2var_epi64(a0, $odd, a1);
        $r2 = _mm512_permutex2var_epi64(b0, $even, b1);
        $r3 = _mm512_permutex2var_epi64(b0, $odd, b1);
        $r4 = _mm512_permutex2var_epi64(c0, $even, c1);
        $r5 = _mm512_permutex2var_epi64(c0, $odd, c1);
        $r6 = _mm512_permutex2var_epi64(d0, $even, d1);
        $r7 = _mm512_permutex2var_epi64(d0, $odd, d1);
    }};
}

macro_rules! ld {
    ($p:ident, $q:ident, $o:ident, $k:expr) => {{
        let v = _mm512_xor_si512(
            _mm512_loadu_si512($p.add($k).cast()),
            _mm512_loadu_si512($q.add($k).cast()),
        );
        _mm512_storeu_si512($o.add($k).cast(), v);
        v
    }};
}

macro_rules! st {
    ($o:ident, $k:expr, $v:ident) => {
        _mm512_storeu_si512(
            $o.add($k).cast(),
            _mm512_xor_si512($v, _mm512_loadu_si512($o.add($k).cast())),
        );
    };
}

macro_rules! compress_body {
    ($prev:ident, $refb:ident, $dst:ident, $after_first_column:expr) => {{
        let p = $prev.0.as_ptr().cast::<__m512i>();
        let q = $refb.0.as_ptr().cast::<__m512i>();
        let o = $dst.0.as_mut_ptr().cast::<__m512i>();
        let (mut r0, mut r1, mut r2, mut r3) = (
            ld!(p, q, o, 0),
            ld!(p, q, o, 1),
            ld!(p, q, o, 2),
            ld!(p, q, o, 3),
        );
        let (mut r4, mut r5, mut r6, mut r7) = (
            ld!(p, q, o, 4),
            ld!(p, q, o, 5),
            ld!(p, q, o, 6),
            ld!(p, q, o, 7),
        );
        let (mut r8, mut r9, mut r10, mut r11) = (
            ld!(p, q, o, 8),
            ld!(p, q, o, 9),
            ld!(p, q, o, 10),
            ld!(p, q, o, 11),
        );
        let (mut r12, mut r13, mut r14, mut r15) = (
            ld!(p, q, o, 12),
            ld!(p, q, o, 13),
            ld!(p, q, o, 14),
            ld!(p, q, o, 15),
        );
        row_pair!(r0, r1, r2, r3);
        row_pair!(r4, r5, r6, r7);
        row_pair!(r8, r9, r10, r11);
        row_pair!(r12, r13, r14, r15);
        let low = _mm512_set_epi64(11, 10, 3, 2, 9, 8, 1, 0);
        let high = _mm512_set_epi64(15, 14, 7, 6, 13, 12, 5, 4);
        let even = _mm512_set_epi64(13, 12, 9, 8, 5, 4, 1, 0);
        let odd = _mm512_set_epi64(15, 14, 11, 10, 7, 6, 3, 2);
        // Half 0 (words 0-7 of every row) holds column 0, whose word 0 is final first.
        column_quad!(r0, r2, r4, r6, r8, r10, r12, r14, low, high, even, odd);
        $after_first_column(_mm_cvtsi128_si64(_mm512_castsi512_si128(r0)) as u64);
        column_quad!(r1, r3, r5, r7, r9, r11, r13, r15, low, high, even, odd);
        st!(o, 0, r0);
        st!(o, 1, r1);
        st!(o, 2, r2);
        st!(o, 3, r3);
        st!(o, 4, r4);
        st!(o, 5, r5);
        st!(o, 6, r6);
        st!(o, 7, r7);
        st!(o, 8, r8);
        st!(o, 9, r9);
        st!(o, 10, r10);
        st!(o, 11, r11);
        st!(o, 12, r12);
        st!(o, 13, r13);
        st!(o, 14, r14);
        st!(o, 15, r15);
    }};
}

#[target_feature(enable = "avx512f")]
pub(super) unsafe fn compress_into(prev: &PowBlock, refb: &PowBlock, dst: &mut PowBlock) {
    compress_body!(prev, refb, dst, |_word0: u64| {});
}

/// As `compress_into`, prefetching the next data-dependent reference as soon as
/// word 0 of the output is final (after the first half's columns).
#[target_feature(enable = "avx512f")]
pub(super) unsafe fn compress_into_mid_prefetch_ring<const RING: usize>(
    prev: &PowBlock,
    refb: &PowBlock,
    dst: &mut PowBlock,
    next_ref_area_size: usize,
    memory_blocks_base: *const PowBlock,
    ring_base: *const PowBlock,
    next_index: usize,
    skip_from: usize,
) {
    let saved0 = prev.0[0] ^ refb.0[0];
    compress_body!(prev, refb, dst, |permuted0: u64| {
        let mut next_ref = reference_index(next_ref_area_size, permuted0 ^ saved0);
        if super::store_skipped(next_ref, skip_from) {
            // Rebuilt from its stored predecessor, so fetch that instead.
            next_ref -= 1;
        }
        if next_index - next_ref < RING {
            prefetch_pow_block::<{ super::ISA_AVX512_STREAM }>(
                &*ring_base.add(next_ref & (RING - 1)),
            );
        } else {
            prefetch_pow_block::<{ super::ISA_AVX512_STREAM }>(&*memory_blocks_base.add(next_ref));
        }
    });
}
