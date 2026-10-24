# Everything-videoEditing installer for Windows 10/11 (no admin rights needed).
#   powershell -ExecutionPolicy Bypass -File install_windows.ps1 [-Root D:\video-tools] [-Gpu] [-NoBlender] [-NoModels]
# Installs into one folder: FFmpeg 9 full build, a Python 3.11 env with Whisper,
# Demucs, CLAP (transformers), OpenCV, librosa; Blender 4.5 LTS portable; AI models.
# Re-running skips finished steps. Remotion needs Node.js 18+ (https://nodejs.org).
param(
  [string]$Root = "",
  [switch]$Gpu,
  [switch]$NoBlender,
  [switch]$NoModels
)
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
if (-not $Root) { $Root = if (Test-Path 'D:\') { 'D:\video-tools' } else { "$env:USERPROFILE\video-tools" } }
New-Item -ItemType Directory -Force $Root, "$Root\downloads", "$Root\models" | Out-Null
$log = "$Root\install.log"
function Log($m) { $t = Get-Date -Format 'HH:mm:ss'; "[$t] $m" | Tee-Object -FilePath $log -Append }
$SkillDir = Split-Path -Parent $PSScriptRoot

# 1. FFmpeg (gyan.dev full build via GitHub: libass, vidstab, rubberband, arnndn ...)
if (-not (Test-Path "$Root\ffmpeg\bin\ffmpeg.exe")) {
  $rel = Invoke-RestMethod https://api.github.com/repos/GyanD/codexffmpeg/releases/latest
  $url = ($rel.assets | Where-Object name -like '*full_build.zip' | Select-Object -First 1).browser_download_url
  Log "FFmpeg $($rel.tag_name): downloading"
  curl.exe -L -s -o "$Root\downloads\ffmpeg.zip" $url
  New-Item -ItemType Directory -Force "$Root\downloads\ffx" | Out-Null
  tar.exe -xf "$Root\downloads\ffmpeg.zip" -C "$Root\downloads\ffx" 2>$null
  Move-Item (Get-ChildItem "$Root\downloads\ffx" -Directory | Select-Object -First 1).FullName "$Root\ffmpeg"
  Remove-Item -Recurse -Force "$Root\downloads\ffx"
}
Log "FFmpeg: $(Test-Path "$Root\ffmpeg\bin\ffmpeg.exe")"

# 2. Python 3.11 env: conda if present, else uv (downloads its own Python)
$py = "$Root\env\python.exe"
if (-not (Test-Path $py)) {
  $conda = $env:CONDA_EXE
  if (-not $conda) { foreach ($c in "$env:USERPROFILE\anaconda3\Scripts\conda.exe", "$env:USERPROFILE\miniconda3\Scripts\conda.exe") { if (Test-Path $c) { $conda = $c } } }
  if ($conda) {
    Log "Python env via conda"
    & $conda create -y -q -p "$Root\env" -c conda-forge --override-channels python=3.11 2>&1 | Out-File -Append $log
  } else {
    Log "Python env via uv"
    $uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
    if (-not $uv) { & py -m pip install --user -q uv; $uv = (& py -c "import sysconfig,os;print(os.path.join(sysconfig.get_path('scripts','nt_user'),'uv.exe'))") }
    & $uv venv --python 3.11 "$Root\venv" 2>&1 | Out-File -Append $log
    & $uv pip install --python "$Root\venv\Scripts\python.exe" pip 2>&1 | Out-File -Append $log
    $py = "$Root\venv\Scripts\python.exe"
  }
}
if (-not (Test-Path $py) -and (Test-Path "$Root\venv\Scripts\python.exe")) { $py = "$Root\venv\Scripts\python.exe" }
Log "Python: $(& $py --version 2>&1)"

# 3. Packages
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
$torchIndex = if ($Gpu) { 'https://download.pytorch.org/whl/cu121' } else { 'https://download.pytorch.org/whl/cpu' }
& $py -c "import torch" 2>$null
if ($LASTEXITCODE -ne 0) {
  Log "pip: torch ($torchIndex)"
  & $py -m pip install -q torch==2.6.0 torchaudio==2.6.0 --index-url $torchIndex 2>&1 | Out-File -Append $log
}
Log 'pip: whisper, demucs, CLAP, opencv, librosa'
& $py -m pip install -q demucs openai-whisper faster-whisper "transformers>=4.40,<5" librosa soundfile scenedetect "opencv-python-headless<5" pillow numpy hf_xet edge-tts 2>&1 | Out-File -Append $log

# 4. Blender 4.5 LTS portable
$blender = "$Root\blender\blender.exe"
if (-not $NoBlender -and -not (Test-Path $blender)) {
  $html = (Invoke-WebRequest -UseBasicParsing https://download.blender.org/release/Blender4.5/).Content
  $zip = [regex]::Matches($html, 'blender-4\.5\.(\d+)-windows-x64\.zip') | Sort-Object { [int]$_.Groups[1].Value } | Select-Object -Last 1
  Log "Blender: downloading $($zip.Value)"
  curl.exe -L -s -o "$Root\downloads\blender.zip" "https://download.blender.org/release/Blender4.5/$($zip.Value)"
  New-Item -ItemType Directory -Force "$Root\downloads\blx" | Out-Null
  tar.exe -xf "$Root\downloads\blender.zip" -C "$Root\downloads\blx" 2>$null
  Move-Item (Get-ChildItem "$Root\downloads\blx" -Directory | Select-Object -First 1).FullName "$Root\blender"
  Remove-Item -Recurse -Force "$Root\downloads\blx"
}

# 5. Config (the skill reads ~/.everything-video/config.json)
$cfg = [ordered]@{ root = $Root; python = $py; ffmpeg = "$Root\ffmpeg\bin\ffmpeg.exe"; ffprobe = "$Root\ffmpeg\bin\ffprobe.exe";
  blender = $(if (Test-Path $blender) { $blender } else { $null }); hf_home = "$Root\models\hf"; torch_home = "$Root\models\torch";
  whisper_dir = "$Root\models\whisper"; device = $(if ($Gpu) { 'cuda' } else { 'cpu' }) }
$json = $cfg | ConvertTo-Json
New-Item -ItemType Directory -Force "$env:USERPROFILE\.everything-video" | Out-Null
[IO.File]::WriteAllText("$Root\config.json", $json)
[IO.File]::WriteAllText("$env:USERPROFILE\.everything-video\config.json", $json)

# 6. Models
if (-not $NoModels) {
  $env:HF_HOME = "$Root\models\hf"; $env:TORCH_HOME = "$Root\models\torch"; $env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
  Log 'Models: whisper small+medium, demucs, CLAP'
  & $py "$PSScriptRoot\predownload.py" 2>&1 | Tee-Object -FilePath $log -Append
}
Log 'ALL DONE. Check with: python scripts\doctor.py'
