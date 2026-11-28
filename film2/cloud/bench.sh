#!/bin/bash
# Ten-minute benchmark on a rented NVIDIA GPU machine: renders one 1080p frame of each scene in Cycles at
# final quality and prints the seconds each took. Paste the last lines back to Claude.
# usage:  curl -fsSL https://raw.githubusercontent.com/praveenchandrahas/Software-Defined-Home-Theatre/film2/film2/cloud/bench.sh | bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
command -v git >/dev/null || { apt-get update -q && apt-get install -y -q git curl; }
apt-get install -y -q --no-install-recommends fonts-inter libxi6 libxkbcommon0 libxxf86vm1 libxfixes3 libxrender1 libsm6 libgl1 libegl1 >/dev/null 2>&1 || true
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
[ -d sdht ] || git clone -q --depth 1 -b film2 https://github.com/praveenchandrahas/Software-Defined-Home-Theatre.git sdht
cd sdht/film2
uv venv -q -p 3.13 .venv
uv pip install -q --python .venv/bin/python bpy==5.3.0 OpenEXR numpy
PY=.venv/bin/python
gpu=optix
$PY blender/render.py echo --gpu optix --frames 60 --res 320x180 --samples 4 --out /tmp/warm 2>&1 | grep -E '"gpu"|no OPTIX' || gpu=cuda
echo "device: $gpu (first frame includes kernel loading)"
for s in echo:60 storm:26 drop:100 canyon:200 earth:121 shatter:40 title:150; do
  $PY blender/render.py "${s%%:*}" --engine cycles --gpu "$gpu" --frames "${s##*:}" --res 1920x1080 --samples 256 --out /tmp/bench \
    2>&1 | grep '"seconds"' || echo "{\"scene\": \"${s%%:*}\", \"error\": true}"
done
echo "done: paste the lines above to Claude"
