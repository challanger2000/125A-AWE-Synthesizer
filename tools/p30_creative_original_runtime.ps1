# P30: Original Creative DEMO.EXE on an emulated AWE32 (no audio fidelity claim).
$ErrorActionPreference = "Stop"
$root = Join-Path (Get-Location).Path "p30-run"
$guest = Join-Path $root "guest"
$work = Join-Path $root "output"
New-Item -ItemType Directory -Force $guest,$work | Out-Null

function Download([string]$url,[string]$target) {
    Invoke-WebRequest -Uri $url -OutFile $target -MaximumRedirection 10
    if ((Get-Item $target).Length -eq 0) { throw "Empty download $target" }
}
function CheckBlob([string]$file,[string]$hash) {
    $current=(& git hash-object -- $file).Trim()
    if ($current -ne $hash) {throw "Creative original object digest mismatch $file"}
}

# Copyrighted Creative inputs are pulled into an ephemeral runner, NOT committed.
$source="https://raw.githubusercontent.com/qb40/sound-blaster-awe32/master/DOS/DEMO"
Download "$source/DEMO.EXE" (Join-Path $guest "DEMO.EXE")
Download "$source/SYNTHGM.SF2" (Join-Path $guest "SYNTHGM.SF2")
CheckBlob (Join-Path $guest "DEMO.EXE") "e10b8705c6a46444a998c4f6aa74a1cda2081506"
CheckBlob (Join-Path $guest "SYNTHGM.SF2") "205a540e5545945b58ab136ef5423327e2066d2c"

$version="2026.10.01"
$zip=Join-Path $root "dosbox-x.zip"
Download "https://github.com/joncampbell123/dosbox-x/releases/download/dosbox-x-v$version/dosbox-x-mingw64-$version-portable.zip" $zip
$hash=(Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant()
if ($hash -ne "def2d84d4415fc26c77252839b4dafb6b476e3a4204b896292e6b05505ca8c59") {
    throw "DOSBox-X release hash mismatch: $hash"
}
Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $root "dosbox") -Force
$binary=Get-ChildItem (Join-Path $root "dosbox") -Filter dosbox-x.exe -File -Recurse |
    Sort-Object FullName | Select-Object -First 1 -ExpandProperty FullName
if (-not $binary) {throw "Cannot find DOSBox-X executable"}

# Synthetic zero ROM: usable ONLY to explore the Creative CPU driver handshake.
$rom=Join-Path $guest "awe32-dummy.raw"
[IO.File]::WriteAllBytes($rom,[byte[]]::new(1048576))
$results=@()
foreach($kind in @("awe32","sb16")){
    $cfg=Join-Path $work "$kind.conf"
    $romUnix=$rom.Replace("\","/")
    $guestUnix=$guest.Replace("\","/")
    $config=@"
[sdl]
fullscreen=false
output=surface
[dos]
xms=true
ems=true
[dosbox]
machine=svga_s3
memsize=32
[sblaster]
sbtype=$kind
sbbase=220
irq=7
dma=1
hdma=5
rompath=$romUnix
memsize=8192
[midi]
mpu401=intelligent
mpubase=330
[autoexec]
mount c "$guestUnix"
c:
set BLASTER=A220 I7 D1 H5 P330 T6 E620
DEMO.EXE /SF2:SYNTHGM.SF2
"@
    Set-Content -Path $cfg -Value $config -Encoding Ascii
    $stdout=Join-Path $work "$kind-stdout.txt"
    $stderr=Join-Path $work "$kind-stderr.txt"
    Write-Host "Original Creative binary + emulated $kind, 28s safety limit"
    $args=@("-conf",('"' + $cfg + '"'),"-fastlaunch","-time-limit","20","-log-con")
    $proc=Start-Process -FilePath $binary -ArgumentList $args -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WorkingDirectory $work
    if (-not $proc.WaitForExit(28000)) {
        try {$proc.Kill()} catch {}
    }
    $combined=""
    foreach($path in @($stdout,$stderr)){
        if (Test-Path $path) { $combined += [IO.File]::ReadAllText($path) + [Environment]::NewLine }
    }
    foreach($file in (Get-ChildItem $work -File -Filter "*log*")){
        if ($file.Length -lt 500000) { $combined += [IO.File]::ReadAllText($file.FullName) + [Environment]::NewLine }
    }
    $status=if ($combined -match "AWE32 not detected") {"NOT_DETECTED"}
            elseif ($combined -match "AWE32 initialization failed") {"INIT_FAILED"}
            elseif ($combined -match "MPU401 initialization failed") {"MPU_FAILED"}
            elseif ($combined -match "Press <Esc> to stop") {"GUEST_LOOP_ENTERED"}
            else {"NO_VERIFIABLE_DOS_CONSOLE_OUTPUT"}
    $results+= [PSCustomObject]@{
        device=$kind
        status=$status
        creative_original_hash_ok=$true
        fake_ROM=$true
        user_SF2_tested=$false
        original_SF2LIB_linked=$null
        realtime_VST3_changed=$false
        output_tail=$combined.Substring([Math]::Max(0,$combined.Length-2600))
    }
}
$results | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $work "P30-result.json")
$results | Format-Table -AutoSize
Write-Host "Original CPU-side Creative DOS experiment complete; 1:1 chip sound NOT assessed."
