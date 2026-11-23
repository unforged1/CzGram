# Installs CzGram for the current Windows user. No administrator rights are needed, except that
# Windows asks once if Tesseract (the OCR engine) has to be installed.
#
#   powershell -ExecutionPolicy Bypass -File packaging\windows\install.ps1
#
# Puts CzGram in %LOCALAPPDATA%\Programs\CzGram, adds a Start menu entry and a `czgram` command,
# and keeps the Czech OCR data in %LOCALAPPDATA%\czgram\tessdata. Python and Tesseract come from
# winget when they're missing. Remove it all with packaging\windows\uninstall.ps1.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest is far slower with a progress bar
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Dest = Join-Path $env:LOCALAPPDATA 'Programs\CzGram'
$Data = Join-Path $env:LOCALAPPDATA 'czgram'
# The same file as Debian's tesseract-ocr-ces, so OCR reads the same on both.
$CesUrl = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/ces.traineddata'
$CesSha256 = '934bcaf97ef3348413263331131c9fa7f55f30db333c711929c124fb635f7e1b'

function Say($text) { Write-Host "==> $text" -ForegroundColor Cyan }

# Runs a program and returns its exit code. Windows PowerShell turns anything a program writes to
# stderr into an error, which 'Stop' above would make fatal; here only the exit code counts.
function Native {
    $ErrorActionPreference = 'Continue'
    $exe, $rest = $args
    & $exe @rest 2>&1 | ForEach-Object { Write-Host "    $_" }
    return $LASTEXITCODE
}

function Find-Python {
    # The Microsoft Store's python.exe placeholder fails this check, so it's never picked.
    $probe = 'import sys, tkinter; print(sys.version_info >= (3, 9)); print(sys.executable)'
    $candidates = @(@('py', '-3'), @('python'), @('python3'))
    foreach ($c in $candidates) {
        if (-not (Get-Command $c[0] -ErrorAction SilentlyContinue)) { continue }
        try {
            $ErrorActionPreference = 'Continue'
            $out = & $c[0] @($c | Select-Object -Skip 1) -c $probe 2>$null
            if ($LASTEXITCODE -eq 0 -and $out -and $out[0] -eq 'True') { return $out[1] }
        } catch { }
    }
    foreach ($v in '313', '312', '311', '310') {
        $p = Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe"
        if (Test-Path $p) { return $p }
    }
    return $null
}

function Find-Tesseract {
    $cmd = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($base in $env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs')) {
        if (-not $base) { continue }
        $p = Join-Path $base 'Tesseract-OCR\tesseract.exe'
        if (Test-Path $p) { return $p }
    }
    return $null
}

function Winget-Install($id, $scope) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget isn't available. Install $id yourself, then run this script again."
    }
    $wargs = @('install', '--exact', '--id', $id, '--silent', '--accept-package-agreements', '--accept-source-agreements')
    if ($scope) { $wargs += @('--scope', $scope) }
    $code = Native winget @wargs
    if ($code -ne 0) { throw "winget couldn't install $id (exit $code)." }
}

# ---------------------------------------------------------------- Python with Tk
Say 'Looking for Python 3.9 or later with Tk'
$Python = Find-Python
if (-not $Python) {
    Say 'Installing Python 3.13 with winget'
    Winget-Install 'Python.Python.3.13' 'user'
    $Python = Find-Python
    if (-not $Python) { throw 'Python was installed, but not found. Open a new terminal and run this script again.' }
}
$PythonW = Join-Path (Split-Path $Python) 'pythonw.exe'
if (-not (Test-Path $PythonW)) { $PythonW = $Python }
Write-Host "    $Python"

if ((Native $Python -c 'import PIL') -ne 0) {
    Say 'Installing Pillow'
    if ((Native $Python -m pip install --user --disable-pip-version-check --quiet Pillow) -ne 0) {
        throw 'pip could not install Pillow.'
    }
}

# ---------------------------------------------------------------- Tesseract and Czech data
$Tesseract = Find-Tesseract
if (-not $Tesseract) {
    Say 'Installing Tesseract OCR with winget (Windows may ask for permission)'
    Winget-Install 'UB-Mannheim.TesseractOCR' $null
    $Tesseract = Find-Tesseract
    if (-not $Tesseract) { throw 'Tesseract was installed, but not found.' }
}
Write-Host "    $Tesseract"

