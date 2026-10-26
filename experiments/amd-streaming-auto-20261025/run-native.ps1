param([Parameter(Mandatory=$true)][string]$Root, [Parameter(Mandatory=$true)][string]$JobId)
$ErrorActionPreference = 'Stop'
$owned = $null
try {
    $arguments = @((Join-Path $Root 'native_run.py'), '--root', $Root, '--job', $JobId)
    $owned = Start-Process -FilePath (Get-Command py.exe).Source -ArgumentList $arguments -WorkingDirectory $Root -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $Root 'native-driver.log') -RedirectStandardError (Join-Path $Root 'native-driver.err')
    $handle = $owned.Handle
    $watch = [Diagnostics.Stopwatch]::StartNew()
    while (!$owned.WaitForExit(3000)) {
        if ($watch.Elapsed.TotalSeconds -gt 2760) { throw 'Independent native controller deadline' }
    }
    $owned.WaitForExit()
    if ($owned.ExitCode -ne 0) { throw "Native campaign failed: $($owned.ExitCode)" }
} finally {
    if ($owned -and !$owned.HasExited) { & taskkill.exe /T /F /PID $owned.Id | Out-Null; $owned.WaitForExit() }
}
