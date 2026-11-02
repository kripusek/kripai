# Windows / PowerShell: sekret wpisywany lokalnie, nigdy w czacie ani argv.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$repos = (Read-Host 'Dozwolone repozytoria owner/repo oddzielone przecinkiem').Split(',') | ForEach-Object { $_.Trim().ToLowerInvariant() }
foreach ($repo in $repos) { if ($repo -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw 'Niepoprawne repozytorium' } }
$secret = Read-Host 'Fine-grained PAT: tylko wybrane repozytoria, Contents Read-only (Issues Read-only opcjonalnie)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $bytes = [Text.Encoding]::UTF8.GetBytes([Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer))
    $encrypted = [Security.Cryptography.ProtectedData]::Protect($bytes,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
    $folder = Join-Path $env:LOCALAPPDATA 'KripAI-data'
    if (!(Test-Path $folder)) { throw 'Najpierw uruchom START.cmd (prywatny folder danych z ACL).' }
    @{repositories=@($repos);credential=[Convert]::ToBase64String($encrypted)} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $folder 'github.json')
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    if ($bytes) { [Array]::Clear($bytes,0,$bytes.Length) }
}
Write-Host 'Zapisano konfigurację DPAPI. Cofnięcie dostępu: usuń github.json i unieważnij PAT w GitHub.'
