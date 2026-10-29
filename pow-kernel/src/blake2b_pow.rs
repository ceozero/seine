//! Faraday BLAKE2b-512 PoW kernel: `BLAKE2b-512(personal; header_base || nonce_le)`.
//!
//! Every message block before the nonce's final block is compressed once per
//! template, so a nonce normally costs one compression (the 156-byte Faraday
//! header leaves a 36-byte final block). Only the first four output words are
//! needed for the target check; full digests are produced for hits.

const BLOCK_BYTES: usize = 128;
const BLOCK_WORDS: usize = 16;
const MAX_TAIL_BLOCKS: usize = 2;
const OUT_BYTES: usize = 64;
const NONCE_BYTES: usize = 8;

const IV: [u64; 8] = [
    0x6a09e667f3bcc908,
    0xbb67ae8584caa73b,
    0x3c6ef372fe94f82b,
    0xa54ff53a5f1d36f1,
    0x510e527fade682d1,
    0x9b05688c2b3e6c1f,
    0x1f83d9abfb41bd6b,
    0x5be0cd19137e2179,
];

const SIGMA: [[usize; 16]; 12] = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    [14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3],
    [11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4],
    [7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8],
    [9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13],
    [2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9],
    [12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11],
    [13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10],
    [6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5],
    [10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0],
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    [14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3],
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Blake2bPowError {
    /// The header plus nonce must leave at most two uncached blocks; true for
    /// every header length, so this only guards the internal layout.
    UnsupportedLayout,
}

impl std::fmt::Display for Blake2bPowError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("unsupported BLAKE2b PoW header layout")
    }
}

impl std::error::Error for Blake2bPowError {}

/// One-compression layout: hash `message` (with the nonce OR-ed in at
/// `nonce_word`/`nonce_shift`) from chain value `h` as the final block.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Blake2bPowSingleBlock {
    pub h: [u64; 8],
    /// Message words with the nonce bytes zeroed.
    pub message: [u64; BLOCK_WORDS],
    pub counter: u128,
    pub nonce_word: usize,
    /// Bit shift of the nonce inside `nonce_word`; a multiple of 8.
    pub nonce_shift: u32,
    /// Words from `message_words` onward are zero for every nonce.
    pub message_words: usize,
}

/// Per-template BLAKE2b state; cheap to clone into each worker.
#[derive(Debug, Clone)]
pub struct Blake2bPowMidstate {
    /// Chain value after the cached prefix blocks.
    h: [u64; 8],
    /// Uncached message words with the nonce bytes zeroed.
    tail: [u64; BLOCK_WORDS * MAX_TAIL_BLOCKS],
    tail_blocks: usize,
    /// Byte counter after the cached prefix.
    prefix_len: u128,
    total_len: u128,
    nonce_word: usize,
    nonce_shift: u32,
}

impl Blake2bPowMidstate {
    pub fn new(personal: &[u8; 16], header_base: &[u8]) -> Result<Self, Blake2bPowError> {
        let total = header_base.len() + NONCE_BYTES;
        // Cache whole blocks that end before the nonce and are not the final block.
        let cached_blocks = (header_base.len() / BLOCK_BYTES).min((total - 1) / BLOCK_BYTES);
        let cached_bytes = cached_blocks * BLOCK_BYTES;
        let tail_len = total - cached_bytes;
        let tail_blocks = tail_len.div_ceil(BLOCK_BYTES);
        if tail_blocks == 0 || tail_blocks > MAX_TAIL_BLOCKS {
            return Err(Blake2bPowError::UnsupportedLayout);
        }

        let mut h = IV;
        h[0] ^= 0x0101_0000 ^ OUT_BYTES as u64;
        h[6] ^= u64::from_le_bytes(personal[..8].try_into().expect("8 bytes"));
        h[7] ^= u64::from_le_bytes(personal[8..].try_into().expect("8 bytes"));
        for (index, block) in header_base[..cached_bytes]
            .chunks_exact(BLOCK_BYTES)
            .enumerate()
        {
            let mut m = [0u64; BLOCK_WORDS];
            for (word, bytes) in m.iter_mut().zip(block.chunks_exact(8)) {
                *word = u64::from_le_bytes(bytes.try_into().expect("8 bytes"));
            }
            compress(&mut h, &m, ((index + 1) * BLOCK_BYTES) as u128, false);
        }

        let mut tail_bytes = [0u8; BLOCK_BYTES * MAX_TAIL_BLOCKS];
        let header_tail = &header_base[cached_bytes..];
        tail_bytes[..header_tail.len()].copy_from_slice(header_tail);
        let mut tail = [0u64; BLOCK_WORDS * MAX_TAIL_BLOCKS];
        for (word, bytes) in tail.iter_mut().zip(tail_bytes.chunks_exact(8)) {
            *word = u64::from_le_bytes(bytes.try_into().expect("8 bytes"));
        }

        Ok(Self {
            h,
            tail,
            tail_blocks,
            prefix_len: cached_bytes as u128,
            total_len: total as u128,
            nonce_word: header_tail.len() / 8,
            nonce_shift: (header_tail.len() % 8) as u32 * 8,
        })
    }

