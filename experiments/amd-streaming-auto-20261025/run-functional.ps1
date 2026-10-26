param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference='Stop'
$owned=$null
try {
    $owned=Start-Process -FilePath (Get-Command py.exe).Source -ArgumentList @((Join-Path $Root 'functional_probe.py'),'--root',$Root) -WorkingDirectory $Root -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $Root 'driver.log') -RedirectStandardError (Join-Path $Root 'driver.err')
    $handle=$owned.Handle
    $watch=[Diagnostics.Stopwatch]::StartNew()
    while (!$owned.WaitForExit(3000)) {
        if ($watch.Elapsed.TotalSeconds -gt 390) { throw 'Independent functional-test deadline exceeded' }
    }
    $owned.WaitForExit()
    if ($owned.ExitCode -ne 0) { throw "Functional test failed: $($owned.ExitCode)" }
} finally {
    if ($owned -and !$owned.HasExited) { & taskkill.exe /T /F /PID $owned.Id | Out-Null; $owned.WaitForExit() }
}
