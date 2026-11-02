param([Parameter(Mandatory=$true)][string]$InputFile,
      [Parameter(Mandatory=$true)][string]$OutputFile)
$ErrorActionPreference = 'Stop'
$synth = $null
try {
    Add-Type -AssemblyName System.Speech
    $request = [IO.File]::ReadAllText($InputFile, [Text.Encoding]::UTF8) | ConvertFrom-Json
    if ($request.language -notin @('pl','en') -or $request.text.Length -gt 1200 -or [string]::IsNullOrWhiteSpace($request.text)) { exit 2 }
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $voices = @($synth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Name -like 'Microsoft *' -and $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq $request.language })
    if ($voices.Count -eq 0) { exit 3 }
    $synth.SelectVoice($voices[0].VoiceInfo.Name)
    $synth.SetOutputToWaveFile($OutputFile)
    # Speak traktuje treść jako tekst. Nie używamy SpeakSsml ani Invoke-Expression.
    $synth.Speak([string]$request.text)
    $synth.SetOutputToNull()
} catch {
    # Wyjątki silnika mogą zawierać czytany tekst: nie wypisujemy ich do logu.
    exit 4
} finally {
    if ($null -ne $synth) { $synth.Dispose() }
}
