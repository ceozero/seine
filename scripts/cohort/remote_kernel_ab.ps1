# Windows kernel A/B: full-size parity, then one ABBA pair per thread count.
# Usage: powershell -File remote_kernel_ab.ps1 -Base avx2 -Cand avx2-stream -Threads 16,24
# (-File passes "16,24" as one string, so it is split here.)
param([string]$Base, [string]$Cand, [string]$Threads, [int]$Secs = 20)
$ThreadList = $Threads -split '[, ]+' | Where-Object { $_ } | ForEach-Object { [int]$_ }
$W = 'C:\cohort'
$R = "$W\results\ab-$Base-vs-$Cand"
New-Item -ItemType Directory -Force $R | Out-Null
& "$W\candidate\verify_cpu_kernels.exe" *> "$R\parity.log"
if (-not (Select-String -Path "$R\parity.log" -Pattern "^${Cand}: PASS" -Quiet)) {
  'PARITY-FAILED' | Tee-Object "$R\summary.txt"; New-Item "$W\AB-DONE" -ItemType File -Force | Out-Null; exit 1
}
function One($kernel, $threads, $tag) {
  & "$W\candidate\seine.exe" --bench --bench-kind backend --backend cpu --ui plain --data-dir "$W\data-ab" `
    --threads $threads --disable-cpu-autotune-threads --bench-cpu-kernel $kernel `
    --bench-secs $Secs --bench-rounds 1 --bench-warmup-rounds 1 --bench-output "$R\$tag.json" *> "$R\$tag.log"
  $d = Get-Content "$R\$tag.json" -Raw | ConvertFrom-Json
  "$tag $([math]::Round($d.avg_hps, 3))"
}
$out = foreach ($t in $ThreadList) {
  One $Base $t "t$t-1-$Base"; One $Cand $t "t$t-2-$Cand"; One $Cand $t "t$t-3-$Cand"; One $Base $t "t$t-4-$Base"
}
$out | Tee-Object "$R\summary.txt"
New-Item "$W\AB-DONE" -ItemType File -Force | Out-Null
