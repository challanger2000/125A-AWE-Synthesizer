param([string]$ExistingDiskImage = '')
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
    if ($ExistingDiskImage) {
        if (-not (Test-Path $ExistingDiskImage)) { throw 'Existing guest image not found' }
        Write-Host "P38 pre-staged Win95 disk: $ExistingDiskImage"
    } else {
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
    }
    if ($ExistingDiskImage) { $disk = $ExistingDiskImage }
    if ((Get-Item $disk).Length -ne 536870912) { throw 'Invalid staged Win95 image size' }
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
[ne2000]
ne2000=true
nicbase=300
nicirq=3
backend=nothing
[serial]
serial2=disabled
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
    $arguments=@('-conf',('"' + $cfg + '"'),'-fastlaunch','-time-limit','88','-log-con')
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
    # P39: Never direct host-level Windows shortcuts to the runner.
    # Always validate foreground emulator PID before guest SendKeys.
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class P39Input {
    [StructLayout(LayoutKind.Sequential)]
    public struct Rect {public int Left,Top,Right,Bottom;}
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr w, out uint p);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr w, out Rect r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr w);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint d,uint e);
}
'@
    $wsh=New-Object -ComObject WScript.Shell
    function ForegroundGuest {
        $proc.Refresh()
        $wnd=$proc.MainWindowHandle
        if ($wnd -eq [IntPtr]::Zero) { throw 'DOSBox-X guest window unavailable' }
        [P39Input]::SetForegroundWindow($wnd)|Out-Null
        $wsh.AppActivate($proc.Id)|Out-Null
        Start-Sleep -Milliseconds 350
        [uint32]$actualPid=0
        [P39Input]::GetWindowThreadProcessId([P39Input]::GetForegroundWindow(),[ref]$actualPid)|Out-Null
        if ($actualPid -ne [uint32]$proc.Id) {
            throw "REFUSE HOST INPUT: guest PID $($proc.Id) != foreground PID $actualPid"
        }
        Write-Host "Verified guest emulator foreground PID $actualPid"
        return $wnd
    }
    function GuestKey([string]$keys) {
        $null=ForegroundGuest
        $wsh.SendKeys($keys)
        Start-Sleep -Milliseconds 250
    }
    function GuestClick([int]$relX,[int]$relY) {
        $wnd=ForegroundGuest
        $rect=New-Object P39Input+Rect
        [P39Input]::GetWindowRect($wnd,[ref]$rect)|Out-Null
        $px=$rect.Left+$relX
        $py=$rect.Top+$relY
        [P39Input]::SetCursorPos($px,$py)|Out-Null
        Start-Sleep -Milliseconds 200
        [P39Input]::mouse_event(2,0,0,0,0)
        Start-Sleep -Milliseconds 100
        [P39Input]::mouse_event(4,0,0,0,0)
        Write-Host "Clicked guest GUI offset ($relX,$relY) -> host ($px,$py)"
    }
    Start-Sleep -Seconds 24
    Capture '024s'
    # DHCP dialog in the actual 640x480 guest window sits at
    # host screenshot x~320..700 y~410..520; the NO button center
    # is window-relative x=377,y=341. SDL receives mouse events
    # even when legacy SendKeys bypass the emulated keyboard scanner.
    GuestClick 376 343
    Start-Sleep -Seconds 4
    Capture '028s_dhcp_dismiss'
    GuestClick 376 343
    Start-Sleep -Seconds 3
    Capture '031s_after_dialog'
    # At this point, if the OS desktop is interactive, click the
    # guest Start button and use its own Run menu.

    # DOSBox-X title/menu consumes 44 px above the 640x480 guest.
    $wnd=ForegroundGuest
    $rect=New-Object P39Input+Rect
    [P39Input]::GetWindowRect($wnd,[ref]$rect)|Out-Null
    $winWidth=$rect.Right-$rect.Left
    $winHeight=$rect.Bottom-$rect.Top
    Write-Host "DOSBox-X host window width $winWidth height $winHeight left $($rect.Left) top $($rect.Top)"
    GuestClick 28 ($winHeight-17)
    Start-Sleep -Seconds 1
    Capture '038_startmenu'
    GuestKey('r')
    Start-Sleep -Seconds 1
    Capture '040_run_dialog'
    $cmd='C:\WINDOWS\RUNDLL.EXE SETUPX.DLL,InstallHinfSection CTL0021_Device 132 C:\AWE32\SB16AWE.INF'
    GuestKey($cmd)
    Start-Sleep -Milliseconds 500
    Capture '042_command'
    GuestKey('{ENTER}')
    Start-Sleep -Seconds 12
    Capture '056_install'
    Start-Sleep -Seconds 14
    Capture '070_install'
    if (-not $proc.HasExited) {
        try { $proc.Kill();$proc.WaitForExit(5000)|Out-Null } catch {}
    }
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
