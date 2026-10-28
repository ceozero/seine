# Windows counterpart of remote_live_compete.sh: same-host live mining, each miner on
# its defaults, against the local all-target Stratum fixture (pool_fixture.py).
# Usage: powershell -File remote_live_compete.ps1 -Secs 900 -Miners "seine,ntmminer,longhorn"
# Expects candidate\seine.exe and extra\ (python embed zip, windows_job.py, ntm\, longhorn\,
# lego.exe). bntpool.com maps to the fixture so Seine's fee work is captured; NTM speaks
# TLS only with bundled public roots, so it gets a short-lived Let's Encrypt IP certificate
# (the lease must allow inbound port 80: aws.py --acme-http).
param([int]$Secs = 900, [string]$Miners = 'seine,ntmminer,longhorn')
$ErrorActionPreference = 'Continue'
$W = 'C:\cohort'
# Defender quarantined the NTM executable on one disposable guest; exclude the work tree.
Add-MpPreference -ExclusionPath $W -ErrorAction SilentlyContinue
$R = "$W\results\live-compete-$Secs"
New-Item -ItemType Directory -Force "$R\tls" | Out-Null
if (-not (Test-Path "$W\python\python.exe")) {
  Expand-Archive -Force "$W\extra\python-3.14.9-embed-amd64.zip" "$W\python"
  Add-Content "$W\python\python314._pth" '..' -Encoding ASCII
}
Copy-Item -Force "$W\extra\windows_job.py" "$W\windows_job.py"
if (-not (Select-String -Quiet -Path 'C:\Windows\System32\drivers\etc\hosts' -Pattern 'bntpool.com')) {
  Add-Content 'C:\Windows\System32\drivers\etc\hosts' "`r`n127.0.0.1 bntpool.com" -Encoding ASCII
}
$list = $Miners -split '[, ]+' | Where-Object { $_ }
$tlsName = $null
if ($list -contains 'ntmminer') {
  $tlsName = (Invoke-RestMethod -TimeoutSec 10 'https://checkip.amazonaws.com').Trim()
  New-NetFirewallRule -Name 'CohortAcme80' -DisplayName 'Cohort ACME HTTP-01' -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow | Out-Null
  & "$W\extra\lego.exe" run --server https://acme-v02.api.letsencrypt.org/directory --path "$W\acme" `
    --account-id seine-disposable-benchmark --http-timeout 30 --domains $tlsName --accept-tos `
    --http --http.address 0.0.0.0:80 --ipv4only --profile shortlived *> "$R\lego.log"
  Remove-NetFirewallRule -Name 'CohortAcme80'
  $crt = Get-ChildItem -Recurse "$W\acme\certificates" -Filter "$tlsName.crt" -ErrorAction SilentlyContinue | Select-Object -First 1
  $key = Get-ChildItem -Recurse "$W\acme\certificates" -Filter "$tlsName.key" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($crt -and $key) { Copy-Item $crt.FullName "$R\tls\cert.pem"; Copy-Item $key.FullName "$R\tls\key.pem" }
  else { 'ntmminer: certificate issuance failed (see lego.log)' | Tee-Object -Append "$R\summary.txt"; $list = $list | Where-Object { $_ -ne 'ntmminer' } }
}
foreach ($m in $list) {
  $tls = @(); $extra = @()
  switch ($m) {
    'seine' { $exe = "$W\candidate\seine.exe"; $extra = @('--ui', 'plain', '--data-dir', "$W\live-$m", '--telemetry', 'off') }
    # A/B on one guest: extra\base\seine.exe is the baseline build.
    'seine-base' { $exe = "$W\extra\base\seine.exe"; $extra = @('--ui', 'plain', '--data-dir', "$W\live-$m", '--telemetry', 'off') }
    'ntmminer' { $exe = "$W\extra\ntm\NTMminer-BNT.exe"; $tls = @('--tls-cert', "$R\tls\cert.pem", '--tls-key', "$R\tls\key.pem", '--tls-name', $tlsName) }
    'longhorn' { $exe = "$W\extra\longhorn\longhorn.exe" }
  }
  Remove-Item -Recurse -Force "$R\$m", "$W\live-$m" -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force "$W\live-$m" | Out-Null
  Push-Location "$W\live-$m"
  & "$W\python\python.exe" "$W\pool_fixture.py" --output "$R\$m" --seconds $Secs --warmup 0 --window-origin launch `
    --startup-timeout $Secs --listen-port 3333 --miner $m --executable $exe @tls -- @extra *> "$R\$m.out"
  Pop-Location
  & "$W\python\python.exe" "$W\live_summary.py" "$R\$m\work.json" $m $Secs | Tee-Object -Append "$R\summary.txt"
}
