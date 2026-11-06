// Faraday BLAKE2b-512 PoW scan for HIP: one final-block compression per nonce
// from a host-computed starting state. hipRTC compiles this without includes;
// the host passes the header-layout defines SEINE_B2_NONCE_WORD,
// SEINE_B2_NONCE_SHIFT, SEINE_B2_MSG_WORDS and SEINE_B2_PRE_COLUMNS
// (round-0 column steps already applied to params.v, as a bit mask).

extern "C" {

typedef unsigned long long u64;
typedef unsigned int u32;

struct Blake2bPowParams {
    // Working state before round 0, with SEINE_B2_PRE_COLUMNS applied.
    u64 v[16];
    u64 m[16];
    // First chain word, for the first output word.
    u64 h0;
    // Big-endian first limb of the target; the host checks full hits exactly.
    u64 target_limb0;
};

__device__ __forceinline__ u64 seine_rotr(u64 x, u32 n) {
    return (x >> n) | (x << (64U - n));
}

#define SEINE_B2_G(a, b, c, d, x, y)        \
    do {                                     \
        a = a + b + (x);                     \
        d = seine_rotr(d ^ a, 32U);          \
        c = c + d;                           \
        b = seine_rotr(b ^ c, 24U);          \
        a = a + b + (y);                     \
        d = seine_rotr(d ^ a, 16U);          \
        c = c + d;                           \
        b = seine_rotr(b ^ c, 63U);          \
    } while (0)

// Message word i, or a literal zero the compiler folds away.
#define SEINE_B2_M(i) ((i) < SEINE_B2_MSG_WORDS ? m[(i) < SEINE_B2_MSG_WORDS ? (i) : 0] : 0ULL)

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

__global__ void blake2b_pow_scan_kernel(
    const Blake2bPowParams params,
    const u64 start_nonce,
    const u64 nonce_count,
    u64 *__restrict__ candidates,
    u32 *__restrict__ candidate_count,
    const u32 candidate_capacity
) {
    const u64 stride = (u64)gridDim.x * blockDim.x;
    u64 index = (u64)blockIdx.x * blockDim.x + threadIdx.x;

    u64 m[SEINE_B2_MSG_WORDS];
#pragma unroll
    for (int i = 0; i < SEINE_B2_MSG_WORDS; ++i) {
        m[i] = params.m[i];
    }
    const u64 base_word = m[SEINE_B2_NONCE_WORD];
#if SEINE_B2_NONCE_SHIFT != 0
    const u64 base_next = m[SEINE_B2_NONCE_WORD + 1];
#endif

    for (; index < nonce_count; index += stride) {
        const u64 nonce = start_nonce + index;
        m[SEINE_B2_NONCE_WORD] = base_word | (nonce << SEINE_B2_NONCE_SHIFT);
#if SEINE_B2_NONCE_SHIFT != 0
        m[SEINE_B2_NONCE_WORD + 1] = base_next | (nonce >> (64 - SEINE_B2_NONCE_SHIFT));
#endif

        u64 v0 = params.v[0], v1 = params.v[1], v2 = params.v[2], v3 = params.v[3];
        u64 v4 = params.v[4], v5 = params.v[5], v6 = params.v[6], v7 = params.v[7];
        u64 v8 = params.v[8], v9 = params.v[9], v10 = params.v[10], v11 = params.v[11];
        u64 v12 = params.v[12], v13 = params.v[13], v14 = params.v[14], v15 = params.v[15];

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
        const u64 out0 = params.h0 ^ v0 ^ v8;
        if (__builtin_bswap64(out0) <= params.target_limb0) {
            const u32 slot = atomicAdd(candidate_count, 1U);
            if (slot < candidate_capacity) {
                candidates[slot] = nonce;
            }
        }
    }
}

} // extern "C"
