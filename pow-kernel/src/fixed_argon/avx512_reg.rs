//! Register-resident full-width AVX-512 compression for `avx512-stream`.
//!
//! The 1 KiB block lives in sixteen zmm registers for the whole permutation:
//! `r[k]` holds words `8k..8k+8`, so row `i` is `r[2i]` (words 0-7) and
//! `r[2i+1]` (words 8-15). Row rounds process two rows per vector set; column
//! rounds process two columns per set, gathered with two-source permutes. The
//! pre-round value is written to `dst` once and XORed back at the end, so no
//! working copy goes through memory. Every entry point requires AVX-512F.
//! Xeon 8488C: +2% at 16 workers and +6.5% at 8 over the 256-bit streaming
//! kernel; EPYC 9R45 neutral against the earlier full-width compress.

use std::arch::x86_64::*;

use super::{prefetch_pow_block, reference_index, PowBlock};

#[inline(always)]
unsafe fn blamka(x: __m512i, y: __m512i) -> __m512i {
    let product = _mm512_mul_epu32(x, y);
    _mm512_add_epi64(_mm512_add_epi64(x, y), _mm512_add_epi64(product, product))
}

/// One BLAKE2b-style round on two independent 4x4 word matrices: lanes 0-3
/// and 4-7 of `a`, `b`, `c` and `d` are separate rows (or columns).
#[inline(always)]
unsafe fn round(a: &mut __m512i, b: &mut __m512i, c: &mut __m512i, d: &mut __m512i) {
    macro_rules! g {
        () => {
            *a = blamka(*a, *b);
            *d = _mm512_ror_epi64::<32>(_mm512_xor_si512(*d, *a));
            *c = blamka(*c, *d);
            *b = _mm512_ror_epi64::<24>(_mm512_xor_si512(*b, *c));
            *a = blamka(*a, *b);
            *d = _mm512_ror_epi64::<16>(_mm512_xor_si512(*d, *a));
            *c = blamka(*c, *d);
            *b = _mm512_ror_epi64::<63>(_mm512_xor_si512(*b, *c));
        };
    }
    g!();
    // Diagonalize within each 256-bit half: b <<< 1, c <<< 2, d <<< 3.
    *b = _mm512_permutex_epi64::<0x39>(*b);
    *c = _mm512_permutex_epi64::<0x4e>(*c);
    *d = _mm512_permutex_epi64::<0x93>(*d);
    g!();
    *b = _mm512_permutex_epi64::<0x93>(*b);
    *c = _mm512_permutex_epi64::<0x4e>(*c);
    *d = _mm512_permutex_epi64::<0x39>(*d);
}

#[inline(always)]
unsafe fn rows(r: &mut [__m512i; 16]) {
    for pair in 0..4 {
        let (i, j) = (4 * pair, 4 * pair + 2); // rows 2*pair and 2*pair + 1
        let mut a = _mm512_shuffle_i64x2::<0x44>(r[i], r[j]);
        let mut b = _mm512_shuffle_i64x2::<0xee>(r[i], r[j]);
        let mut c = _mm512_shuffle_i64x2::<0x44>(r[i + 1], r[j + 1]);
        let mut d = _mm512_shuffle_i64x2::<0xee>(r[i + 1], r[j + 1]);
        round(&mut a, &mut b, &mut c, &mut d);
        r[i] = _mm512_shuffle_i64x2::<0x44>(a, b);
        r[j] = _mm512_shuffle_i64x2::<0xee>(a, b);
        r[i + 1] = _mm512_shuffle_i64x2::<0x44>(c, d);
        r[j + 1] = _mm512_shuffle_i64x2::<0xee>(c, d);
    }
}

/// Columns `2t` and `2t + 1` of half `h` (0: words 0-7, 1: words 8-15). Returns
/// the processed (a, b, c, d) pairs so the caller can scatter two pairs at once.
#[inline(always)]
unsafe fn column_pair(r: &[__m512i; 16], h: usize, t: usize) -> [__m512i; 4] {
    // Lanes are 128-bit word pairs: take lane 2t then 2t+1 from rows x and y.
    let index = if t == 0 {
        _mm512_set_epi64(11, 10, 3, 2, 9, 8, 1, 0)
    } else {
        _mm512_set_epi64(15, 14, 7, 6, 13, 12, 5, 4)
    };
    let gather = |x: usize, y: usize| _mm512_permutex2var_epi64(r[2 * x + h], index, r[2 * y + h]);
    let mut a = gather(0, 1);
    let mut b = gather(2, 3);
    let mut c = gather(4, 5);
    let mut d = gather(6, 7);
    round(&mut a, &mut b, &mut c, &mut d);
    [a, b, c, d]
}

