$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
function Ask-File($title,$filter) {
  $d = New-Object System.Windows.Forms.OpenFileDialog
  $d.Title = $title
  $d.Filter = $filter
  $d.CheckFileExists = $true
  if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $d.FileName }
  return $null
}
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$rom = Ask-File 'awe32.raw (Original-Wave-ROM)' 'Wave-ROM (*.raw;*.rom;*.bin)|*.raw;*.rom;*.bin|Alle Dateien|*.*'
if (-not $rom) { exit 2 }
$gm = Ask-File 'SYNTHGM.SBK (Original GM-ROM-Presets)' 'SoundFont Bank (*.sbk)|*.sbk|Alle Dateien|*.*'
if (-not $gm) { exit 2 }
$sf2 = Ask-File 'Synth 512 Bank.sf2 (deine SF2)' 'SoundFont (*.sf2)|*.sf2|Alle Dateien|*.*'
if (-not $sf2) { exit 2 }
$out = Join-Path $root '125A-P112-Alle-Presets.csv'
$log = Join-Path $root '125A-P112-Testprotokoll.txt'
Write-Host 'Der ROM-GM-SF2-Hoertest laeuft lokal auf deinem PC.'
Write-Host 'ROM, SBK und SF2 werden NICHT hochgeladen oder veraendert.'
& (Join-Path $root 'awe32_p112_all_presets_audio_audit.exe') --rom $rom --gm $gm --sf2 $sf2 --out $out *> $log
$code = $LASTEXITCODE
Get-Content $log -Tail 15
if ($code -eq 0) {
  Write-Host 'Fertig. Bitte die CSV-Datei in ChatGPT hochladen:'
  Write-Host $out
  Start-Process explorer.exe -ArgumentList $root
} else {
  Write-Host 'Fehler. Bitte das Testprotokoll pruefen:'
  Write-Host $log
}
exit $code
