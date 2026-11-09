#requires -Version 5.1
# P188 privilege-aware launcher. Independent ETW-only preflight before one ASIO run.
[CmdletBinding()]param([switch]$CheckOnly,[switch]$Cancel,[switch]$PreflightOnly,[switch]$Elevated)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot;$out=$null;$report=$null
function Save-P188 {
  if ($null -ne $out -and $null -ne $report) {
    $report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $out 'P188-PREFLIGHT.json') -Encoding UTF8
  }
}
try {
  if (-not [Environment]::Is64BitProcess) { throw 'WINDOWS_X64_REQUIRED' }
  $manifest=Get-Content -LiteralPath (Join-Path $root 'P185-PACKAGE.json') -Raw | ConvertFrom-Json
  if ($manifest.schema -cne '125a-p185-package-v1' -or $manifest.testlab_source -cnotmatch '^[0-9a-f]{40}$') { throw 'PACKAGE_MANIFEST_INVALID' }
  foreach ($entry in $manifest.files.PSObject.Properties) {
    if ($entry.Name -match '(^[\\/]|\.\.|:)' -or $entry.Value -cnotmatch '^[0-9a-f]{64}$') { throw 'PACKAGE_ENTRY_INVALID' }
    $path=Join-Path $root $entry.Name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.Value) {
      throw 'PACKAGE_HASH_MISMATCH'
    }
  }
  foreach ($required in @('125A_Test_Lab_ETW.exe','P185-RUN.ps1','P185-DIAGNOSTICS.ps1','P188-PREFLIGHT.ps1','P188-ETW-ASIO.bat')) {
    if (-not $manifest.files.PSObject.Properties[$required]) { throw 'PACKAGE_ENTRY_MISSING' }
  }
  if ($CheckOnly) {
    Write-Host 'P188 Paketintegritaet: PASS. Kein Audio, keine ETW-Aufzeichnung, keine UAC-Abfrage.'
    exit 0
  }
  if ($Cancel) { Write-Host 'P188 abgebrochen: kein Test gestartet.';exit 2 }
  $principal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
  $admin=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $admin) {
    if ($Elevated) { throw 'ELEVATED_TOKEN_NOT_OBTAINED' }
    Write-Host 'P188: Kernel-ETW braucht einen erhoehten Administrator-Prozess. Windows fragt per UAC.'
    $arg='-NoLogo -NoProfile -ExecutionPolicy Bypass -File "'+$PSCommandPath+'" -Elevated'
    if ($PreflightOnly) { $arg+=' -PreflightOnly' }
    try {
      $proc=Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $arg -Verb RunAs -PassThru -Wait -ErrorAction Stop
      exit [int]$proc.ExitCode
    } catch {
      Write-Host 'P188: UAC verweigert oder keine erhoehten Administratorrechte vorhanden; kein ASIO-Test gestartet.'
      exit 5
    }
  }
  $out=Join-Path $root ('P188-PREFLIGHT-'+[Guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Path $out | Out-Null
  $report=[ordered]@{
    schema='125a-p188-etw-privilege-v1';status='INCONCLUSIVE';code='ETW_PREFLIGHT_NOT_RUN';
    administrator_token=$true;etw_only=$true;physical_asio='NOT_RUN';awe_realtime='NOT_RUN';
    cause='INCONCLUSIVE';release_approved=$false;full_audit=$false;
    testlab_source=$manifest.testlab_source;etw_tool_sha256=$manifest.files.'125A_Test_Lab_ETW.exe'
  }
  $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
  try {$bytes=New-Object byte[] 24;$rng.GetBytes($bytes)} finally {$rng.Dispose()}
  $nonce=([BitConverter]::ToString($bytes)).Replace('-','').ToLowerInvariant()
  $dir=Join-Path $out 'RAW-LOCAL-ONLY'
  $etw=Join-Path $root '125A_Test_Lab_ETW.exe'
  Write-Host 'P188: Administrator-Token bestaetigt; teste ETW zuerst OHNE Audiointerface und ohne ASIO.'
  $old=$ErrorActionPreference;$nativeExit=-1
  try {
    $ErrorActionPreference='Continue'
    & $etw --selftest $dir $nonce 2>&1 | ForEach-Object { [string]$_ } | Tee-Object -FilePath (Join-Path $out 'preflight.log') | Out-Host
    $nativeExit=[int]$LASTEXITCODE
  } finally { $ErrorActionPreference=$old }
  $report.native_exit=$nativeExit
  if (-not (Test-Path -LiteralPath (Join-Path $dir 'capture.json') -PathType Leaf)) {
    $report.code='ETW_PREFLIGHT_CAPTURE_MISSING';Save-P188
    Write-Host ('P188: ETW konnte keine Diagnose erzeugen. Kein ASIO-Test. Ergebnis: '+(Join-Path $out 'P188-PREFLIGHT.json'))
    exit 3
  }
  $c=Get-Content -LiteralPath (Join-Path $dir 'capture.json') -Raw | ConvertFrom-Json
  $report.etw=[ordered]@{
    kernel_start=[long]$c.kernel.start;user_start=[long]$c.user.start;
    kernel_stop=[long]$c.kernel.stop;user_stop=[long]$c.user.stop;
    marker_enable=[long]$c.marker_enable;events=[long]$c.events;
    cswitches=[long]$c.cswitches;decode_errors=[long]$c.decode_errors;
    child_pid=[long]$c.child_pid;child_exit=[long]$c.child_exit;
    kernel_open=[long]$c.kernel.open;user_open=[long]$c.user.open;
    kernel_process=[long]$c.kernel.process;user_process=[long]$c.user.process;
    kernel_events_lost=[long]$c.kernel.events_lost;user_events_lost=[long]$c.user.events_lost;
    kernel_buffers_lost=[long]$c.kernel.buffers_lost;user_buffers_lost=[long]$c.user.buffers_lost
  }
  if ($c.kernel.start -eq 5 -or $c.user.start -eq 5) {
    $report.code='ETW_ACCESS_DENIED_DESPITE_ELEVATION'
  } elseif ($c.kernel.start -ne 0 -or $c.user.start -ne 0 -or $c.marker_enable -ne 0) {
    $report.code='ETW_SESSION_START_FAILED'
  } elseif ($nativeExit -ne 0 -or $c.kernel.stop -ne 0 -or $c.user.stop -ne 0 -or
       $c.kernel.open -ne 0 -or $c.user.open -ne 0 -or $c.kernel.process -ne 0 -or $c.user.process -ne 0) {
    $report.code='ETW_PREFLIGHT_NATIVE_FAILED'
  } elseif ($c.decode_errors -ne 0 -or $c.cswitches -le 0) {
    $report.code='ETW_PREFLIGHT_DECODER_OR_CSWITCH_FAILED'
  } elseif ($c.kernel.events_lost -ne 0 -or $c.user.events_lost -ne 0 -or
       $c.kernel.buffers_lost -ne 0 -or $c.user.buffers_lost -ne 0) {
    $report.code='ETW_PREFLIGHT_LOSS'
  } else {
    $report.code='ETW_PREFLIGHT_PASS';$report.status='PREFLIGHT_ONLY_PASS'
  }
  Save-P188
  if ($report.code -cne 'ETW_PREFLIGHT_PASS') {
    Write-Host ('P188: '+$report.code+'. ASIO NICHT gestartet. Nur diese Datei hochladen: '+(Join-Path $out 'P188-PREFLIGHT.json'))
    exit 3
  }
  Write-Host ('P188: Kernel-/User-ETW und Decoder-Vorprobe bestanden: '+(Join-Path $out 'P188-PREFLIGHT.json'))
  if ($PreflightOnly) { Write-Host 'P188: Preflight-only. Kein Audio, kein ASIO-Test.';exit 0 }
  Write-Host 'P188: Jetzt folgt EIN P185-Referenz-ASIO-Test nach expliziter START-Bestaetigung.'
  & (Join-Path $root 'P185-RUN.ps1')
  exit [int]$LASTEXITCODE
} catch {
  $code=[string]$_.Exception.Message
  if ($code -cnotmatch '^[A-Z0-9_]+$') { $code='P188_LOCAL_TOOL_ERROR' }
  if ($null -ne $report) { $report.code=$code;Save-P188 }
  Write-Host ('P188: '+$code+'. Keine Mess-/Releasefreigabe.')
  exit 3
}
