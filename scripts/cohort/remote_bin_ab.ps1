# Windows binary A/B: same kernel, extra\base\seine.exe vs candidate\seine.exe.
# Usage: powershell -File remote_bin_ab.ps1 -Kernel avx512-stream -Threads 14
# Full-size parity of the candidate runs first; one ABBA pair per thread count.
param([string]$Kernel, [string]$Threads, [int]$Secs = 20)
$ThreadList = $Threads -split '[, ]+' | Where-Object { $_ } | ForEach-Object { [int]$_ }
$W = 'C:\cohort'
$R = "$W\results\bin-ab-$Kernel"
New-Item -ItemType Directory -Force $R | Out-Null
& "$W\candidate\verify_cpu_kernels.exe" *> "$R\parity.log"
if (-not (Select-String -Path "$R\parity.log" -Pattern "^${Kernel}: PASS" -Quiet)) {
  'PARITY-FAILED' | Tee-Object "$R\summary.txt"; exit 1
}
function One($exe, $threads, $tag) {
  & $exe --bench --bench-kind backend --backend cpu --ui plain --data-dir "$W\data-ab" `
    --threads $threads --disable-cpu-autotune-threads --bench-cpu-kernel $Kernel `
    --bench-secs $Secs --bench-rounds 1 --bench-warmup-rounds 1 --bench-output "$R\$tag.json" *> "$R\$tag.log"
  $d = Get-Content "$R\$tag.json" -Raw | ConvertFrom-Json
  "$tag $([math]::Round($d.avg_hps, 3))"
}
$base = "$W\extra\base\seine.exe"
$cand = "$W\candidate\seine.exe"
$out = foreach ($t in $ThreadList) {
  One $base $t "t$t-1-base"; One $cand $t "t$t-2-cand"; One $cand $t "t$t-3-cand"; One $base $t "t$t-4-base"
}
$out | Tee-Object "$R\summary.txt"
