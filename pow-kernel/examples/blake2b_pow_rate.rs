//! Single-thread BLAKE2b PoW scan rate for the Faraday 156-byte header.
//! Usage: blake2b_pow_rate [seconds]
use blocknet_pow_kernel::Blake2bPowMidstate;
use blocknet_pow_spec::{BLAKE2B_POW_PERSONAL_MAINNET, FARADAY_HEADER_BASE_LEN};
use std::time::{Duration, Instant};

fn main() {
    let secs: f64 = std::env::args()
        .nth(1)
        .map_or(3.0, |s| s.parse().expect("seconds"));
    let header: Vec<u8> = (0..FARADAY_HEADER_BASE_LEN).map(|i| i as u8).collect();
    let midstate = Blake2bPowMidstate::new(&BLAKE2B_POW_PERSONAL_MAINNET, &header).unwrap();
    let target = [0u8; 32];
    let budget = Duration::from_secs_f64(secs);
    let started = Instant::now();
    let (mut nonce, mut hashes, mut hits) = (0u64, 0u64, 0u64);
    while started.elapsed() < budget {
        hashes += midstate.scan(nonce, 1 << 20, &target, |_| hits += 1);
        nonce = nonce.wrapping_add(1 << 20);
    }
    let elapsed = started.elapsed().as_secs_f64();
    println!(
        "{{\"hashes\":{hashes},\"secs\":{elapsed:.3},\"mhs\":{:.3},\"hits\":{hits}}}",
        hashes as f64 / elapsed / 1e6
    );
}
