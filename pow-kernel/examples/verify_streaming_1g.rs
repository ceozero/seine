//! Native full-size parity on an actual Linux x86-64 1 GiB HugeTLB mapping.
//! Requires at least three free 1 GiB pages; never falls back to ordinary pages.

#[cfg(all(target_os = "linux", target_arch = "x86_64"))]
mod native {
    use argon2::{Algorithm, Argon2, Params, Version};
    use blocknet_pow_kernel::{CpuKernel, FixedArgon2id, PowBlock};
    use std::{ffi::c_void, fs, io, mem, ptr, slice};

    unsafe extern "C" {
        fn mmap(
            addr: *mut c_void,
            length: usize,
            prot: i32,
            flags: i32,
            fd: i32,
            offset: i64,
        ) -> *mut c_void;
        fn munmap(addr: *mut c_void, length: usize) -> i32;
    }

    const MEMORY_KIB: usize = 2 * 1024 * 1024;
    const MAPPING_BYTES: usize = 3 * 1024 * 1024 * 1024;

    struct Arena(*mut c_void);

    impl Arena {
        fn new() -> Self {
            // Linux x86-64: PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS,
            // MAP_HUGETLB and log2(page-size) in MAP_HUGE_SHIFT (26).
            // No MAP_NORESERVE: fail immediately when the required pool is absent.
            let mapped = unsafe {
                mmap(
                    ptr::null_mut(),
                    MAPPING_BYTES,
                    0x3,
                    0x2 | 0x20 | 0x40000 | (30 << 26),
                    -1,
                    0,
                )
            };
            assert_ne!(
                mapped as usize,
                usize::MAX,
                "1 GiB HugeTLB mmap: {}",
                io::Error::last_os_error()
            );
            assert!(!mapped.is_null());
            Self(mapped)
        }

        fn blocks(&mut self) -> &mut [PowBlock] {
            assert_eq!(mem::size_of::<PowBlock>(), 1024);
            assert_eq!(self.0 as usize % mem::align_of::<PowBlock>(), 0);
            assert!((MEMORY_KIB + 2) * mem::size_of::<PowBlock>() <= MAPPING_BYTES);
            // Anonymous mmap initializes every byte to zero, a valid PowBlock.
            // The mapping is exclusively owned and outlives this mutable slice.
            unsafe { slice::from_raw_parts_mut(self.0.cast(), MEMORY_KIB + 2) }
        }

        fn page_size_kib(&self) -> u64 {
            let address = self.0 as usize;
            let mut inside = false;
            for line in fs::read_to_string("/proc/self/smaps").unwrap().lines() {
                if let Some((first, last)) = line
                    .split_whitespace()
                    .next()
                    .and_then(|s| s.split_once('-'))
                {
                    if let (Ok(first), Ok(last)) = (
                        usize::from_str_radix(first, 16),
                        usize::from_str_radix(last, 16),
                    ) {
                        inside = first <= address && address < last;
                    }
                }
                if inside && line.starts_with("KernelPageSize:") {
                    return line.split_whitespace().nth(1).unwrap().parse().unwrap();
                }
            }
            panic!("mapping not found in smaps");
        }
    }

    impl Drop for Arena {
        fn drop(&mut self) {
            // This pointer/length is exactly the successful mmap owned by Arena.
            if unsafe { munmap(self.0, MAPPING_BYTES) } != 0 {
                eprintln!("HugeTLB munmap failed: {}", io::Error::last_os_error());
            }
        }
    }

    pub fn run() {
        assert!(CpuKernel::Avx512256Stream.is_supported());
        let mut arena = Arena::new();
        let page_size = arena.page_size_kib();
        assert_eq!(page_size, 1024 * 1024, "must observe actual 1 GiB pages");
        println!("MAPPING page_mode=large-1g kernel_page_size_kib={page_size} length_bytes={MAPPING_BYTES}");
        let salt = b"streaming-full-size";
        let reference = Argon2::new(
            Algorithm::Argon2id,
            Version::V0x13,
            Params::new(MEMORY_KIB as u32, 1, 1, Some(32)).unwrap(),
        );
        let mut cases = Vec::new();
        for nonce in [0u64, 12345, u64::MAX] {
            let mut output = [0u8; 32];
            reference
                .hash_password_into(&nonce.to_le_bytes(), salt, &mut output)
                .unwrap();
            cases.push((nonce, output));
        }
        let mut guard = PowBlock::default();
        guard.as_mut().fill(0xa5a5_a5a5_a5a5_a5a5);
        let guarded = arena.blocks();
        guarded[0] = guard;
        guarded[MEMORY_KIB + 1] = guard;
        let mut hasher = FixedArgon2id::with_kernel(MEMORY_KIB as u32, CpuKernel::Avx2).unwrap();
        for (nonce, expected) in cases {
            for kernel in [
                CpuKernel::Avx2,
                CpuKernel::Avx512256Stream,
                CpuKernel::Avx512,
                CpuKernel::Avx512256Stream,
                CpuKernel::Avx512256,
                CpuKernel::Avx512256Stream,
                CpuKernel::Avx2,
            ] {
                hasher.set_kernel(kernel).unwrap();
                let mut output = [0u8; 32];
                hasher
                    .hash_password_into_with_memory(
                        &nonce.to_le_bytes(),
                        salt,
                        &mut output,
                        &mut guarded[1..MEMORY_KIB + 1],
                    )
                    .unwrap();
                assert_eq!(output, expected, "nonce={nonce},kernel={kernel}");
                assert_eq!(guarded[0].as_ref(), guard.as_ref());
                assert_eq!(guarded[MEMORY_KIB + 1].as_ref(), guard.as_ref());
                println!("PASS nonce={nonce} kernel={kernel} backing=large-1g full_size_bytes={} dirty_reuse=true guards=true", MEMORY_KIB as u64 * 1024);
            }
        }
    }
}

fn main() {
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    native::run();
    #[cfg(not(all(target_os = "linux", target_arch = "x86_64")))]
    panic!("this verifier requires Linux x86-64 and explicit 1 GiB HugeTLB pages");
}
