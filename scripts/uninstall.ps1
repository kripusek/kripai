$ErrorActionPreference = 'Stop'
$target = Join-Path $env:LOCALAPPDATA 'KripAI'
$data = Join-Path $env:LOCALAPPDATA 'KripAI-data'
if (-not (Test-Path -LiteralPath (Join-Path $target '.kripai-native'))) { throw 'Brak oznaczonej instalacji KripAI.' }
foreach ($folder in @($target,$data)) {
    if ((Test-Path -LiteralPath $folder) -and ((Get-Item -LiteralPath $folder).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Odmowa usuwania dowiazania.' }
}
$mutex = New-Object Threading.Mutex($false, 'Local\KripAI-Setup')
if (-not $mutex.WaitOne(0)) { throw 'Instalator lub odinstalowanie jest juz uruchomione.' }
try {
$answer = Read-Host 'Odinstalowac program? Wpisz TAK (rozmowy i modele pozostana)'
if ($answer -cne 'TAK') { exit 0 }
$python = Join-Path $target 'runtime\python\python.exe'
& $python (Join-Path $target 'scripts\manage.py') stop
if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie bezpiecznie zatrzymac programu.' }
if (Test-Path -LiteralPath (Join-Path $data 'kripai.sqlite3')) {
    & $python (Join-Path $target 'scripts\manage.py') backup
    if ($LASTEXITCODE -ne 0) { throw 'Brak potwierdzonej kopii. Odinstalowanie wstrzymane.' }
}
$erase = Read-Host 'Opcjonalnie wpisz USUN DANE, aby usunac tez rozmowy i modele. Enter zachowuje dane'
Remove-Item -LiteralPath $target -Recurse -Force
if ($erase -ceq 'USUN DANE') { Remove-Item -LiteralPath $data -Recurse -Force }
Write-Host 'Odinstalowano program. Kopie w %LOCALAPPDATA%\KripAI-backups pozostaly.'

} finally { $mutex.ReleaseMutex();$mutex.Dispose() }
