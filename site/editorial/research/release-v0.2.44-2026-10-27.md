# seine v0.2.44 release review

Checked October 27, 2026, 11:51 PM EDT. Published October 27, 2026, 10:10:12 PM EDT.

Official release: https://github.com/zpalmtree/seine/releases/tag/v0.2.44
Commit: `752f6679d0656eb45404bf867a72a3c475c59cdf`.

Four pinned source files (fee implementation, NVIDIA guide, configuration guide and release workflow) and src/config.rs are byte-identical to v0.2.43. Five platform archive names and flat2% fee remain unchanged. The sole src change is in adaptive_cpu.rs: reductions in thread count now account for the baseline measurement spread when the peak-floor requirement is at least1. Existing automatic-tuning and setup guides remain accurate; no new performance claim is added from the release's EPYC measurements. Current RAM reserve guidance remains valid.

Both official Linux archives were downloaded and matched the release SHA256SUMS.txt and GitHub asset digest. Internal executable checksums match packaged manifests. Readelf reports maximum GLIBC_2.39 for both architectures. No miner binary was executed.

- seine-linux-aarch64.tar.gz: `f7de91cfb6f0e799d3916a29718df17df01f2c5ab4202294b8780b8b37645d57`; maximum GLIBC_2.39.
- seine-linux-x86_64.tar.gz: `83d7d9599bd5f76a05b96e676035b6eed74369bf505028dd71685ae32b0d8c7c`; maximum GLIBC_2.39.

Pool release identity is refreshed for the same reviewed fee input. Calculator output is compared before/after in all20 locales; an unchanged rendering does not require a production restart. Full artifact evidence and output comparison are archived in the transaction-walkthrough showcase.
