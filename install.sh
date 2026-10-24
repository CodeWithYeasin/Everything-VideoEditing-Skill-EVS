#!/usr/bin/env bash
# Everything-videoEditing installer (Linux / macOS)
#   bash install.sh                 # link the skill into Claude Code, Codex and Gemini CLI
#   bash install.sh --tools         # ...and install FFmpeg/Python tools + AI models (~3-5 GB)
#   bash install.sh --agents claude,codex
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="$HERE/skills/everything-video-editing"
AGENTS="claude,codex,gemini"
TOOLS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --tools) TOOLS=1 ;;
    --agents) shift; AGENTS="$1" ;;
    *) echo "unknown option $1"; exit 1 ;;
  esac
  shift
done
link() {  # $1 = skills folder of an agent
  mkdir -p "$1"
  ln -sfn "$SKILL" "$1/everything-video-editing"
  echo "linked -> $1/everything-video-editing"
}
case ",$AGENTS," in *,claude,*) link "$HOME/.claude/skills" ;; esac
case ",$AGENTS," in *,codex,*)  link "$HOME/.codex/skills" ;; esac
case ",$AGENTS," in *,gemini,*) link "$HOME/.gemini/skills"
  echo "  Gemini CLI: enable Agent Skills in /settings, or install as an extension:"
  echo "  gemini extensions install $HERE" ;; esac
if [ "$TOOLS" = 1 ]; then
  bash "$SKILL/setup/install_unix.sh"
else
  echo "Tools not installed. Run: bash install.sh --tools   (or check: python3 $SKILL/scripts/doctor.py)"
fi
