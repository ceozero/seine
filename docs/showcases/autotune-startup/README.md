# Autotune startup explanations

Showcase URL: http://localhost:8770/

From the repository root:

```sh
python3 -m http.server 8770 --directory docs/showcases/autotune-startup
```

`index.html` renders the real Ratatui log component with fixture messages at
120-column desktop and 48-column mobile terminal widths. It covers empty,
invalid, unreadable and incompatible caches; build, hardware, runtime, topology,
compiler and settings changes; cache reuse; explicit overrides; NVIDIA fallback;
and live CPU startup with and without available RAM. CPU benchmark-only expiry
and live-measurement rejection are shown separately. Source blob IDs label the
captured revision. Desktop and mobile screenshots were captured and reviewed
through the shared Playwright MCP at 1100 px and 390 px.

CPU mining keeps its live tuning behavior. NVIDIA keeps its startup tuning and
memory-budget compatibility fallback. Diagnostics report the first applicable
mismatch, comparing NVIDIA records only with the same GPU identity. They do not
print fingerprints, cache contents, addresses or credentials. The separate live
CPU kernel-cache controller is unchanged.

Regenerate after changing the messages or renderer:

```sh
cargo +1.93.0 test --locked -p seine export_autotune_showcase -- --ignored
```

Then refresh both browser captures. The generator checks that fixture reasons
still exist in the production sources. These fixtures verify presentation; they
do not run CPU/GPU mining or claim hardware performance validation.
