# blocknet-pow-kernel

Reusable fixed-parameter Argon2id kernel extracted from Seine's CPU backend
for reuse by external verifiers.

This crate exports:
- `FixedArgon2id`
- `PowBlock`
- `ReusablePowContext`

## Verification tools

The opt-in `cpu-research` feature adds verification and analysis tools used in
development. It is not enabled by the miner and does not change PoW parameters or
kernel dispatch.

## Faraday BLAKE2b-512 PoW

`Blake2bPowMidstate` implements the Faraday fork hash
(`BLAKE2b-512(personal; header_base || nonce_le)`, target check on the first
32 output bytes read big-endian). It compresses the template prefix once, so
the 156-byte v2 header costs one compression per nonce. The reference lives in
`blocknet-pow-spec` (`blake2b_pow_hash`). Its vectors come from Python's
`hashlib.blake2b` until upstream publishes official ones; the kernel is
checked against the reference for every header length from 0 to 300 bytes.

CPU workers use it for BLAKE2b templates. To print the single-thread scan
rate on a host:

```bash
cargo +1.93.0 run --release --locked -p blocknet-pow-kernel --example blake2b_pow_rate -- 3
```
