#requires -Version 5.1
# P180: Windows PowerShell native-process wrapper; exit codes never suppressed.
function Invoke-P180NativeWithLog {
  [CmdletBinding()]
  param([Parameter(Mandatory=$true)][string]$Executable,
        [string[]]$Arguments=@(),
        [Parameter(Mandatory=$true)][string]$LogPath)
  $previousPreference=$ErrorActionPreference
  try {
    # Windows PowerShell 5.1 may raise NativeCommandError when native stderr
    # is merged into the success stream under ErrorActionPreference=Stop.
    # The scoped preference prevents a false failure in the diagnostic
    # launcher; the actual native exit code remains the approval gate.
    $ErrorActionPreference='Continue'
    & $Executable @Arguments 2>&1 | ForEach-Object {
      if($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() }
      else { [string]$_ }
    } | Tee-Object -FilePath $LogPath | Out-Host
    return [int]$LASTEXITCODE
  } finally {
    $ErrorActionPreference=$previousPreference
  }
}
