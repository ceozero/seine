# RAM guide evidence — October 26, 2026 (EDT)

Intent: choose a cross-platform CPU memory budget and diagnose allocation failures.
Adjacent hardware, Argon2id, Mac and huge-pages guides retain chip comparisons,
algorithm theory, Mac-specific setup and page configuration respectively.

Reviewed public release: v0.2.26, commit 899ff7ea8bd547163ae48d636f569a0a8c7e25bb.
- `pow-spec/src/lib.rs:9`: CPU_LANE_MEMORY_BYTES = POW_MEMORY_KB * 1024, 2 GiB.
- `src/config.rs:393-401`: threads, reserve flag, default 5%, explicit override.
- `src/config.rs:476-494`: automatic tuning and maximum-thread options.
- `src/config.rs:2836-2872`: automatic selection, CPU/resource caps and available
  memory minus reserve based on effective total memory.
- `src/config.rs:2880-2930`: checks against total and available memory.
- `src/config.rs:3025-3195`: Linux effective memory and cgroup constraints.
- `src/backend/cpu/kernel.rs` and `src/config.rs:58-66`: arenas and page allocation/fallback contract.
- `docs/guides/nvidia.md`: discrete VRAM arena sizing.
- `docs/guides/configuration.md`: CLI/persisted configuration semantics.

Sources are pinned to the public release; pending master optimizations are not
represented as shipped behavior. No benchmark or mining job was run. The 1/2/4/8/16
thread table and 16 - 4 = 12 GiB / 2 = 6 example are arithmetic only. 2 GiB equals
2,147,483,648 bytes. A 1 GiB process allowance cannot hold one arena. Swap is not
presented as extra physical RAM. Explicit page modes require requested backing.
The SVG is a code-native editorial diagram: four 2 GiB arenas and separately
shown system/application space, not a measured memory-use screenshot.

All translations authored with the active model, no external translation API.
They remain draft; independent review is optional and not claimed. User authorized
publication. Related-link metadata added to hardware and dashboard articles;
their translated prose is unchanged and only source hashes are refreshed.

## Verification

Strict source and all 19 translation checks passed. Three existing site tests passed; Astro built 602 pages.
All 20 new localized pages passed metadata, canonical/hreflang, FAQ/schema, image and internal-anchor checks. Desktop/mobile English, Arabic and Thai, tables, graphics and existing blog lists were inspected through Windows Playwright. Language menus close on outside click. No page-level horizontal overflow was observed; long commands scroll inside their code block. The browser extension ethereum injection error is unrelated to the app. The static pool preview uses the API favicon constant for its favicon route.

Showcase: http://localhost:8874/ram-and-shares/ (source revisions, captures and live verification). These are static article pages; loading, empty, error and disabled application states are not part of this content change.