    /// Number of compressions per nonce (1 for the Faraday header).
    pub fn compressions_per_nonce(&self) -> usize {
        self.tail_blocks
    }

    /// Inputs for an accelerator that hashes the single final block itself;
    /// `None` when the nonce leaves two uncached blocks.
    pub fn single_block_layout(&self) -> Option<Blake2bPowSingleBlock> {
        if self.tail_blocks != 1 {
            return None;
        }
        let nonce_end = self.nonce_word * 8 + (self.nonce_shift / 8) as usize + NONCE_BYTES;
        Some(Blake2bPowSingleBlock {
            h: self.h,
            message: self.tail[..BLOCK_WORDS].try_into().expect("16 words"),
            counter: self.total_len,
            nonce_word: self.nonce_word,
            nonce_shift: self.nonce_shift,
            message_words: nonce_end.div_ceil(8),
        })
    }

    /// Full 64-byte digest for one nonce.
    pub fn hash(&self, nonce: u64) -> [u8; OUT_BYTES] {
        let h = self.chain(nonce);
        let mut out = [0u8; OUT_BYTES];
        for (bytes, word) in out.chunks_exact_mut(8).zip(h) {
            bytes.copy_from_slice(&word.to_le_bytes());
        }
        out
    }

    /// The 32 bytes compared against the target (first half of the digest).
    pub fn target_bytes(&self, nonce: u64) -> [u8; 32] {
        self.hash(nonce)[..32].try_into().expect("32 bytes")
    }

    /// Hashes `count` nonces from `start_nonce` (wrapping) and reports each
    /// nonce whose target bytes are `<= target`. Returns hashes computed.
    pub fn scan(
        &self,
        start_nonce: u64,
        count: u64,
        target: &[u8; 32],
        on_hit: impl FnMut(u64),
    ) -> u64 {
        self.scan_stride(start_nonce, 1, count, target, on_hit)
    }

    /// Like `scan`, visiting `start_nonce + i * stride` for `i < count`
    /// (wrapping), so interleaved CPU lanes share one nonce range.
    pub fn scan_stride(
        &self,
        start_nonce: u64,
        stride: u64,
        count: u64,
        target: &[u8; 32],
        mut on_hit: impl FnMut(u64),
    ) -> u64 {
        let target_words = TargetWords::new(target);
        let mut nonce = start_nonce;
        if self.tail_blocks == 1 {
            for _ in 0..count {
                let h = self.single_block_prefix(nonce);
                if target_words.accepts(&h) {
                    on_hit(nonce);
                }
                nonce = nonce.wrapping_add(stride);
            }
        } else {
            for _ in 0..count {
                let h = self.chain(nonce);
                if target_words.accepts(&[h[0], h[1], h[2], h[3]]) {
                    on_hit(nonce);
                }
                nonce = nonce.wrapping_add(stride);
            }
        }
        count
    }

    #[inline(always)]
    fn message(&self, nonce: u64) -> [u64; BLOCK_WORDS * MAX_TAIL_BLOCKS] {
        let mut m = self.tail;
        m[self.nonce_word] |= nonce << self.nonce_shift;
        if self.nonce_shift != 0 {
            m[self.nonce_word + 1] |= nonce >> (64 - self.nonce_shift);
        }
        m
    }

    fn chain(&self, nonce: u64) -> [u64; 8] {
        let m = self.message(nonce);
        let mut h = self.h;
        for block in 0..self.tail_blocks {
            let last = block + 1 == self.tail_blocks;
            let counter = if last {
                self.total_len
            } else {
                self.prefix_len + ((block + 1) * BLOCK_BYTES) as u128
            };
            let words: &[u64; BLOCK_WORDS] = m[block * BLOCK_WORDS..(block + 1) * BLOCK_WORDS]
                .try_into()
                .expect("16 words");
            compress(&mut h, words, counter, last);
        }
        h
    }