#[inline(always)]
unsafe fn scatter_columns(r: &mut [__m512i; 16], h: usize, low: [__m512i; 4], high: [__m512i; 4]) {
    // low holds lanes 0,1 of rows (x, y); high holds lanes 2,3.
    let even = _mm512_set_epi64(13, 12, 9, 8, 5, 4, 1, 0);
    let odd = _mm512_set_epi64(15, 14, 11, 10, 7, 6, 3, 2);
    for (k, (lo, hi)) in low.into_iter().zip(high).enumerate() {
        r[2 * (2 * k) + h] = _mm512_permutex2var_epi64(lo, even, hi);
        r[2 * (2 * k + 1) + h] = _mm512_permutex2var_epi64(lo, odd, hi);
    }
}

#[inline(always)]
unsafe fn load_xor_store(prev: &PowBlock, refb: &PowBlock, dst: &mut PowBlock) -> [__m512i; 16] {
    let p = prev.0.as_ptr().cast::<__m512i>();
    let q = refb.0.as_ptr().cast::<__m512i>();
    let o = dst.0.as_mut_ptr().cast::<__m512i>();
    let mut r = [_mm512_setzero_si512(); 16];
    for k in 0..16 {
        r[k] = _mm512_xor_si512(
            _mm512_loadu_si512(p.add(k).cast()),
            _mm512_loadu_si512(q.add(k).cast()),
        );
        _mm512_storeu_si512(o.add(k).cast(), r[k]);
    }
    r
}

#[inline(always)]
unsafe fn finish(r: &[__m512i; 16], dst: &mut PowBlock) {
    let o = dst.0.as_mut_ptr().cast::<__m512i>();
    for k in 0..16 {
        let saved = _mm512_loadu_si512(o.add(k).cast());
        _mm512_storeu_si512(o.add(k).cast(), _mm512_xor_si512(r[k], saved));
    }
}

#[target_feature(enable = "avx512f")]
pub(super) unsafe fn compress_into(prev: &PowBlock, refb: &PowBlock, dst: &mut PowBlock) {
    let mut r = load_xor_store(prev, refb, dst);
    rows(&mut r);
    for h in 0..2 {
        let low = column_pair(&r, h, 0);
        let high = column_pair(&r, h, 1);
        scatter_columns(&mut r, h, low, high);
    }
    finish(&r, dst);
}

/// As `compress_into`, prefetching the next data-dependent reference as soon as
/// word 0 of the output is final (after the first column pair).
#[target_feature(enable = "avx512f")]
pub(super) unsafe fn compress_into_mid_prefetch_ring<const RING: usize>(
    prev: &PowBlock,
    refb: &PowBlock,
    dst: &mut PowBlock,
    next_ref_area_size: usize,
    memory_blocks_base: *const PowBlock,
    ring_base: *const PowBlock,
    next_index: usize,
) {
    let mut r = load_xor_store(prev, refb, dst);
    rows(&mut r);
    let low = column_pair(&r, 0, 0);
    // Word 0 of the output is lane 0 of the processed `a` XOR the saved input.
    let word0 = _mm_cvtsi128_si64(_mm512_castsi512_si128(low[0])) as u64 ^ dst.0[0];
    let next_ref = reference_index(next_ref_area_size, word0);
    if next_index - next_ref < RING {
        prefetch_pow_block::<{ super::ISA_AVX512_STREAM }>(&*ring_base.add(next_ref & (RING - 1)));
    } else {
        prefetch_pow_block::<{ super::ISA_AVX512_STREAM }>(&*memory_blocks_base.add(next_ref));
    }
    let high = column_pair(&r, 0, 1);
    scatter_columns(&mut r, 0, low, high);
    let low = column_pair(&r, 1, 0);
    let high = column_pair(&r, 1, 1);
    scatter_columns(&mut r, 1, low, high);
    finish(&r, dst);
}
