//! Offline full-size correctness check for a CPU architecture validation host.
//! Uses one 2 GiB arena at a time; never connects to a daemon or pool.
use argon2::{Algorithm, Argon2, Params, Version};
use blocknet_pow_kernel::{CpuKernel, FixedArgon2id, PowBlock};

fn main() {
    const MEMORY_KIB: u32 = 2 * 1024 * 1024;
    let password = b"architecture-matrix-full-size";
    let salt = b"seine-cpu-validation";
    let mut reference = [0u8; 32];
    Argon2::new(
        Algorithm::Argon2id,
        Version::V0x13,
        Params::new(MEMORY_KIB, 1, 1, Some(32)).unwrap(),
    )
    .hash_password_into(password, salt, &mut reference)
    .unwrap();
    println!("reference={reference:02x?}");
    let mut arena = vec![PowBlock::default(); MEMORY_KIB as usize];
    for kernel in CpuKernel::ALL {
        if !kernel.is_supported() {
            println!("{kernel}: unsupported");
            continue;
        }
        let mut hasher = FixedArgon2id::with_kernel(MEMORY_KIB, kernel).unwrap();
        let mut result = [0u8; 32];
        hasher
            .hash_password_into_with_memory(password, salt, &mut result, &mut arena)
            .unwrap();
        assert_eq!(result, reference, "kernel={kernel}");
        println!("{kernel}: PASS (full 2 GiB reference parity)");
        // Research: skipped arena stores, checked on an arena that still holds
        // the previous hash, so a stale read would show up as a mismatch.
        if kernel.as_str().starts_with("avx512") && kernel.as_str().contains("stream") {
            for permille in [500u16, 600] {
                hasher.set_skip_store_permille(permille);
                let salt2 = b"seine-cpu-validation-skip";
                let mut expected2 = [0u8; 32];
                Argon2::new(
                    Algorithm::Argon2id,
                    Version::V0x13,
                    Params::new(MEMORY_KIB, 1, 1, Some(32)).unwrap(),
                )
                .hash_password_into(password, salt2, &mut expected2)
                .unwrap();
                hasher
                    .hash_password_into_with_memory(password, salt2, &mut result, &mut arena)
                    .unwrap();
                assert_eq!(result, expected2, "kernel={kernel} skip={permille}");
                println!("{kernel} skip-store {permille}: PASS (full 2 GiB reference parity)");
                hasher.set_skip_store_permille(0);
            }
        }
    }
}
