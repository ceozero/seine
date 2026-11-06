// Faraday BLAKE2b-512 PoW scan for Metal: one final-block compression per
// nonce from a host-computed starting state. The host prepends the defines
// for the header layout:
// SEINE_B2_NONCE_WORD, SEINE_B2_NONCE_SHIFT, SEINE_B2_MSG_WORDS and
// SEINE_B2_PRE_COLUMNS (round-0 column steps already applied to params.v).

#include <metal_stdlib>
using namespace metal;

struct Blake2bPowParams {
    // Working state before round 0, with SEINE_B2_PRE_COLUMNS applied.
    ulong v[16];
    ulong m[16];
    // First chain word, for the first output word.
    ulong h0;
    // Big-endian first limb of the target; the host checks full hits exactly.
    ulong target_limb0;
};

static inline ulong seine_rotr32(ulong x) {
    return as_type<ulong>(as_type<uint2>(x).yx);
}

static inline ulong seine_rotr(ulong x, uint n) {
    return (x >> n) | (x << (64 - n));
}

static inline uint seine_bswap32(uint x) {
    return (x >> 24) | ((x >> 8) & 0xff00u) | ((x << 8) & 0xff0000u) | (x << 24);
}

static inline ulong seine_bswap64(ulong x) {
    uint2 halves = as_type<uint2>(x);
    return (ulong(seine_bswap32(halves.x)) << 32) | ulong(seine_bswap32(halves.y));
}

#define SEINE_B2_G(a, b, c, d, x, y)        \
    do {                                     \
        a = a + b + (x);                     \
        d = seine_rotr32(d ^ a);             \
        c = c + d;                           \
        b = seine_rotr(b ^ c, 24);           \
        a = a + b + (y);                     \
        d = seine_rotr(d ^ a, 16);           \
        c = c + d;                           \
        b = seine_rotr(b ^ c, 63);           \
    } while (0)

// Message word i, or a literal zero the compiler folds away.
#define SEINE_B2_M(i) ((i) < SEINE_B2_MSG_WORDS ? m[(i) < SEINE_B2_MSG_WORDS ? (i) : 0] : 0UL)

#define SEINE_B2_ROUND(s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14, s15) \
    do {                                                                                      \
        SEINE_B2_G(v0, v4, v8, v12, SEINE_B2_M(s0), SEINE_B2_M(s1));                          \
        SEINE_B2_G(v1, v5, v9, v13, SEINE_B2_M(s2), SEINE_B2_M(s3));                          \
        SEINE_B2_G(v2, v6, v10, v14, SEINE_B2_M(s4), SEINE_B2_M(s5));                         \
        SEINE_B2_G(v3, v7, v11, v15, SEINE_B2_M(s6), SEINE_B2_M(s7));                         \
        SEINE_B2_G(v0, v5, v10, v15, SEINE_B2_M(s8), SEINE_B2_M(s9));                         \
        SEINE_B2_G(v1, v6, v11, v12, SEINE_B2_M(s10), SEINE_B2_M(s11));                       \
        SEINE_B2_G(v2, v7, v8, v13, SEINE_B2_M(s12), SEINE_B2_M(s13));                        \
        SEINE_B2_G(v3, v4, v9, v14, SEINE_B2_M(s14), SEINE_B2_M(s15));                        \
    } while (0)

kernel void blake2b_pow_scan_kernel(
    constant Blake2bPowParams &params [[buffer(0)]],
    constant ulong &start_nonce [[buffer(1)]],
    constant ulong &nonce_count [[buffer(2)]],
    device ulong *candidates [[buffer(3)]],
    device atomic_uint *candidate_count [[buffer(4)]],
    constant uint &candidate_capacity [[buffer(5)]],
    uint gid [[thread_position_in_grid]],
    uint grid_size [[threads_per_grid]]
) {
    ulong m[SEINE_B2_MSG_WORDS];
    for (int i = 0; i < SEINE_B2_MSG_WORDS; ++i) {
        m[i] = params.m[i];
    }
    const ulong base_word = m[SEINE_B2_NONCE_WORD];
#if SEINE_B2_NONCE_SHIFT != 0
    const ulong base_next = m[SEINE_B2_NONCE_WORD + 1];
#endif

    for (ulong index = gid; index < nonce_count; index += grid_size) {
        const ulong nonce = start_nonce + index;
        m[SEINE_B2_NONCE_WORD] = base_word | (nonce << SEINE_B2_NONCE_SHIFT);
#if SEINE_B2_NONCE_SHIFT != 0
        m[SEINE_B2_NONCE_WORD + 1] = base_next | (nonce >> (64 - SEINE_B2_NONCE_SHIFT));
#endif

        ulong v0 = params.v[0], v1 = params.v[1], v2 = params.v[2], v3 = params.v[3];
        ulong v4 = params.v[4], v5 = params.v[5], v6 = params.v[6], v7 = params.v[7];
        ulong v8 = params.v[8], v9 = params.v[9], v10 = params.v[10], v11 = params.v[11];
        ulong v12 = params.v[12], v13 = params.v[13], v14 = params.v[14], v15 = params.v[15];

        // Round 0 (identity schedule) without the precomputed column steps.
#if !(SEINE_B2_PRE_COLUMNS & 1)
        SEINE_B2_G(v0, v4, v8, v12, SEINE_B2_M(0), SEINE_B2_M(1));
#endif
#if !(SEINE_B2_PRE_COLUMNS & 2)
        SEINE_B2_G(v1, v5, v9, v13, SEINE_B2_M(2), SEINE_B2_M(3));
#endif
#if !(SEINE_B2_PRE_COLUMNS & 4)
        SEINE_B2_G(v2, v6, v10, v14, SEINE_B2_M(4), SEINE_B2_M(5));
#endif
#if !(SEINE_B2_PRE_COLUMNS & 8)
        SEINE_B2_G(v3, v7, v11, v15, SEINE_B2_M(6), SEINE_B2_M(7));
#endif
        SEINE_B2_G(v0, v5, v10, v15, SEINE_B2_M(8), SEINE_B2_M(9));
        SEINE_B2_G(v1, v6, v11, v12, SEINE_B2_M(10), SEINE_B2_M(11));
        SEINE_B2_G(v2, v7, v8, v13, SEINE_B2_M(12), SEINE_B2_M(13));
        SEINE_B2_G(v3, v4, v9, v14, SEINE_B2_M(14), SEINE_B2_M(15));

        SEINE_B2_ROUND(14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3);
        SEINE_B2_ROUND(11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4);
        SEINE_B2_ROUND(7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8);
        SEINE_B2_ROUND(9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13);
        SEINE_B2_ROUND(2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9);
        SEINE_B2_ROUND(12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11);
        SEINE_B2_ROUND(13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10);
        SEINE_B2_ROUND(6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5);
        SEINE_B2_ROUND(10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0);
        SEINE_B2_ROUND(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15);
        SEINE_B2_ROUND(14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3);

        // Only output word 0 decides a candidate.
        const ulong out0 = params.h0 ^ v0 ^ v8;
        if (seine_bswap64(out0) <= params.target_limb0) {
            const uint slot = atomic_fetch_add_explicit(candidate_count, 1u, memory_order_relaxed);
            if (slot < candidate_capacity) {
                candidates[slot] = nonce;
            }
        }
    }
}
