# Everything-videoEditing installer (Windows, no admin needed)
#   powershell -ExecutionPolicy Bypass -File install.ps1             # link the skill into Claude Code, Codex, Gemini CLI
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Tools      # ...and install FFmpeg, Python tools, Blender, AI models
#   ... -Tools -Root D:\video-tools -Gpu                              # choose the install folder / NVIDIA GPU (4 GB+)
param(
  [string]$Agents = "claude,codex,gemini",
  [switch]$Tools,
  [string]$Root = "",
  [switch]$Gpu
)
$ErrorActionPreference = 'Stop'
$skill = Join-Path $PSScriptRoot 'skills\everything-video-editing'
function Link($dir) {
  New-Item -ItemType Directory -Force $dir | Out-Null
  $target = Join-Path $dir 'everything-video-editing'
  if (Test-Path $target) { (Get-Item $target).Delete() }
  New-Item -ItemType Junction -Path $target -Target $skill | Out-Null
  Write-Output "linked -> $target"
}
$list = $Agents.Split(',') | ForEach-Object { $_.Trim().ToLower() }
if ($list -contains 'claude') { Link "$env:USERPROFILE\.claude\skills" }
if ($list -contains 'codex')  { Link "$env:USERPROFILE\.codex\skills" }
if ($list -contains 'gemini') {
  Link "$env:USERPROFILE\.gemini\skills"
  Write-Output "  Gemini CLI: enable Agent Skills in /settings, or: gemini extensions install `"$PSScriptRoot`""
}
if ($Tools) {
  $args2 = @('-ExecutionPolicy', 'Bypass', '-File', (Join-Path $skill 'setup\install_windows.ps1'))
  if ($Root) { $args2 += @('-Root', $Root) }
  if ($Gpu) { $args2 += '-Gpu' }
  & powershell @args2
} else {
  Write-Output "Tools not installed. Run again with -Tools (or check: python $skill\scripts\doctor.py)"
}
