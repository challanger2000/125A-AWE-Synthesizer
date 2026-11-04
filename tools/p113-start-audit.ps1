$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
function AskFile($title, $filter) {
  $dialog = New-Object System.Windows.Forms.OpenFileDialog
  $dialog.Title = $title
  $dialog.Filter = $filter
  $dialog.CheckFileExists = $true
  if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    return $dialog.FileName
  }
  return $null
}
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$rom = AskFile 'P113: Original Wave-ROM (awe32.raw)' 'Wave-ROM (*.raw;*.rom;*.bin)|*.raw;*.rom;*.bin|Alle Dateien|*.*'
if (-not $rom) { Write-Host 'Abgebrochen: ROM nicht ausgewaehlt.'; exit 2 }
$gm = AskFile 'P113: Original GM-Beschreibung (SYNTHGM.SBK)' 'SoundFont 1 (*.sbk)|*.sbk|Alle Dateien|*.*'
if (-not $gm) { Write-Host 'Abgebrochen: GM-Bank nicht ausgewaehlt.'; exit 2 }
$sf2 = AskFile 'P113: Synth 512 Bank.sf2 (77 Presets)' 'SoundFont 2 (*.sf2)|*.sf2|Alle Dateien|*.*'
if (-not $sf2) { Write-Host 'Abgebrochen: SF2 nicht ausgewaehlt.'; exit 2 }
$out = Join-Path $root '125A-P113-Pegel-Diagnose.csv'
$log = Join-Path $root '125A-P113-Diagnoseprotokoll.txt'
Write-Host 'Pruefe 9 auffaellige Presets + 2 Kontrollen bei 64/100/127 Velocity.'
Write-Host 'Alle Dateien bleiben lokal. Kein Upload von ROM/SF2/SBK oder Audio.'
& (Join-Path $root 'awe32_p113_sf2_output_rail_diagnostic.exe') --rom $rom --gm $gm --sf2 $sf2 --out $out *> $log
$code = $LASTEXITCODE
Get-Content $log -Tail 16
if ($code -eq 0) {
  Write-Host 'Fertig: bitte NUR diese CSV hier im Chat hochladen:'
  Write-Host $out
  Start-Process explorer.exe -ArgumentList $root
} else {
  Write-Host 'Fehler: bitte das Diagnoseprotokoll hochladen:'
  Write-Host $log
}
exit $code
