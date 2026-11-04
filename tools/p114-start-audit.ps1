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
$rom = AskFile 'P114: Original Wave-ROM (awe32.raw)' 'Wave-ROM (*.raw;*.rom;*.bin)|*.raw;*.rom;*.bin|Alle Dateien|*.*'
if (-not $rom) { Write-Host 'Abgebrochen: ROM nicht ausgewaehlt.'; exit 2 }
$gm = AskFile 'P114: Original GM-Beschreibung (SYNTHGM.SBK)' 'SoundFont 1 (*.sbk)|*.sbk|Alle Dateien|*.*'
if (-not $gm) { Write-Host 'Abgebrochen: GM-Bank nicht ausgewaehlt.'; exit 2 }
$sf2 = AskFile 'P114: Synth 512 Bank.sf2 (77 Presets)' 'SoundFont 2 (*.sf2)|*.sf2|Alle Dateien|*.*'
if (-not $sf2) { Write-Host 'Abgebrochen: SF2 nicht ausgewaehlt.'; exit 2 }
$out = Join-Path $root '125A-P114-Rohpegel-Diagnose.csv'
$log = Join-Path $root '125A-P114-Diagnoseprotokoll.txt'
Write-Host 'P114: 32-Bit-Rohpegel vor 16-Bit-Begrenzung (11 Sounds x 3 Velocities).'
Write-Host 'Die drei Klangdateien bleiben lokal. Audio/DSP wird nicht veraendert.'
& (Join-Path $root 'awe32_p114_raw_32bit_audit.exe') --rom $rom --gm $gm --sf2 $sf2 --out $out *> $log
$code = $LASTEXITCODE
Get-Content $log -Tail 16
if ($code -eq 0) {
  Write-Host 'Fertig. Bitte nur die CSV-Datei hier hochladen:'
  Write-Host $out
  Start-Process explorer.exe -ArgumentList $root
} else {
  Write-Host 'P114 Fehler. Bitte das Testprotokoll hier hochladen:'
  Write-Host $log
}
exit $code
