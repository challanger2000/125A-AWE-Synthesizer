$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
function Choose-File($title,$filter) {
  $d = New-Object System.Windows.Forms.OpenFileDialog
  $d.Title = $title
  $d.Filter = $filter
  if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $d.FileName }
  return $null
}
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$rom = Choose-File 'Originale AWE32/AWE64 Wave-ROM auswaehlen' 'Wave-ROM (*.raw;*.rom;*.bin)|*.raw;*.rom;*.bin|Alle Dateien|*.*'
if (-not $rom) { exit 2 }
$sf2 = Choose-File 'Deine Synth 512 Bank.sf2 auswaehlen' 'SoundFont (*.sf2)|*.sf2|Alle Dateien|*.*'
if (-not $sf2) { exit 2 }
$out = Join-Path $root '125A-P109-Preset-Audit.csv'
$log = Join-Path $root '125A-P109-Testprotokoll.txt'
& (Join-Path $root 'awe32_p109_sf2_preset_audit.exe') --rom $rom --sf2 $sf2 --out $out *> $log
$code = $LASTEXITCODE
Get-Content $log -Tail 12
if ($code -eq 0) {
  Write-Host 'FERTIG. Bitte NUR die CSV-Datei hier in ChatGPT hochladen:'
  Write-Host $out
  Start-Process explorer.exe -ArgumentList $root
} else {
  Write-Host 'Test fehlgeschlagen. Fehlerprotokoll:' 
  Write-Host $log
}
exit $code
