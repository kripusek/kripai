$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$source = Split-Path $PSScriptRoot -Parent
$target = Join-Path $env:LOCALAPPDATA 'KripAI'
$data = Join-Path $env:LOCALAPPDATA 'KripAI-data'
$backups = Join-Path $env:LOCALAPPDATA 'KripAI-backups'
$mutex = New-Object Threading.Mutex($false, 'Local\KripAI-Setup')
if (-not $mutex.WaitOne(0)) { throw 'Instalator jest juz uruchomiony.' }
try {
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw 'Ta paczka wymaga Windows x64.' }
    if ((Test-Path -LiteralPath $target) -and -not (Test-Path -LiteralPath (Join-Path $target '.kripai-native'))) { throw 'Obcy folder KripAI. Nie nadpisuje go.' }
    foreach ($folder in @($target,$data,$backups)) {
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        if ((Get-Item -LiteralPath $folder).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Folder instalacji nie moze byc dowiazaniem.' }
        $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        & icacls.exe $folder /inheritance:r /grant:r "*${sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie zabezpieczyc folderu danych.' }
    }
    $python = Join-Path $target 'runtime\python\python.exe'
    if (Test-Path -LiteralPath $python) {
        & $python (Join-Path $target 'scripts\manage.py') stop
        if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie zatrzymac poprzedniej instancji.' }
    }
    Set-Content -LiteralPath (Join-Path $target '.kripai-native') -Value 'KripAI-native-v1' -Encoding ASCII
    if ([IO.Path]::GetFullPath($source) -ne [IO.Path]::GetFullPath($target)) {
        Get-ChildItem -LiteralPath $source -Force | Where-Object { $_.Name -notin @('runtime','reports','.git','.kripai-native') } | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $target -Force -Recurse
        }
    }
    Write-Host 'Przygotowuje prywatny Python (bez zmiany systemowego PATH)...'
    $archive = Join-Path $target 'vendor\python-3.13.17-embed-amd64.zip'
    if (-not (Test-Path -LiteralPath $archive)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $archive -Parent) | Out-Null
        $partialPython = $archive + '.part'
        try {
            Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip' -OutFile $partialPython
            if ((Get-FileHash -LiteralPath $partialPython -Algorithm SHA256).Hash.ToLowerInvariant() -ne '9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38') { throw 'Uszkodzone pobranie Python.' }
            Move-Item -LiteralPath $partialPython -Destination $archive -Force
        } finally {
            Remove-Item -LiteralPath $partialPython -Force -ErrorAction SilentlyContinue
        }
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne '9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38') { throw 'Uszkodzona paczka Python.' }
    $runtime = Join-Path $target 'runtime\python'
    New-Item -ItemType Directory -Force -Path $runtime | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $runtime -Force
    Set-Content -LiteralPath (Join-Path $runtime 'python313._pth') -Encoding ASCII -Value @('python313.zip','.','..\deps','..\..','import site')
    $missingRuntime = @("msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll") | Where-Object { -not (Test-Path -LiteralPath (Join-Path "$env:WINDIR\System32" $_)) }
    if ($missingRuntime) {
        Write-Host 'Instaluje oficjalny runtime Microsoft Visual C++; Windows moze poprosic o zgode.'
        $redist = Join-Path $target 'runtime\vc_redist.x64.exe'
        Invoke-WebRequest -UseBasicParsing 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile $redist
        $signature = Get-AuthenticodeSignature -LiteralPath $redist
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') { throw 'Nieprawidlowy podpis instalatora Microsoft.' }
        $process = Start-Process -FilePath $redist -ArgumentList '/install','/quiet','/norestart' -Wait -PassThru
        if ($process.ExitCode -notin @(0,1638,3010)) { throw 'Instalacja Visual C++ nie powiodla sie.' }
    }
    & $python (Join-Path $target 'scripts\downloads.py') deps
    if ($LASTEXITCODE -ne 0) { throw 'Instalacja bibliotek przerwana.' }
    Write-Host 'Testuje SQLite, API i obsluge awarii na oddzielnych danych...'
    & $python (Join-Path $target 'scripts\test_all.py')
    if ($LASTEXITCODE -ne 0) { throw 'Testy nie przeszly. Raport jest w folderze reports.' }
    & $python (Join-Path $target 'scripts\downloads.py') model
    if ($LASTEXITCODE -ne 0) { throw 'Przygotowanie CUDA/modelu przerwane. Uruchom START ponownie po poprawieniu przyczyny.' }
    & $python (Join-Path $target 'scripts\downloads.py') voice
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Modul glosu niegotowy. Czat tekstowy nadal moze dzialac; START ponowi pobranie.' }
    & $python (Join-Path $target 'scripts\downloads.py') vision
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Model obrazu niegotowy. Czat i podglad plikow nadal dostepne; START ponowi pobranie.' }
    & $python (Join-Path $target 'scripts\manage.py') start
    if ($LASTEXITCODE -ne 0) { throw 'Uruchomienie nie powiodlo sie.' }
    Start-Process 'http://localhost:8765'
    Write-Host 'KripAI uruchomione. Tryb gry zmieniasz w panelu; WYLACZ.cmd zamyka program.'
} catch {
    Write-Host ('BLAD: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    $mutex.ReleaseMutex();$mutex.Dispose()
}
