#!/usr/bin/env bash
# Sets the GitHub topics ("tags" in the repository's About box) on the seven repositories (Roomtone is the former theater-measurement). Touches GitHub metadata only, no code.
#   ./scripts/github-topics.sh            DRY RUN: prints what it would do
#   ./scripts/github-topics.sh --apply    does it (needs `gh auth login` once; adds topics, never removes any)
OWNER="${SDHT_OWNER:-praveenchandrahas}"
COMMON="software-defined-home-theatre home-theater linux pipewire"
declare -A T=(
  [Software-Defined-Home-Theatre]="diy dolby-atmos dts-x camilladsp mpv room-correction object-audio"
  [linux-theater-dsp]="upmixer surround-sound camilladsp room-correction dolby-atmos python"
  [mpv-object-audio]="mpv dolby-atmos dts-x object-audio omniphony"
  [seekthumbs]="mpv uosc rclone thumbnails seek-bar python"
  [mpv-shelf]="mpv uosc tmdb library-browser lua python"
  [Roomtone]="room-correction acoustic-measurement audio-analysis microphone-calibration camilladsp python"
  [Spatial-Lab]="spatial-audio immersive-audio vbap 5-1-2 camilladsp threejs aiohttp multichannel-audio audio-test-tools psychoacoustics"
)
APPLY=0; [ "${1:-}" = "--apply" ] && APPLY=1
[ "$APPLY" = 1 ] && ! command -v gh >/dev/null && { echo "gh not found"; exit 1; }
for r in Software-Defined-Home-Theatre linux-theater-dsp mpv-object-audio seekthumbs mpv-shelf Roomtone Spatial-Lab; do
  args=(); for t in $COMMON ${T[$r]}; do args+=(--add-topic "$t"); done
  if [ "$APPLY" = 1 ]; then echo "== $OWNER/$r"; gh repo edit "$OWNER/$r" "${args[@]}" || echo "   failed (gh auth login?)"
  else echo "gh repo edit $OWNER/$r ${args[*]}"; fi
done
[ "$APPLY" = 1 ] || echo "(dry run: nothing was changed; add --apply to do it)"
