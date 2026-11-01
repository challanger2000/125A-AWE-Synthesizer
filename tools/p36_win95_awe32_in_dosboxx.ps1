$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP 'p36-win95'
$exeRoot = Join-Path $root 'dosbox'
$out = Join-Path (Get-Location).Path 'p36-output'
New-Item -ItemType Directory -Force $root,$exeRoot,$out | Out-Null

function Download($url,$dest) {
    & curl.exe --fail --location --retry 3 --connect-timeout 20 --max-time 240 --output $dest $url
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $dest)) { throw "Download failed: $url" }
}
try {
    $os = Join-Path $root 'win95.img.7z'
    Download 'https://www.rekoba.de/~cs/v86/win95/Windows95b_p9x-0.9.91_512MB.img.7z' $os
    $seven = 'C:\Program Files\7-Zip\7z.exe'
    if (-not (Test-Path $seven)) {
       $cmd=Get-Command 7z -ErrorAction SilentlyContinue
       if (-not $cmd) { throw '7-Zip absent' }
       $seven=$cmd.Source
    }
    & $seven x -y "-o$root" $os | Select-Object -Last 10
    if ($LASTEXITCODE -ne 0) { throw 'OSR2 disk extraction failed' }
    $disk = Get-ChildItem $root -Filter '*.img' -Recurse -File |
            Where-Object {$_.Length -eq 536870912} |
            Select-Object -First 1 -ExpandProperty FullName
    if (-not $disk) { throw 'Valid Windows OSR2 raw disk image absent' }
    $rom = Join-Path $root 'awe32-dummy.raw'
    [IO.File]::WriteAllBytes($rom,[byte[]]::new(1048576))
    $zip = Join-Path $root 'dosbox-x.zip'
    Download 'https://github.com/joncampbell123/dosbox-x/releases/download/dosbox-x-v2026.10.01/dosbox-x-mingw64-2026.10.01-portable.zip' $zip
    $actual=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne 'def2d84d4415fc26c77252839b4dafb6b476e3a4204b896292e6b05505ca8c59') {
        throw "DOSBox-X package integrity failure $actual"
    }
    Expand-Archive -LiteralPath $zip -DestinationPath $exeRoot -Force
    $binary=Get-ChildItem $exeRoot -Filter dosbox-x.exe -Recurse -File |
            Sort-Object FullName | Select-Object -First 1 -ExpandProperty FullName
    if (-not $binary) { throw 'DOSBox-X executable missing' }
    $osUnix=$disk.Replace('\','/')
    $romUnix=$rom.Replace('\','/')
    $cfg=Join-Path $root 'awe32-win95.conf'
    @"
[sdl]
fullscreen=false
output=surface
[dosbox]
title=125A P36 Win95 AWE32
machine=svga_s3
memsize=64
[dos]
ver=7.1
xms=true
ems=true
hard drive data rate limit=0
[video]
vmemsize=8
[cpu]
cputype=pentium_mmx
core=normal
[sblaster]
sbtype=awe32
sbbase=220
irq=7
dma=1
hdma=5
[emu8k]
rompath=$romUnix
memsize=8192
[fdc, primary]
int13fakev86io=true
[ide, primary]
int13fakeio=true
int13fakev86io=true
[ide, secondary]
int13fakeio=true
int13fakev86io=true
[autoexec]
imgmount C "$osUnix" -ide 1m
boot C:
"@ | Set-Content -Path $cfg -Encoding Ascii
    $stdout=Join-Path $out 'dosboxx.stdout.txt'
    $stderr=Join-Path $out 'dosboxx.stderr.txt'
    $arguments=@('-conf',('"' + $cfg + '"'),'-fastlaunch','-time-limit','52','-log-con')
    $proc=Start-Process -FilePath $binary -WorkingDirectory (Split-Path $binary) -ArgumentList $arguments -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    function Capture($label) {
        try {
            Add-Type -AssemblyName System.Drawing
            Add-Type -AssemblyName System.Windows.Forms
            $bounds=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            if ($bounds.Width -lt 200 -or $bounds.Height -lt 200) { throw 'No display available' }
            $bmp=New-Object Drawing.Bitmap($bounds.Width,$bounds.Height)
            $g=[Drawing.Graphics]::FromImage($bmp)
            $g.CopyFromScreen($bounds.Location,[Drawing.Point]::Empty,$bounds.Size)
            $file=Join-Path $out "display_$label.png"
            $bmp.Save($file,[Drawing.Imaging.ImageFormat]::Png)
            $g.Dispose()
            $bmp.Dispose()
            Write-Host "Saved host display $file"
        } catch { Write-Warning "No interactive-screen capture: $_" }
    }
    Start-Sleep -Seconds 22
    Capture '022s'
    Start-Sleep -Seconds 25
    Capture '047s'
    if (-not $proc.HasExited) { try { $proc.Kill();$proc.WaitForExit(5000)|Out-Null } catch {} }
    $report=[PSCustomObject]@{
       image_format='Windows 95 OSR2 raw 512MB'; emulation='DOSBox-X 2026.10.01'
       emulated_sound_card='awe32'; emu8000_RAM_kb=8192
       synthetic_ROM=$true; real_wave_ROM_used=$false
       user_SF2_tested=$false; creative_VXD_installed=$false
       original_driver_trace_captured=$false
       exit_code=$proc.ExitCode
       screenshots=@(Get-ChildItem $out -Filter 'display_*.png' | Select-Object -ExpandProperty Name)
    }
    $report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $out 'P36-result.json')
    Get-Content $stdout -Tail 25 -ErrorAction SilentlyContinue
    Get-Content $stderr -Tail 25 -ErrorAction SilentlyContinue
    $report | Format-List
}
finally {
    Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host 'Deleted ephemeral Windows95 image, DOSBox-X and dummy ROM'
}
