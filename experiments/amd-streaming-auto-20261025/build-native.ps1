param([Parameter(Mandatory=$true)][string]$Root, [Parameter(Mandatory=$true)][string]$Commit, [ValidateSet('all','verify')][string]$Phases = 'all')
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$env:SEINE_GIT_COMMIT = $Commit
$env:CARGO_BUILD_JOBS = '2'
$env:CARGO_TARGET_DIR = Join-Path $Root 'target'
$cargo = Join-Path $env:USERPROFILE '.cargo\bin\cargo.exe'
$statePath = Join-Path $env:LOCALAPPDATA 'GpuQ\operator-state.json'
if ($Phases -eq 'verify') { $steps = @('verify') } else { $steps = @('build','test','verify') }
foreach ($phase in $steps) {
    $arguments = @('+1.93.0', $phase, '--release', '--locked')
    if ($phase -eq 'test') { $arguments += @('--workspace', '--', '--test-threads=2') }
    if ($phase -eq 'verify') { $arguments = @('+1.93.0','build','--release','--locked','-p','blocknet-pow-kernel','--example','verify_cpu_kernels','--example','verify_streaming_dispatch') }
    $owned = $null
    try {
        $owned = Start-Process -FilePath $cargo -ArgumentList $arguments -WorkingDirectory (Join-Path $Root 'source') -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $Root "$phase.log") -RedirectStandardError (Join-Path $Root "$phase.err")
        $handle = $owned.Handle
        $owned.PriorityClass = 'BelowNormal'
        $watch = [Diagnostics.Stopwatch]::StartNew()
        while (!$owned.WaitForExit(3000)) {
            $state = Get-Content -Raw $statePath | ConvertFrom-Json
            $age = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() - $state.updatedAtUnixMs
            if ($age -gt 60000 -or $state.gamingActive) { throw 'Gaming reservation; stop owned native build' }
            if ($watch.Elapsed.TotalSeconds -gt 1200) { throw 'Native build/test deadline exceeded' }
        }
        $owned.WaitForExit()
        if ($owned.ExitCode -ne 0) { throw "$phase failed: $($owned.ExitCode)" }
        Write-Output "$phase PASS"
    } finally {
        if ($owned -and !$owned.HasExited) { & taskkill.exe /T /F /PID $owned.Id | Out-Null; $owned.WaitForExit() }
    }
}
