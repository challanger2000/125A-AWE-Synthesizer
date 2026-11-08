#requires -Version 5.1
# P182: physical ASIO comparison REFERENCE-A / AWE / REFERENCE-B.
# Results are diagnostic only: never a release or hardware-output certification.
[CmdletBinding()]param([switch]$OfflineSelfTest)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Classify-P182([int]$a,[int]$s,[int]$b) {
  if($a -lt 0 -or $s -lt 0 -or $b -lt 0){return 'INCOMPLETE'}
  if($a -gt 0 -or $b -gt 0) {
    if($s -gt 0){return 'REFERENCE_AND_AWE_GAPS_NON_EXCLUSIVE'}
    return 'REFERENCE_GAP_NO_AWE_GAP_IN_THIS_SET'
  }
  if($s -gt 0){return 'AWE_ONLY_GAP_IN_THIS_SET_NO_CAUSAL_PROOF'}
  return 'NO_GAP_IN_THREE_RUNS_NOT_UNIVERSAL'
}
if($OfflineSelfTest) {
  $cases=@(
    @(@(1,1,1),'REFERENCE_AND_AWE_GAPS_NON_EXCLUSIVE'),
    @(@(1,0,0),'REFERENCE_GAP_NO_AWE_GAP_IN_THIS_SET'),
    @(@(0,1,0),'AWE_ONLY_GAP_IN_THIS_SET_NO_CAUSAL_PROOF'),
    @(@(0,0,0),'NO_GAP_IN_THREE_RUNS_NOT_UNIVERSAL'),
    @(@(-1,1,1),'INCOMPLETE')
  )
  foreach($case in $cases) {
    if((Classify-P182 $case[0][0] $case[0][1] $case[0][2]) -cne $case[1]) {
      throw 'P182 artificial category test failed'
    }
  }
  Write-Host '[PASS] P182 classification unit tests; physical ASIO NOT RUN'
  exit 0
}
function New-P182Nonce {
  $bytes=New-Object byte[] 24
  $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
  try{$rng.GetBytes($bytes)}finally{$rng.Dispose()}
  return ([BitConverter]::ToString($bytes)).Replace('-','').ToLowerInvariant()
}
function Read-P182Path([string]$name) {
  return (Read-Host $name).Trim().Trim([char]34)
}
$root=$PSScriptRoot
$exe=Join-Path $root '125A-Test-Lab-ASIO-MIDI.exe'
$awe=Join-Path $root '125A_AWE_Synthesizer.vst3\Contents\x86_64-win\125A_AWE_Synthesizer.vst3'
$reference=Join-Path $root '125A_QA_ASIO_Reference_MIDI.vst3\Contents\x86_64-win\125A_QA_ASIO_Reference_MIDI.vst3'
$out=Join-Path $root ('P182-LOCAL-RESULT-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Force $out | Out-Null
$reportFile=Join-Path $out 'P182-COMPARISON.json'
$report=@{
  schema='125a-p182-physical-reference-awe-reference-comparison-v1'
  status='NOT_RUN_OR_FAIL'
  classification='INCOMPLETE'
  diagnostics_only=$true
  physical_asio_verified=$false
  daw_session_verified=$false
  analog_hardware_output_verified=$false
  release_approved=$false
  original_rom_sf2='LOCAL_NOT_UPLOADED'
  trials=@()
  errors=@()
}
function Publish-P182 {
  $report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $reportFile -Encoding UTF8
}
$oldRom=$env:AWE32_ROM_PATH
$oldSf2=$env:AWE32_SF2_PATH
try {
  if(-not [Environment]::Is64BitProcess){throw 'P182 requires 64-bit Windows PowerShell'}
  . (Join-Path $root 'P179-NATIVE-CALL.ps1')
  foreach($file in @($exe,$awe,$reference)){
    if(-not (Test-Path -LiteralPath $file -PathType Leaf)){
      throw ('Required P182 binary missing: '+[IO.Path]::GetFileName($file))}
  }
  $hostHash=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
  $aweHash=(Get-FileHash -LiteralPath $awe -Algorithm SHA256).Hash.ToLowerInvariant()
  $refHash=(Get-FileHash -LiteralPath $reference -Algorithm SHA256).Hash.ToLowerInvariant()
  $originalManifest=Get-Content -LiteralPath (Join-Path $root 'P179-SHA256SUMS.txt')
  $refManifest=Get-Content -LiteralPath (Join-Path $root 'P182-REFERENCE-SHA256.txt')
  if(-not ($originalManifest -contains ($hostHash+'  125A-Test-Lab-ASIO-MIDI.exe')) -or
     -not ($originalManifest -contains ($aweHash+'  125A_AWE_Synthesizer.vst3')) -or
     -not ($refManifest -contains ($refHash+'  125A_QA_ASIO_Reference_MIDI.vst3'))){
    throw 'P182 binaries do not match pinned Windows CI SHA256 manifest'
  }
  $rom=Read-P182Path 'Original AWE32-ROM (*.raw), voller Pfad'
  $sf2=Read-P182Path 'Original SoundFont (*.sf2), voller Pfad'
  if(-not (Test-Path -LiteralPath $rom -PathType Leaf) -or
     (Get-Item -LiteralPath $rom).Length -ne 1048576){
    throw 'Original-ROM fehlt oder nicht exakt 1.048.576 Bytes'}
  if(-not (Test-Path -LiteralPath $sf2 -PathType Leaf) -or
     [IO.Path]::GetExtension($sf2).ToLowerInvariant() -ne '.sf2'){
    throw 'Original-SF2 Datei fehlt'}
  $driversRoot='Registry::HKEY_LOCAL_MACHINE\SOFTWARE\ASIO'
  if(-not (Test-Path -LiteralPath $driversRoot)){throw 'Kein physischer ASIO-Treiber registriert'}
  $drivers=@(Get-ChildItem -LiteralPath $driversRoot | ForEach-Object {
    $entry=Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue
    $id=if($entry -and $entry.PSObject.Properties['CLSID']){[string]$entry.CLSID}else{''}
    if($id -match '^\{[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\}$'){
      [PSCustomObject]@{Name=$_.PSChildName;CLSID=$id}
    }
  })
  if($drivers.Count -eq 0){throw 'Kein gueltiger ASIO-Treiber'}
  if($drivers.Count -eq 1){$selected=$drivers[0]}
  else {
    Write-Host 'ASIO-Treiber zur Auswahl:'
    for($i=0;$i -lt $drivers.Count;$i++){Write-Host ('  '+($i+1)+': '+$drivers[$i].Name)}
    $choice=Read-Host 'Nummer des tatsaechlichen USB-Audiointerface-Treibers'
    $number=0
    if(-not [int]::TryParse($choice,[ref]$number) -or
       $number -lt 1 -or $number -gt $drivers.Count){throw 'Ungueltige ASIO-Treiberwahl'}
    $selected=$drivers[$number-1]
  }
  Write-Host ('P182 ASIO-Treiber (alle drei Durchlaeufe): '+$selected.Name)
  Write-Host 'A/B/A: einfacher MIDI-Sinus -> echter AWE -> MIDI-Sinus.'
  Write-Host 'DAW schliessen und Kopfhoerer/Monitore leise stellen. ASIO-Ausgang -20 dBFS begrenzt.'
  $consent=Read-Host 'Mit Enter den physischen ASIO-Dreifachtest starten; N bricht ab'
  if($consent.Trim() -ne ''){throw 'P182 vom Benutzer abgebrochen'}
  $capNonce=New-P182Nonce
  $capPath=Join-Path $out 'ASIO-DRIVER-CAPABILITIES.json'
  $capArgs=@('--asio-buffer-capabilities','--driver-name',$selected.Name,
    '--driver-clsid',$selected.CLSID,'--nonce',$capNonce,'--out',$capPath)
  $capExit=Invoke-P180NativeWithLog -Executable $exe -Arguments $capArgs -LogPath (Join-Path $out 'ASIO-CAPABILITY-LOG.txt')
  if($capExit -ne 0 -or -not (Test-Path -LiteralPath $capPath -PathType Leaf)){
    throw 'P182 real ASIO capability probe did not succeed'}
  $caps=Get-Content -LiteralPath $capPath -Raw | ConvertFrom-Json
  if($caps.schema -cne '125a-asio-driver-capability-v1' -or
     $caps.nonce -cne $capNonce -or
     $caps.driver_name -cne $selected.Name -or
     $caps.driver_clsid -ine $selected.CLSID -or
     $caps.executor_sha256 -cne $hostHash -or
     [bool]$caps.physical_audio_callbacks -or [bool]$caps.release_approved){
    throw 'P182 independent driver capabilities have invalid provenance'}
  $rate=[int]$caps.selected_rate
  $frames=[int]$caps.selected_frames
  $low=[int]$caps.minimum_frames
  $high=[int]$caps.maximum_frames
  $preferred=[int]$caps.preferred_frames
  $step=[int]$caps.granularity
  if($frames -lt 64 -or $frames -gt 4096 -or $low -le 0 -or
     $frames -lt $low -or $frames -gt $high -or
     -not (($step -eq 0 -and $frames -eq $preferred) -or
           ($step -eq -1 -and ($frames -band ($frames-1)) -eq 0) -or
           ($step -gt 0 -and ($frames-$low)%$step -eq 0))){
    throw 'Physical ASIO reports invalid requested frame count'}
  if(-not (($rate -eq 44100 -and [bool]$caps.rate_44100) -or
           ($rate -eq 48000 -and [bool]$caps.rate_48000) -or
           ($rate -eq 96000 -and [bool]$caps.rate_96000))){
    throw 'Physical ASIO rejects requested rate'}
  $report.driver=$selected.Name
  $report.driver_clsid=$selected.CLSID
  $report.sample_rate=$rate
  $report.buffer_frames=$frames
  $report.buffer_period_ms=[Math]::Round(1000.0*$frames/$rate,5)
  $report.executor_sha256=$hostHash
  $report.awe_sha256=$aweHash
  $report.reference_sha256=$refHash
  $env:AWE32_ROM_PATH=$rom
  $env:AWE32_SF2_PATH=$sf2
  $plan=@(
    [PSCustomObject]@{name='REFERENCE-A';instrument='QA_MIDI_SINE';path=$reference;hash=$refHash},
    [PSCustomObject]@{name='AWE';instrument='REAL_AWE_VST3';path=$awe;hash=$aweHash},
    [PSCustomObject]@{name='REFERENCE-B';instrument='QA_MIDI_SINE';path=$reference;hash=$refHash}
  )
  foreach($run in $plan) {
    if($report.trials.Count -gt 0){Start-Sleep -Milliseconds 750}
    Write-Host ('Starte reale ASIO-Session: '+$run.name)
    $dir=Join-Path $out $run.name
    New-Item -ItemType Directory -Force $dir | Out-Null
    $nonce=New-P182Nonce
    $diagPath=Join-Path $dir 'ASIO-CALLBACK-DIAGNOSTICS.json'
    $tracePath=Join-Path $dir 'ASIO-CALLBACK-TIMING-TRACE.json'
    $passPath=Join-Path $dir 'ASIO-CALLBACKS.json'
    $midiPath=Join-Path $dir 'ASIO-MIDI-PCM.json'
    $args=@('--physical-asio-probe','--plugin',$run.path,
       '--driver-name',$selected.Name,'--driver-clsid',$selected.CLSID,
       '--rate',[string]$rate,'--frames',[string]$frames,'--callbacks','1000',
       '--nonce',$nonce,'--out',$passPath,'--midi-note','48','--midi-out',$midiPath,
       '--diagnostic-out',$diagPath,'--timing-trace-out',$tracePath)
    $exitCode=Invoke-P180NativeWithLog -Executable $exe -Arguments $args -LogPath (Join-Path $dir 'NATIVE-HOST-LOG.txt')
    if(-not (Test-Path -LiteralPath $diagPath -PathType Leaf) -or
       -not (Test-Path -LiteralPath $tracePath -PathType Leaf)){
      throw ($run.name+': genuine ASIO session has no complete diagnostic/trace; native exit='+$exitCode)
    }
    $d=Get-Content -LiteralPath $diagPath -Raw | ConvertFrom-Json
    $t=Get-Content -LiteralPath $tracePath -Raw | ConvertFrom-Json
    if($d.schema -cne '125a-asio-callback-diagnostic-v1' -or
       $t.schema -cne '125a-real-asio-callback-window-trace-v1' -or
       $d.status -cne 'DIAGNOSTIC_ONLY_NOT_HARDWARE_PASS' -or
       $t.status -cne 'DIAGNOSTIC_ONLY_NOT_HARDWARE_PASS' -or
       $d.nonce -cne $nonce -or $t.nonce -cne $nonce -or
       $d.asio_driver_name -cne $selected.Name -or $t.asio_driver_name -cne $selected.Name -or
       $d.asio_driver_clsid -ine $selected.CLSID -or $t.asio_driver_clsid -ine $selected.CLSID -or
       $d.product_sha256 -cne $run.hash -or $t.product_sha256 -cne $run.hash -or
       $d.executor_sha256 -cne $hostHash -or $t.executor_sha256 -cne $hostHash -or
       [int]$d.sample_rate -ne $rate -or [int]$t.sample_rate -ne $rate -or
       [int]$d.buffer_frames -ne $frames -or [int]$t.buffer_frames -ne $frames -or
       [int]$d.asio_callbacks -ne 1000 -or [int]$d.successful_process_callbacks -ne 1000 -or
       [int]$d.failed_process_callbacks -ne 0 -or
       [int]$t.actual_callbacks -ne 1000 -or [int]$t.recorded_callbacks -ne 1000 -or
       [int]$t.unrecorded_callback_slots -ne 0 -or [int]$t.trace_overflow_callbacks -ne 0 -or
       -not [bool]$t.trace_complete -or
       [int]$d.callback_spacing_violations -ne [int]$t.callback_start_spacing_violations -or
       -not [bool]$d.observed_after_actual_driver_stop -or
       -not [bool]$t.captured_after_asio_driver_stop -or
       [bool]$d.physical_asio_verified -or [bool]$t.physical_asio_verified -or
       [bool]$d.release_approved -or [bool]$t.release_approved){
      throw ($run.name+': ASIO trace identity or callback proof mismatch')
    }
    if([int]$d.note_on_events -lt 1 -or [int]$d.note_off_events -lt 1 -or
       [int]$d.nonzero_pcm_samples -lt 100 -or [double]$d.observed_peak_before_safety_limit -le 0.0001 -or
       [int]$d.vst_process_returned_error -ne 0 -or [int]$d.nonfinite_vst_pcm_samples -ne 0){
      throw ($run.name+': MIDI events or valid audio missing')
    }
    $events=@($t.events)
    $bad=@($events | Where-Object {[bool]$_.gap_violation})
    if($bad.Count -ne [int]$d.callback_spacing_violations -or
       $events.Count -ne [int]$t.selected_window_callbacks){
      throw ($run.name+': gap count or trace window mismatch')
    }
    $i=-1
    foreach($ev in $events){
      if([int]$ev.callback_index_zero_based -le $i -or
         [int]$ev.callback_index_zero_based -ge 1000){throw ($run.name+': invalid trace indexes')}
      $i=[int]$ev.callback_index_zero_based
      if([bool]$ev.gap_violation -and
         [double]$ev.previous_start_to_start_us -le 2000000.0*$frames/$rate){
        throw ($run.name+': reported gap does not breach strict timing threshold')}
    }
    $strictClean=([int]$d.deadline_misses_total -eq 0 -and
       [int]$d.hardware_asio_overload_or_resync_messages -eq 0 -and
       [int]$d.sample_rate_change_notifications -eq 0 -and
       [int]$d.failed_process_callbacks -eq 0)
    if(($exitCode -eq 0) -ne $strictClean){
      throw ($run.name+': actual native status contradicts ASIO timing evidence')}
    if($exitCode -eq 0){
      if(-not (Test-Path -LiteralPath $passPath -PathType Leaf) -or
         -not (Test-Path -LiteralPath $midiPath -PathType Leaf)){
        throw ($run.name+': native PASS without physical ASIO MIDI proof')}
      $pass=Get-Content -LiteralPath $passPath -Raw | ConvertFrom-Json
      $midi=Get-Content -LiteralPath $midiPath -Raw | ConvertFrom-Json
      if($pass.nonce -cne $nonce -or $midi.nonce -cne $nonce -or
         $pass.product_sha256 -cne $run.hash -or $midi.product_sha256 -cne $run.hash -or
         $pass.executor_sha256 -cne $hostHash -or $midi.executor_sha256 -cne $hostHash -or
         [int]$pass.asio_callbacks -ne 1000 -or [int]$pass.deadline_misses -ne 0 -or
         [int]$midi.midi_note -ne 48 -or [int]$midi.note_ons -lt 1 -or
         [int]$midi.note_offs -lt 1 -or [int]$midi.nonzero_pcm_samples -lt 100){
        throw ($run.name+': ASIO positive proof identity or PCM data invalid')
      }
    } else {
      if((Test-Path -LiteralPath $passPath) -or (Test-Path -LiteralPath $midiPath)){
        throw ($run.name+': false positive success files after ASIO FAIL')}
    }
    $gaps=@($bad | ForEach-Object {
      [PSCustomObject]@{
        callback_index_zero_based=[int]$_.callback_index_zero_based
        thread_id=[int64]$_.thread_id
        start_to_start_ms=[Math]::Round([double]$_.previous_start_to_start_us/1000.0,4)
        relative_start_ms=[Math]::Round([double]$_.relative_start_us/1000.0,4)
        previous_duration_ms=[Math]::Round([double]$_.previous_callback_duration_us/1000.0,4)
        current_duration_ms=[Math]::Round([double]$_.this_callback_duration_us/1000.0,4)
      }
    })
    $summary=[PSCustomObject]@{
      stage=$run.name
      instrument=$run.instrument
      product_sha256=$run.hash
      original_asio_gate=if($exitCode -eq 0){'PASS'}else{'NO_GO'}
      native_exit_code=$exitCode
      callbacks=[int]$d.asio_callbacks
      processed=[int]$d.successful_process_callbacks
      start_gap_count=[int]$d.callback_spacing_violations
      execution_overruns=[int]$d.callback_execution_over_budget
      asio_overload_resync=[int]$d.hardware_asio_overload_or_resync_messages
      maximum_spacing_ms=[Math]::Round([double]$d.maximum_callback_spacing_ns/1000000.0,4)
      maximum_execution_ms=[Math]::Round([double]$d.maximum_callback_duration_ns/1000000.0,4)
      note_on=[int]$d.note_on_events
      note_off=[int]$d.note_off_events
      nonzero_pcm_samples=[int64]$d.nonzero_pcm_samples
      gap_events=$gaps
      physical_asio_verified=$false
      release_approved=$false
    }
    $report.trials+=@($summary)
    Publish-P182
    Write-Host ('P182 '+$run.name+': '+$summary.original_asio_gate+', gaps='+$summary.start_gap_count)
  }
  if($report.trials.Count -ne 3){throw 'P182 missing one of three verified ASIO sessions'}
  $report.classification=Classify-P182 ([int]$report.trials[0].start_gap_count) ([int]$report.trials[1].start_gap_count) ([int]$report.trials[2].start_gap_count)
  $report.status='THREE_REAL_ASIO_SESSIONS_VERIFIED_DIAGNOSTIC_ONLY'
  $report.explanation='The three sequential physical ASIO stream starts are not proof of USB, Windows scheduling, AWE or DAW cause.'
  Write-Host ('P182 comparison result: '+$report.classification)
} catch {
  $report.status='NOT_RUN_OR_FAIL'
  $report.classification='INCOMPLETE'
  $report.errors=@($_.Exception.Message)
  Write-Host ('P182 NO-GO: '+$_.Exception.Message) -ForegroundColor Red
} finally {
  [Environment]::SetEnvironmentVariable('AWE32_ROM_PATH',$oldRom,'Process')
  [Environment]::SetEnvironmentVariable('AWE32_SF2_PATH',$oldSf2,'Process')
  Publish-P182
  Write-Host ('P182 final report: '+$reportFile)
}
if($report.status -ceq 'THREE_REAL_ASIO_SESSIONS_VERIFIED_DIAGNOSTIC_ONLY'){exit 0}
exit 1
