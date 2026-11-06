param([string]$Build='build-p132',[int]$Trial=1)
$ErrorActionPreference='Stop'
$paths=Get-Content "$Build/p132-paths-Release.txt"
$hostExe=$paths[0];$normal=$paths[1];$diag=$paths[2];$assets=$paths[3];$reader=$paths[4]
New-Item -ItemType Directory -Force qa | Out-Null
$cpuAvailable=$false;$heapEnabled=$false;$heapStarted=$false
$haveWpr=($null -ne (Get-Command wpr.exe -ErrorAction SilentlyContinue))
Get-ComputerInfo -Property OsName,OsVersion,WindowsVersion,CsProcessors,HyperVisorPresent | Format-List | Out-File qa/machine.txt
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | Format-List | Out-File qa/cpu.txt
@{cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed);os=[Environment]::OSVersion.VersionString;hostLogicalProcessors=[Environment]::ProcessorCount} | ConvertTo-Json -Depth 4 | Set-Content qa/machine.json
powercfg /getactivescheme | Out-File qa/power.txt
Get-Command wpr.exe,xperf.exe,wpaexporter.exe -ErrorAction SilentlyContinue | Select-Object Name,Source | Format-List | Out-File qa/profilers.txt
if($haveWpr){wpr -profiles 2>&1 | Out-File qa/wpr-profiles.txt}
$capabilities=@{cpuStart=$null;cpuStop=$null;heapConfig=$null;heapStart=$null;heapStop=$null;trial=$Trial}
try {
  # Opposite order in two independent Windows runner allocations.
  $order=if($Trial -eq 1){@('traced','untraced')}else{@('untraced','traced')}
  foreach($pass in $order){
    $output="qa/$pass";New-Item -ItemType Directory -Force $output | Out-Null
    if($pass -eq 'traced' -and $haveWpr){
      wpr -start CPU -filemode 2>&1 | Out-File qa/cpu-start.txt
      $capabilities.cpuStart=$LASTEXITCODE;$cpuAvailable=($LASTEXITCODE -eq 0)
    }
    & $hostExe $pass $normal $diag $assets $output 2>&1 | Tee-Object -FilePath "$output/host-log.txt"
    if($LASTEXITCODE -ne 0){throw "P132_INCOMPLETE host $pass exit=$LASTEXITCODE"}
    if($pass -eq 'traced' -and $cpuAvailable){
      wpr -stop qa/cpu.etl 2>&1 | Out-File qa/cpu-stop.txt
      $capabilities.cpuStop=$LASTEXITCODE;$cpuAvailable=$false
      if($LASTEXITCODE -eq 0){
        & $reader qa/cpu.etl "$output/callbacks.csv" "$output/modules.csv" "$output/etw" 2>&1 | Tee-Object -FilePath qa/cpu-decode.txt
        if($LASTEXITCODE -ne 0){throw 'ETW CPU decode failed'}
      }
    }
    python tests/p132/analyze.py $output 2>&1 | Tee-Object -FilePath "$output/analysis-log.txt"
    if($LASTEXITCODE -ne 0){throw 'Raw callback analysis failed'}
  }
  if($haveWpr){
    wpr -HeapTracingConfig awe32_p132_dll_host.exe enable 2>&1 | Out-File qa/heap-config.txt
    $capabilities.heapConfig=$LASTEXITCODE;$heapEnabled=($LASTEXITCODE -eq 0)
  }
  if($heapEnabled){
    wpr -start Heap -filemode 2>&1 | Out-File qa/heap-start.txt
    $capabilities.heapStart=$LASTEXITCODE;$heapStarted=($LASTEXITCODE -eq 0)
  }
  New-Item -ItemType Directory -Force qa/memory | Out-Null
  & $hostExe memory $normal $diag $assets qa/memory 2>&1 | Tee-Object -FilePath qa/memory/host-log.txt
  if($LASTEXITCODE -ne 0){throw 'Memory instrument workload incomplete'}
  if($heapStarted){
    wpr -stop qa/heap.etl 2>&1 | Out-File qa/heap-stop.txt
    $capabilities.heapStop=$LASTEXITCODE;$heapStarted=$false
    if($LASTEXITCODE -eq 0){
      & $reader qa/heap.etl qa/memory/callbacks.csv qa/memory/modules.csv qa/memory/etw 2>&1 | Tee-Object -FilePath qa/heap-decode.txt
      if($LASTEXITCODE -ne 0){throw 'ETW heap decode failed'}
    }
  }
  python tests/p132/analyze.py qa/memory 2>&1 | Tee-Object -FilePath qa/memory/analysis-log.txt
  if($LASTEXITCODE -ne 0){throw 'Heap evidence analysis failed'}
  if($heapEnabled){
    wpr -HeapTracingConfig awe32_p132_dll_host.exe disable 2>&1 | Out-File qa/heap-disable.txt
    $capabilities.heapDisable=$LASTEXITCODE;$heapEnabled=($LASTEXITCODE -ne 0)
    if($heapEnabled){throw 'Heap tracing configuration still active before crossover'}
  }
  if($env:P132_BASELINE_DIR){
    # ABBA/BAAB crossover: same runner, same executable, same workloads and
    # physically verified 30 voices. Only the loaded DLL differs.
    $env:P132_TARGET_ONLY='1'
    try {
      $pairOrder=if($Trial -eq 1){@('before-1','after-1','after-2','before-2')}else{@('after-1','before-1','before-2','after-2')}
      foreach($tag in $pairOrder){
        $dll=if($tag.StartsWith('before')){Join-Path $env:P132_BASELINE_DIR 'symbols/125A_P132_Diagnostic.vst3'}else{$diag}
        $output="qa/paired-$tag";New-Item -ItemType Directory -Force $output | Out-Null
        & $hostExe paired $normal $dll $assets $output 2>&1 | Tee-Object -FilePath "$output/host-log.txt"
        if($LASTEXITCODE -ne 0){throw "P132_INCOMPLETE paired $tag"}
        python tests/p132/analyze.py $output 2>&1 | Tee-Object -FilePath "$output/analysis-log.txt"
        if($LASTEXITCODE -ne 0){throw "Paired $tag analysis failed"}
      }
    } finally {Remove-Item Env:P132_TARGET_ONLY}
  }
} finally {
  # Stop only sessions successfully started by this workflow. Never cancel
  # an unrelated pre-existing WPR session.
  if($cpuAvailable){wpr -stop qa/cpu-incomplete.etl 2>&1 | Out-File qa/cpu-cleanup.txt}
  if($heapStarted){wpr -stop qa/heap-incomplete.etl 2>&1 | Out-File qa/heap-cleanup.txt}
  if($heapEnabled){wpr -HeapTracingConfig awe32_p132_dll_host.exe disable 2>&1 | Out-File qa/heap-disable.txt}
  $capabilities | ConvertTo-Json | Set-Content qa/capabilities.json
}
