# Removes CzGram for the current Windows user and gives PrintScreen back to the Snipping Tool.
#
#   powershell -ExecutionPolicy Bypass -File packaging\windows\uninstall.ps1 [-Purge]
#
# -Purge also deletes your settings, API keys, token counts and the Czech OCR data.
# Python and Tesseract stay installed; remove them in Settings > Apps if you don't need them.
param([switch]$Purge)

$ErrorActionPreference = 'Continue'
$Dest = Join-Path $env:LOCALAPPDATA 'Programs\CzGram'
$Data = Join-Path $env:LOCALAPPDATA 'czgram'
$Cmd = Join-Path $Dest 'bin\czgram.cmd'

# First, so the key works again: this restores the Snipping Tool setting and stops the listener.
if (Test-Path $Cmd) { & $Cmd --restore-shortcut }

# In case the backup was already gone: the sign-in entry and the running listener.
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'CzGram hotkey' -ErrorAction SilentlyContinue
$pidFile = Join-Path $Data 'run\hotkey.pid'
if (Test-Path $pidFile) {
    $id = Get-Content $pidFile -ErrorAction SilentlyContinue
    $p = Get-Process -Id $id -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -like 'python*') { Stop-Process -Id $id -Force }
}

# The browser connector's registration.
foreach ($key in 'Google\Chrome', 'Chromium', 'Microsoft\Edge', 'BraveSoftware\Brave-Browser', 'Mozilla') {
    Remove-Item -Path "HKCU:\Software\$key\NativeMessagingHosts\cz.czgram.bridge" -ErrorAction SilentlyContinue
}

Remove-Item (Join-Path ([Environment]::GetFolderPath('Programs')) 'CzGram.lnk') -ErrorAction SilentlyContinue
$bin = Join-Path $Dest 'bin'
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath) {
    $kept = ($userPath -split ';' | Where-Object { $_ -and $_ -ne $bin }) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $kept, 'User')
}
Remove-Item -Recurse -Force $Dest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $Data 'native-host'), (Join-Path $Data 'run') -ErrorAction SilentlyContinue

if ($Purge) {
    Remove-Item -Recurse -Force $Data, (Join-Path $env:APPDATA 'czgram') -ErrorAction SilentlyContinue
    Write-Host 'CzGram, its settings and its data were removed.'
} else {
    Write-Host "CzGram was removed. Your settings are still in $env:APPDATA\czgram (delete them with -Purge)."
}
Write-Host 'If you added the browser extension, remove it in your browser too.'
