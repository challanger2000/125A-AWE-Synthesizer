param([string]$Build='build-p140',[string]$Baseline='evidence/p135-old-diagnostic')
$ErrorActionPreference='Stop'
$paths=Get-Content "$Build/p139-paths-Release.txt"
$hostExe=$paths[0];$normal=$paths[1];$diag=$paths[2];$assets=$paths[3]
$before=(Resolve-Path "$Baseline/symbols/125A_P135_Diagnostic.vst3").Path
if(-not (Test-Path $hostExe) -or -not (Test-Path $diag) -or -not (Test-Path $before)){
    throw "P140 missing full host/old-P134/new-P137 diagnostic binaries"
}
New-Item -ItemType Directory -Force qa/p140-paired | Out-Null
$env:P139_TARGET_ONLY='1'
try {
  $order=@('before-1','after-1','after-2','before-2')
  foreach($tag in $order){
    $dll=if($tag.StartsWith('before')){$before}else{$diag}
    $output="qa/p140-paired/$tag";New-Item -ItemType Directory -Force $output | Out-Null
    Write-Host "P140_PAIRS arm=$tag old=$before new=$diag"
    & $hostExe paired $normal $dll $assets $output 2>&1 | Tee-Object -FilePath "$output/host-log.txt"
    if($LASTEXITCODE -ne 0){throw "P140 incomplete actual audio workload $tag"}
    python tests/p139/analyze.py $output 2>&1 | Tee-Object -FilePath "$output/analysis-log.txt"
    if($LASTEXITCODE -ne 0){throw "P140 incomplete raw analysis $tag"}
  }
} finally {
  Remove-Item Env:P139_TARGET_ONLY -ErrorAction SilentlyContinue
}
python tests/p139/p140_pair_compare.py qa/p140-paired qa/p140-paired/p140-paired-128x30-v11.json 2>&1 | Tee-Object qa/p140-paired/P140-FINAL.txt
if($LASTEXITCODE -ne 0){throw "P140 paired P134 vs P137 test incomplete"}
