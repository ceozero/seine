use blocknet_pow_kernel::Blake2bPowMidstate;
use blocknet_pow_spec::{
    blake2b_pow_hash, blake2b_pow_target_bytes, BLAKE2B_POW_PERSONAL_MAINNET,
    BLAKE2B_POW_PERSONAL_TESTNET, FARADAY_HEADER_BASE_LEN,
};

fn header(len: usize, seed: u64) -> Vec<u8> {
    let mut state = seed ^ 0x9e37_79b9_7f4a_7c15;
    (0..len)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            state as u8
        })
        .collect()
}

const NONCES: [u64; 7] = [
    0,
    1,
    0xff,
    0x1_0000_0000,
    0x0123_4567_89ab_cdef,
    u64::MAX - 1,
    u64::MAX,
];

#[test]
fn midstate_matches_reference_for_every_layout() {
    // 0..=300 covers no cached block, a straddling nonce, an exactly full final
    // block, two uncached blocks and two cached blocks.
    for personal in [&BLAKE2B_POW_PERSONAL_MAINNET, &BLAKE2B_POW_PERSONAL_TESTNET] {
        for len in 0..=300 {
            let base = header(len, len as u64);
            let midstate = Blake2bPowMidstate::new(personal, &base).unwrap();
            for nonce in NONCES {
                assert_eq!(
                    midstate.hash(nonce),
                    blake2b_pow_hash(personal, &base, nonce),
                    "len={len} nonce={nonce:#x}"
                );
            }
        }
    }
}

#[test]
fn faraday_header_is_one_compression_per_nonce() {
    let base = header(FARADAY_HEADER_BASE_LEN, 7);
    let midstate = Blake2bPowMidstate::new(&BLAKE2B_POW_PERSONAL_MAINNET, &base).unwrap();
    assert_eq!(midstate.compressions_per_nonce(), 1);
}

fn scan_matches_reference(len: usize) {
    let base = header(len, 99);
    let personal = &BLAKE2B_POW_PERSONAL_MAINNET;
    let midstate = Blake2bPowMidstate::new(personal, &base).unwrap();
    let start = u64::MAX - 1_000;
    let count = 4_000;
    let hashes: Vec<[u8; 32]> = (0..count)
        .map(|i| {
            blake2b_pow_target_bytes(&blake2b_pow_hash(personal, &base, start.wrapping_add(i)))
        })
        .collect();

    // Targets equal to sampled hashes exercise the `<=` boundary in every limb.
    let mut sorted = hashes.clone();
    sorted.sort();
    let mut targets = vec![[0u8; 32], [0xff; 32]];
    for index in [0, 1, 3, 40, 999, 3_999] {
        targets.push(sorted[index]);
        let mut below = sorted[index];
        for byte in below.iter_mut().rev() {
            let (value, borrow) = byte.overflowing_sub(1);
            *byte = value;
            if !borrow {
                break;
            }
        }
        targets.push(below);
    }
    let mut first_limb_tie = sorted[10];
    first_limb_tie[8..].fill(0);
    targets.push(first_limb_tie);

    for target in targets {
        let expected: Vec<u64> = (0..count)
            .filter(|&i| hashes[i as usize] <= target)
            .map(|i| start.wrapping_add(i))
            .collect();
        let mut hits = Vec::new();
        assert_eq!(
            midstate.scan(start, count, &target, |nonce| hits.push(nonce)),
            count
        );
        assert_eq!(hits, expected, "len={len} target={target:02x?}");
    }
}

#[test]
fn scan_reports_exactly_the_reference_hits() {
    scan_matches_reference(FARADAY_HEADER_BASE_LEN);
    // Two uncached blocks take the general path.
    scan_matches_reference(124);
}

#[test]
fn single_block_layout_describes_the_faraday_header() {
    let base = header(FARADAY_HEADER_BASE_LEN, 3);
    let midstate = Blake2bPowMidstate::new(&BLAKE2B_POW_PERSONAL_MAINNET, &base).unwrap();
    let layout = midstate.single_block_layout().unwrap();
    // 28 header bytes then the nonce: word 3 high half and word 4 low half.
    assert_eq!(
        (layout.nonce_word, layout.nonce_shift, layout.message_words),
        (3, 32, 5)
    );
    assert_eq!(layout.counter, 164);
    assert!(layout.message[5..].iter().all(|&word| word == 0));
    let straddle = Blake2bPowMidstate::new(&BLAKE2B_POW_PERSONAL_MAINNET, &header(124, 3)).unwrap();
    assert!(straddle.single_block_layout().is_none());
}

#[test]
fn strided_scan_visits_interleaved_nonces() {
    let base = header(FARADAY_HEADER_BASE_LEN, 11);
    let personal = &BLAKE2B_POW_PERSONAL_MAINNET;
    let midstate = Blake2bPowMidstate::new(personal, &base).unwrap();
    let mut target = [0u8; 32];
    target[0] = 0x10; // about 1 in 16
    let (start, stride, count) = (u64::MAX - 20, 3u64, 2_000u64);
    let expected: Vec<u64> = (0..count)
        .map(|i| start.wrapping_add(i * stride))
        .filter(|&nonce| {
            blake2b_pow_target_bytes(&blake2b_pow_hash(personal, &base, nonce)) <= target
        })
        .collect();
    let mut hits = Vec::new();
    assert_eq!(
        midstate.scan_stride(start, stride, count, &target, |n| hits.push(n)),
        count
    );
    assert!(!expected.is_empty());
    assert_eq!(hits, expected);
}
