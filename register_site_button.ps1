$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot 'RUN_REFRESH.bat'
if (-not (Test-Path -LiteralPath $launcher)) {
    throw 'RUN_REFRESH.bat is missing. Extract every file from the ZIP first.'
}
$base = 'HKCU:\Software\Classes\phjunivrates'
$commandKey = Join-Path $base 'shell\open\command'
New-Item -Path $commandKey -Force | Out-Null
Set-Item -Path $base -Value 'URL:University Competition Rate Refresh'
New-ItemProperty -Path $base -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null
$command = '"' + $env:ComSpec + '" /d /c ""' + $launcher + '" "%1""'
Set-Item -Path $commandKey -Value $command
Write-Output ('Registered: phjunivrates://refresh -> ' + $launcher)
