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
  native_midi_audio_verified=$false;diagnostics_verified=$false;timing_trace_verified=$false;errors=@()}
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
  if (-not (Test-Path -LiteralPath (Join-Path $root 'P179-NATIVE-CALL.ps1') -PathType Leaf)) { throw 'Verifizierter P179-Native-Wrapper fehlt.' }
  . (Join-Path $root 'P179-NATIVE-CALL.ps1')
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
  $capExit=Invoke-P180NativeWithLog -Executable $exe -Arguments $capArgs -LogPath (Join-Path $out 'ASIO-CAPABILITY-LOG.txt')
  if($capExit -ne 0 -or -not (Test-Path -LiteralPath $capsPath -PathType Leaf)){
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
  $diagnosticPath=Join-Path $out 'ASIO-CALLBACK-DIAGNOSTICS.json'
  $timingTracePath=Join-Path $out 'ASIO-CALLBACK-TIMING-TRACE.json'
  $env:AWE32_ROM_PATH=$rom
  $env:AWE32_SF2_PATH=$sf2
  $args=@('--physical-asio-probe','--plugin',$dll,'--driver-name',$selected.Name,
    '--driver-clsid',$selected.CLSID,'--rate',([string]$rate),'--frames',([string]$frames),
    '--callbacks','1000','--nonce',$nonce,'--out',$asioPath,
    '--midi-note','48','--midi-out',$midiPath,
    '--diagnostic-out',$diagnosticPath,
    '--timing-trace-out',$timingTracePath)
  $nativeExit=Invoke-P180NativeWithLog -Executable $exe -Arguments $args -LogPath (Join-Path $out 'NATIVE-HOST-LOG.txt')
  # A diagnostic report NEVER establishes hardware PASS.
  if(Test-Path -LiteralPath $diagnosticPath -PathType Leaf){
    $diag=Get-Content -LiteralPath $diagnosticPath -Raw | ConvertFrom-Json
    if($diag.schema -cne '125a-asio-callback-diagnostic-v1' -or
       $diag.status -cne 'DIAGNOSTIC_ONLY_NOT_HARDWARE_PASS' -or
       $diag.nonce -cne $nonce -or
       $diag.asio_driver_name -cne $selected.Name -or
       $diag.asio_driver_clsid -ine $selected.CLSID -or
       $diag.executor_sha256 -cne $executorHash -or
       $diag.product_sha256 -cne $moduleHash -or
       [int]$diag.sample_rate -ne $rate -or
       [int]$diag.buffer_frames -ne $frames -or
       [int]$diag.requested_callbacks -ne 1000 -or
       -not [bool]$diag.observed_after_actual_driver_stop -or
       [bool]$diag.physical_asio_verified -or
       [bool]$diag.commercial_daw_verified -or
       [bool]$diag.release_approved){
      throw 'Die ASIO-Diagnose ist ungueltig oder gehoert zu einem anderen Testlauf.'
    }
    $report.diagnostics_verified=$true
    $report.diagnostics_file='ASIO-CALLBACK-DIAGNOSTICS.json'
    $report.asio_callback_counts=@{
      total=[int64]$diag.asio_callbacks
      successful=[int64]$diag.successful_process_callbacks
      failed=[int64]$diag.failed_process_callbacks
      deadline_misses=[int64]$diag.deadline_misses_total
      callback_spacing_violations=[int64]$diag.callback_spacing_violations
      callback_execution_over_budget=[int64]$diag.callback_execution_over_budget
      xruns=[int64]$diag.hardware_asio_overload_or_resync_messages
      rate_changes=[int64]$diag.sample_rate_change_notifications
      midi_on=[int64]$diag.note_on_events
      midi_off=[int64]$diag.note_off_events
      pcm_nonzero_samples=[int64]$diag.nonzero_pcm_samples
    }
    $report.asio_cause_counts=@{
      midi_event_failures=[int64]$diag.midi_event_failures
      vst_process_errors=[int64]$diag.vst_process_returned_error
      nonfinite_pcm=[int64]$diag.nonfinite_vst_pcm_samples
      missing_asio_buffers=[int64]$diag.missing_asio_output_buffers
      asio_converter_errors=[int64]$diag.asio_sample_write_failures
      callback_exceptions=[int64]$diag.caught_callback_exceptions
    }
  }
  # Time windows, exact nonce+driver+hash checked independently from P102.
  if(Test-Path -LiteralPath $timingTracePath -PathType Leaf){
    $trace=Get-Content -LiteralPath $timingTracePath -Raw | ConvertFrom-Json
    if($trace.schema -cne '125a-real-asio-callback-window-trace-v1' -or
       $trace.status -cne 'DIAGNOSTIC_ONLY_NOT_HARDWARE_PASS' -or
       $trace.nonce -cne $nonce -or
       $trace.asio_driver_name -cne $selected.Name -or
       $trace.asio_driver_clsid -ine $selected.CLSID -or
       $trace.product_sha256 -cne $moduleHash -or
       $trace.executor_sha256 -cne $executorHash -or
       [int]$trace.sample_rate -ne $rate -or
       [int]$trace.buffer_frames -ne $frames -or
       [int]$trace.requested_callbacks -ne 1000 -or
       [int]$trace.actual_callbacks -lt 1000 -or
       [int]$trace.recorded_callbacks -ne [int]$trace.actual_callbacks -or
       [int]$trace.unrecorded_callback_slots -ne 0 -or
       [int]$trace.trace_overflow_callbacks -ne 0 -or
       -not [bool]$trace.trace_complete -or
       [long]$trace.qpc_frequency_hz -le 0 -or
       -not [bool]$trace.captured_after_asio_driver_stop -or
       [bool]$trace.physical_asio_verified -or
       [bool]$trace.commercial_daw_verified -or
       [bool]$trace.release_approved){
      throw 'P181 Zeitspur hat falsche Sitzung, Identitaet oder unvollstaendige Daten.'
    }
    if(-not $report.diagnostics_verified){
      throw 'P181 Zeitspur kann ohne unabhaengig verifizierte P102-Diagnose nicht gelten.'
    }
    $events=@($trace.events)
    if([int]$trace.callback_start_spacing_violations -ne [int]$diag.callback_spacing_violations -or
       [int]$trace.actual_callbacks -ne [int]$diag.asio_callbacks -or
       [int]$trace.selected_window_callbacks -ne $events.Count){
      throw 'P181 Zeitspur und realer P102 ASIO-Zaehler widersprechen sich.'
    }
    $outOfOrder=$false
    $previous=-1
    $gapsInWindows=0
    foreach($sample in $events){
      $ci=[int]$sample.callback_index_zero_based
      if($ci -le $previous -or $ci -ge [int]$trace.actual_callbacks -or
         [long]$sample.qpc_end_ticks -lt [long]$sample.qpc_start_ticks){$outOfOrder=$true}
      $previous=$ci
      if([bool]$sample.gap_violation){
        $gapsInWindows++
        if([double]$sample.previous_start_to_start_us -le (2000000.0*$frames/$rate)){
          throw 'P181 aufgezeichnete Timingverletzung hat keinen validen Startabstand.'
        }
      }
    }
    if($outOfOrder -or $gapsInWindows -ne [int]$trace.callback_start_spacing_violations){
      throw 'P181 QPC Zeitfenster enthalten doppelte oder fehlende Callback-Indizes.'
    }
    $report.timing_trace_verified=$true
    $report.timing_trace_file='ASIO-CALLBACK-TIMING-TRACE.json'
    $report.timing_trace_gaps=[int]$trace.callback_start_spacing_violations
    $report.timing_trace_window_samples=$events.Count
    $report.timing_trace_events=@($events | ForEach-Object {
      [PSCustomObject]@{
        callback_index_zero_based=[int]$_.callback_index_zero_based
        driver_buffer_index=[int]$_.driver_buffer_index
        thread_id=[int64]$_.thread_id
        relative_start_us=[double]$_.relative_start_us
        previous_start_to_start_us=[double]$_.previous_start_to_start_us
        previous_callback_duration_us=[double]$_.previous_callback_duration_us
        this_callback_duration_us=[double]$_.this_callback_duration_us
        gap_violation=[bool]$_.gap_violation
        process_success=[bool]$_.process_success
        driver_overload_or_resync_messages=[int]$_.driver_overload_or_resync_messages
        sample_rate_change_messages=[int]$_.sample_rate_change_messages
        midi_note_on_count_after=[int]$_.midi_note_on_count_after
        midi_note_off_count_after=[int]$_.midi_note_off_count_after
      }
    })
  }
  if(-not $report.timing_trace_verified -and $nativeExit -eq 0){
    throw 'P181 Echtzeit-Zeitspur fehlt trotz erfolgreichem ASIO-Native-Host.'
  }
  if($nativeExit -ne 0){
    throw ('Echter ASIO-Test NO-GO (Exitcode '+$nativeExit+'). Siehe ASIO-CALLBACK-DIAGNOSTICS.json und NATIVE-HOST-LOG.txt')
  }
  if(-not $report.diagnostics_verified){throw 'Echte ASIO-Hardwarediagnose fehlt trotz erfolgreichem Prozess.'}
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
