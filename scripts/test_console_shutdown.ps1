param([Parameter(Mandatory=$true)][string]$Probe)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Join-Path ([IO.Path]::GetTempPath()) ('seine-console-test-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
try {
    foreach ($mode in @('legacy', 'fixed', 'stuck', 'interrupt', 'forced-interrupt')) {
        $dir = Join-Path $root $mode
        New-Item -ItemType Directory -Path $dir | Out-Null
        $timer = [Diagnostics.Stopwatch]::StartNew()
        $p = Start-Process -FilePath $Probe -ArgumentList @(('"' + $dir + '"'), $mode) -PassThru -WindowStyle Hidden
        try {
            if (!$p.WaitForExit(12000)) { throw "Probe $mode exceeded deadline" }
            $timer.Stop()
            $running = Test-Path (Join-Path $dir 'running')
            $completed = Test-Path (Join-Path $dir 'completed')
            $requestFile = Join-Path $dir 'request.json'
            $request = if (Test-Path $requestFile) { [IO.File]::ReadAllText($requestFile) | ConvertFrom-Json } else { $null }
            [pscustomobject]@{mode=$mode; elapsed_ms=$timer.ElapsedMilliseconds; exit=$p.ExitCode; unfinished=$running; completed=$completed; request=$request} | ConvertTo-Json -Compress
            if ($mode -in @('fixed', 'interrupt')) {
                if ($running -or !$completed -or $p.ExitCode -ne 0) { throw "Cleanup failed: $mode" }
            } elseif (!$running -or $completed) { throw "Expected interrupted marker: $mode" }
            if ($mode -in @('fixed', 'stuck') -and $request -ne 'console_close') { throw 'Missing close request' }
            if ($mode -in @('interrupt', 'forced-interrupt') -and $request -ne 'interrupt') { throw 'Missing interrupt request' }
            if ($mode -eq 'forced-interrupt' -and $p.ExitCode -ne 130) { throw 'Second interrupt did not force exit' }
            if ($mode -eq 'stuck' -and ($timer.ElapsedMilliseconds -lt 3500 -or $timer.ElapsedMilliseconds -gt 8000)) { throw 'Unbounded or missing close grace' }
        } finally {
            if (!$p.HasExited) { $p.Kill(); $p.WaitForExit(3000) | Out-Null }
            $p.Dispose()
        }
    }
} finally {
    Remove-Item -Recurse -Force $root
}
