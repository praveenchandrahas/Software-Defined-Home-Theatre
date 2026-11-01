#!/usr/bin/env bash
# Runs shellcheck over every shell script of a repository and a syntax check of every Python file. Fails on any finding at --severity (default warning).
#   ci-lint.sh [--repo DIR] [--severity error|warning|info|style]
set -uo pipefail
REPO=.; SEV=warning
while [ $# -gt 0 ]; do case "$1" in --repo) REPO=$2; shift 2 ;; --severity) SEV=$2; shift 2 ;; *) echo "unknown: $1" >&2; exit 2 ;; esac; done
cd "$REPO" || exit 1
command -v shellcheck >/dev/null || { echo "shellcheck is not installed" >&2; exit 1; }
sh_files=(); py_files=()
while IFS= read -r f; do
  [ -f "$f" ] && [ ! -L "$f" ] || continue
  first=$(head -c 120 "$f" 2>/dev/null | head -1 || true)
  case "$f" in *.sh|*.bash) sh_files+=("$f"); continue ;; *.py) py_files+=("$f"); continue ;; esac
  case "$first" in
    '#!'*bash*|'#!'*/sh|'#!'*' sh'|'#!/bin/sh'*) sh_files+=("$f") ;;
    '#!'*python*) py_files+=("$f") ;;
  esac
done < <(git ls-files 2>/dev/null || find . -type f -not -path './.git/*')
rc=0
echo "shellcheck (${#sh_files[@]} files, severity $SEV)"
if [ ${#sh_files[@]} -gt 0 ]; then
  shellcheck --severity="$SEV" -x "${sh_files[@]}" || rc=1
fi
echo "python syntax (${#py_files[@]} files)"
for f in "${py_files[@]}"; do
  python3 -I -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1])' "$f" || { echo "syntax error: $f"; rc=1; }
done
[ $rc = 0 ] && echo "lint OK" || echo "lint FAILED"
exit $rc