$Tessdata = Join-Path $Data 'tessdata'
$Ces = Join-Path $Tessdata 'ces.traineddata'
New-Item -ItemType Directory -Force -Path $Tessdata | Out-Null
if (-not (Test-Path $Ces) -or (Get-FileHash $Ces -Algorithm SHA256).Hash -ne $CesSha256) {
    Say 'Downloading the Czech OCR data'
    $tmp = "$Ces.download"
    Invoke-WebRequest -UseBasicParsing -Uri $CesUrl -OutFile $tmp
    $hash = (Get-FileHash $tmp -Algorithm SHA256).Hash
    if ($hash -ne $CesSha256) {
        Remove-Item $tmp -Force
        throw "The Czech OCR data didn't match its expected checksum (got $hash)."
    }
    Move-Item -Force $tmp $Ces
}

# ---------------------------------------------------------------- CzGram itself
Say "Copying CzGram to $Dest"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
foreach ($old in 'czgram', 'extension') {
    $p = Join-Path $Dest $old
    if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}
New-Item -ItemType Directory -Force -Path (Join-Path $Dest 'czgram') | Out-Null
Copy-Item (Join-Path $Repo 'czgram\*.py') (Join-Path $Dest 'czgram')
Copy-Item -Recurse (Join-Path $Repo 'extension') (Join-Path $Dest 'extension')
foreach ($f in 'czgram.pyw', 'LICENSE', 'README.md') { Copy-Item (Join-Path $Repo $f) $Dest }
$null = Native $Python -m compileall -q (Join-Path $Dest 'czgram')
if ((Native $Python (Join-Path $PSScriptRoot 'make_icon.py') (Join-Path $Dest 'czgram.ico')) -ne 0) {
    throw 'Could not create the icon.'
}

# The czgram command, for --usage, --restore-shortcut and the rest.
$Bin = Join-Path $Dest 'bin'
New-Item -ItemType Directory -Force -Path $Bin | Out-Null
$launcher = Join-Path $Dest 'czgram.pyw'
# cmd.exe reads batch files in the OEM code page, so a folder like C:\Users\Jiří must be written in
# it (czgram/windows.py's write_batch does the same for the browser connector).
$run = "`"$Python`" `"$launcher`" %*"
$oem = [Text.Encoding]::GetEncoding([Globalization.CultureInfo]::CurrentCulture.TextInfo.OEMCodePage)
if ($oem.GetString($oem.GetBytes($run)) -eq $run) {
    $lines, $enc = @('@echo off', $run), $oem
} else {
    $lines, $enc = @('@echo off', 'chcp 65001 >nul', $run), (New-Object Text.UTF8Encoding $false)
}
[IO.File]::WriteAllText((Join-Path $Bin 'czgram.cmd'), (($lines -join "`r`n") + "`r`n"), $enc)
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not $userPath) { $userPath = '' }
if (($userPath -split ';') -notcontains $Bin) {
    [Environment]::SetEnvironmentVariable('Path', (($userPath.TrimEnd(';'), $Bin) -join ';').TrimStart(';'), 'User')
}

# Start menu entry. pythonw keeps a console window from opening.
$Programs = [Environment]::GetFolderPath('Programs')
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $Programs 'CzGram.lnk'))
$lnk.TargetPath = $PythonW
$lnk.Arguments = "`"$launcher`""
$lnk.WorkingDirectory = $Dest
$lnk.IconLocation = (Join-Path $Dest 'czgram.ico')
$lnk.Description = 'Czech grammar on the PrintScreen key'
$lnk.Save()

Say 'Done'
Write-Host @"

Open CzGram from the Start menu, choose your settings and press Save. Then press PrintScreen
on a Czech exercise. Saving turns off Windows' "Print screen opens Snipping Tool" option; to get
it back, untick the option in CzGram or run:  czgram --restore-shortcut

The czgram command works in terminals opened from now on.
"@