    /// First four chain words for a single final block; the compiler drops the
    /// work that only feeds output words 4..8.
    #[inline(always)]
    fn single_block_prefix(&self, nonce: u64) -> [u64; 4] {
        let m = self.message(nonce);
        let words: &[u64; BLOCK_WORDS] = m[..BLOCK_WORDS].try_into().expect("16 words");
        let v = rounds(&self.h, words, self.total_len, true);
        [
            self.h[0] ^ v[0] ^ v[8],
            self.h[1] ^ v[1] ^ v[9],
            self.h[2] ^ v[2] ^ v[10],
            self.h[3] ^ v[3] ^ v[11],
        ]
    }
}

/// Target as big-endian u64 limbs so output words compare without byte copies.
struct TargetWords([u64; 4]);

impl TargetWords {
    fn new(target: &[u8; 32]) -> Self {
        let mut words = [0u64; 4];
        for (word, bytes) in words.iter_mut().zip(target.chunks_exact(8)) {
            *word = u64::from_be_bytes(bytes.try_into().expect("8 bytes"));
        }
        Self(words)
    }

    /// Output words are little-endian, so byte-swapping gives the big-endian limb.
    #[inline(always)]
    fn accepts(&self, h: &[u64; 4]) -> bool {
        let first = h[0].swap_bytes();
        if first != self.0[0] {
            return first < self.0[0];
        }
        [h[1].swap_bytes(), h[2].swap_bytes(), h[3].swap_bytes()]
            <= [self.0[1], self.0[2], self.0[3]]
    }
}

#[inline(always)]
fn g(v: &mut [u64; 16], a: usize, b: usize, c: usize, d: usize, x: u64, y: u64) {
    v[a] = v[a].wrapping_add(v[b]).wrapping_add(x);
    v[d] = (v[d] ^ v[a]).rotate_right(32);
    v[c] = v[c].wrapping_add(v[d]);
    v[b] = (v[b] ^ v[c]).rotate_right(24);
    v[a] = v[a].wrapping_add(v[b]).wrapping_add(y);
    v[d] = (v[d] ^ v[a]).rotate_right(16);
    v[c] = v[c].wrapping_add(v[d]);
    v[b] = (v[b] ^ v[c]).rotate_right(63);
}

macro_rules! round {
    ($v:ident, $m:ident, $r:literal) => {{
        const S: [usize; 16] = SIGMA[$r];
        g(&mut $v, 0, 4, 8, 12, $m[S[0]], $m[S[1]]);
        g(&mut $v, 1, 5, 9, 13, $m[S[2]], $m[S[3]]);
        g(&mut $v, 2, 6, 10, 14, $m[S[4]], $m[S[5]]);
        g(&mut $v, 3, 7, 11, 15, $m[S[6]], $m[S[7]]);
        g(&mut $v, 0, 5, 10, 15, $m[S[8]], $m[S[9]]);
        g(&mut $v, 1, 6, 11, 12, $m[S[10]], $m[S[11]]);
        g(&mut $v, 2, 7, 8, 13, $m[S[12]], $m[S[13]]);
        g(&mut $v, 3, 4, 9, 14, $m[S[14]], $m[S[15]]);
    }};
}

#[inline(always)]
fn rounds(h: &[u64; 8], m: &[u64; BLOCK_WORDS], counter: u128, last: bool) -> [u64; 16] {
    let mut v = [0u64; 16];
    v[..8].copy_from_slice(h);
    v[8..].copy_from_slice(&IV);
    v[12] ^= counter as u64;
    v[13] ^= (counter >> 64) as u64;
    if last {
        v[14] = !v[14];
    }
    round!(v, m, 0);
    round!(v, m, 1);
    round!(v, m, 2);
    round!(v, m, 3);
    round!(v, m, 4);
    round!(v, m, 5);
    round!(v, m, 6);
    round!(v, m, 7);
    round!(v, m, 8);
    round!(v, m, 9);
    round!(v, m, 10);
    round!(v, m, 11);
    v
}

fn compress(h: &mut [u64; 8], m: &[u64; BLOCK_WORDS], counter: u128, last: bool) {
    let v = rounds(h, m, counter, last);
    for i in 0..8 {
        h[i] ^= v[i] ^ v[i + 8];
    }
}
