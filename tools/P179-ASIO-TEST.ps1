#requires -Version 5.1
# P179: true hardware ASIO + MIDI/PCM from actual AWE VST3, LOCAL ONLY.
# Never silently installs a driver, copies original ROM/SF2 or uploads media.
[CmdletBinding()] param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$exe=Join-Path $root '125A-Test-Lab-ASIO-MIDI.exe'
$dll=Join-Path $root '125A_AWE_Synthesizer.vst3\Contents\x86_64-win\125A_AWE_Synthesizer.vst3'
$out=Join-Path $root ('P179-LOCAL-RESULT-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
$reportFile=Join-Path $out 'P179-ACCEPTANCE.json'
$report=@{schema='125a-p179-local-awe-asio-v1';status='NOT_RUN';
  original_rom_sf2='LOCAL_NOT_UPLOADED';daw_session_verified=$false;
  release_approved=$false;physical_asio_verified=$false;
  native_midi_audio_verified=$false;errors=@()}
function Publish { $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportFile -Encoding UTF8 }
function ReadPath([string]$title) {
  $inputPath=Read-Host $title
  return ($inputPath.Trim().Trim([char]34))
}
$oldRom=$env:AWE32_ROM_PATH
$oldSf2=$env:AWE32_SF2_PATH
try {
  if (-not [Environment]::Is64BitProcess) { throw 'Bitte eine 64-Bit-Windows-PowerShell verwenden.' }
  if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'ASIO-Testprogramm fehlt im Paket.' }
  if (-not (Test-Path -LiteralPath $dll -PathType Leaf)) { throw 'AWE-VST3-Modul fehlt im Paket.' }
  $rom=ReadPath 'Original AWE32-ROM (*.raw), voller Pfad'
  $sf2=ReadPath 'Original SoundFont (*.sf2), voller Pfad'
  if (-not (Test-Path -LiteralPath $rom -PathType Leaf)) { throw 'Die angegebene ROM-Datei existiert nicht.' }
  if ((Get-Item -LiteralPath $rom).Length -ne 1048576) { throw 'Die ROM muss genau 1.048.576 Bytes gross sein (keine Echtheitsgarantie).' }
  if (-not (Test-Path -LiteralPath $sf2 -PathType Leaf) -or [IO.Path]::GetExtension($sf2).ToLowerInvariant() -ne '.sf2') { throw 'Die SF2 existiert nicht oder ist ungueltig.' }
  $driverRoot='Registry::HKEY_LOCAL_MACHINE\SOFTWARE\ASIO'
  if (-not (Test-Path -LiteralPath $driverRoot)) { throw 'Keine Windows-ASIO-Treiberregistrierung vorhanden.' }
  $drivers=@(Get-ChildItem -LiteralPath $driverRoot | ForEach-Object {
    $driver=$_.PSChildName
    $props=Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue
    $clsidValue=if($props -and $props.PSObject.Properties['CLSID']){[string]$props.CLSID}else{''}
    if($clsidValue -match '^\{[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\}$') {
      [PSCustomObject]@{Name=$driver;CLSID=$clsidValue}
    }
  })
  if ($drivers.Count -eq 0) { throw 'Kein gueltig registrierter Windows-ASIO-Treiber gefunden.' }
  $audient=@($drivers | Where-Object {$_.Name -match '(?i)audient|id14|id\s*driver'})
  if ($audient.Count -eq 1) {
    $selected=$audient[0]
    Write-Host ('ASIO-Treiber automatisch erkannt: '+$selected.Name)
  } elseif ($drivers.Count -eq 1) {
    $selected=$drivers[0]
  } else {
    Write-Host 'Installierte echte ASIO-Treiber:'
    for($i=0;$i -lt $drivers.Count;$i++){Write-Host ('  '+($i+1)+': '+$drivers[$i].Name)}
    $choice=Read-Host 'Nummer des Audiointerface-ASIO-Treibers'
    $number=0
    if(-not [int]::TryParse($choice,[ref]$number) -or $number -lt 1 -or $number -gt $drivers.Count) { throw 'Ungueltige ASIO-Treiberwahl.' }
    $selected=$drivers[$number-1]
  }
  Write-Host ''
  Write-Host 'Dieser Test nutzt den ECHTEN ASIO-Treiber und spielt MIDI-Note 48.'
  Write-Host 'Bitte DAW schliessen und Monitor-/Kopfhoererlautstaerke absenken.'
  Write-Host 'Sicherheitsgrenze am ASIO-Ausgang: -20 dBFS Peak.'
  $consent=Read-Host 'Mit Enter starten, mit N abbrechen'
  if($consent.Trim() -ne ''){throw 'Benutzer hat ASIO-Test nicht gestartet.'}
  $moduleHash=(Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant()
  $executorHash=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
  $manifestFile=Join-Path $root 'P179-SHA256SUMS.txt'
  if(-not (Test-Path -LiteralPath $manifestFile -PathType Leaf)){throw 'P179-SHA256SUMS.txt fehlt.'}
  $checks=Get-Content -LiteralPath $manifestFile
  if(-not ($checks -contains ($moduleHash+'  125A_AWE_Synthesizer.vst3')) -or
     -not ($checks -contains ($executorHash+'  125A-Test-Lab-ASIO-MIDI.exe'))) {
    throw 'P179-Binaerdateien stimmen nicht mit dem verifizierten SHA256-Paket ueberein.'
  }
  $random=[byte[]]::new(24)
  $rng=[System.Security.Cryptography.RandomNumberGenerator]::Create()
  try{$rng.GetBytes($random)}finally{$rng.Dispose()}
  $nonce=([BitConverter]::ToString($random)).Replace('-','').ToLowerInvariant()
  # Query the installed IASIO driver before audio: do not guess 256 frames.
  $capsPath=Join-Path $out 'ASIO-DRIVER-CAPABILITIES.json'
  $capArgs=@('--asio-buffer-capabilities','--driver-name',$selected.Name,
    '--driver-clsid',$selected.CLSID,'--nonce',$nonce,'--out',$capsPath)
  & $exe @capArgs 2>&1 | Tee-Object -FilePath (Join-Path $out 'ASIO-CAPABILITY-LOG.txt')
  if($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $capsPath -PathType Leaf)){
    throw 'Echter ASIO-Treiber konnte keine Puffer-/Sampleraten-Auskunft liefern.'
  }
  $caps=Get-Content -LiteralPath $capsPath -Raw | ConvertFrom-Json
  if($caps.schema -cne '125a-asio-driver-capability-v1' -or
     $caps.nonce -cne $nonce -or $caps.driver_name -cne $selected.Name -or
     $caps.driver_clsid -ine $selected.CLSID -or
     $caps.executor_sha256 -cne $executorHash -or
     [bool]$caps.physical_audio_callbacks -or [bool]$caps.release_approved){
    throw 'ASIO-Geraeteauskunft hat ungueltige Identitaet, Sitzung oder Herkunft.'
  }
  $frames=[int]$caps.selected_frames
  $rate=[int]$caps.selected_rate
  $minimum=[int]$caps.minimum_frames
  $maximum=[int]$caps.maximum_frames
  $preferred=[int]$caps.preferred_frames
  $step=[int]$caps.granularity
  $validFrames=$frames -ge 64 -and $frames -le 4096 -and
    $minimum -gt 0 -and $maximum -ge $minimum -and
    $frames -ge $minimum -and $frames -le $maximum -and (
    ($step -eq -1 -and ($frames -band ($frames-1)) -eq 0) -or
    ($step -eq 0 -and $frames -eq $preferred) -or
    ($step -gt 0 -and (($frames-$minimum) % $step) -eq 0))
  if(-not $validFrames){throw 'Ungestuetze ASIO-Puffergroesse vom Treiber gemeldet.'}
  if(-not (($rate -eq 44100 -and $caps.rate_44100) -or
           ($rate -eq 48000 -and $caps.rate_48000) -or
           ($rate -eq 96000 -and $caps.rate_96000))){
    throw 'ASIO-Samplerate nicht vom Treiber bestaetigt.'
  }
  Write-Host ('ASIO-Treiber bestaetigt '+$frames+' Samples bei '+$rate+' Hz; bevorzugt '+$preferred+'.')
  $asioPath=Join-Path $out 'ASIO-CALLBACKS.json'
  $midiPath=Join-Path $out 'ASIO-MIDI-PCM.json'
  $env:AWE32_ROM_PATH=$rom
  $env:AWE32_SF2_PATH=$sf2
  $args=@('--physical-asio-probe','--plugin',$dll,'--driver-name',$selected.Name,
    '--driver-clsid',$selected.CLSID,'--rate',([string]$rate),'--frames',([string]$frames),
    '--callbacks','1000','--nonce',$nonce,'--out',$asioPath,
    '--midi-note','48','--midi-out',$midiPath)
  & $exe @args 2>&1 | Tee-Object -FilePath (Join-Path $out 'NATIVE-HOST-LOG.txt')
  if($LASTEXITCODE -ne 0){throw ('Echter ASIO-Host FAIL (Exitcode '+$LASTEXITCODE+'). Siehe NATIVE-HOST-LOG.txt')}
  if(-not (Test-Path $asioPath) -or -not (Test-Path $midiPath)){throw 'Echte ASIO- und MIDI-PCM-Beweisdateien fehlen.'}
  $asio=Get-Content -LiteralPath $asioPath -Raw | ConvertFrom-Json
  $midi=Get-Content -LiteralPath $midiPath -Raw | ConvertFrom-Json
  if($asio.schema -cne '125a-physical-asio-native-evidence-v1' -or
     $midi.schema -cne '125a-physical-asio-instrument-midi-v1' -or
     $asio.nonce -cne $nonce -or $midi.nonce -cne $nonce -or
     $asio.product_sha256 -cne $moduleHash -or $midi.product_sha256 -cne $moduleHash -or
     $asio.executor_sha256 -cne $executorHash -or $midi.executor_sha256 -cne $executorHash -or
     $asio.asio_driver_name -cne $selected.Name -or $midi.asio_driver_name -cne $selected.Name -or
     [int]$asio.sample_rate -ne $rate -or [int]$asio.buffer_frames -ne $frames -or
     [int]$asio.completed_callbacks -lt 1000 -or [int]$asio.asio_callbacks -lt 1000 -or
     [int]$asio.asio_callbacks -ne [int]$asio.completed_callbacks -or
     [int]$asio.deadline_misses -ne 0 -or [int]$asio.xruns -ne 0 -or
     [int]$asio.process_failures -ne 0 -or [int]$asio.error_code -ne 0 -or
     [int]$midi.midi_note -ne 48 -or [int]$midi.note_ons -lt 1 -or
     [int]$midi.note_offs -lt 1 -or [int]$midi.nonzero_pcm_samples -lt 100 -or
     [double]$midi.peak_before_safety_ceiling -le 0.0001) {
    throw 'ASIO-/MIDI-Nachweise sind falsch, unvollstaendig oder ohne Klang.'
  }
  $report.status='PHYSICAL_ASIO_MIDI_PCM_PASS'
  $report.physical_asio_verified=$true
  $report.native_midi_audio_verified=$true
  $report.driver=$selected.Name
  $report.sample_rate=$rate
  $report.buffer_frames=$frames
  $report.driver_preferred_frames=$preferred
  $report.capability_query='REAL_IASIO_GETBUFFERSIZE'
  $report.callbacks=[int]$asio.asio_callbacks
  $report.midi_notes=[int]$midi.note_ons
  $report.pcm_peak=[double]$midi.peak_before_safety_ceiling
  $report.module_sha256=$moduleHash
  $report.executor_sha256=$executorHash
  Write-Host 'PASS: Echter ASIO-Callback und MIDI-Klang deiner Originaldateien verifiziert.'
} catch {
  $report.status='NOT_RUN_OR_FAIL'
  $report.errors=@($_.Exception.Message)
  Write-Host ('ASIO-NO-GO: '+$_.Exception.Message) -ForegroundColor Red
} finally {
  [Environment]::SetEnvironmentVariable('AWE32_ROM_PATH',$oldRom,'Process')
  [Environment]::SetEnvironmentVariable('AWE32_SF2_PATH',$oldSf2,'Process')
  Publish
  Write-Host ('Ergebnis: '+$reportFile)
}
if($report.status -ceq 'PHYSICAL_ASIO_MIDI_PCM_PASS'){exit 0}
exit 1
