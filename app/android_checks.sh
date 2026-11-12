#!/bin/bash
# The emulator's part of an Android build: Electo.apk must open and show the page (or the build stops); then, when
# it was built, Electo-with-AI.apk the same way (a failure there only keeps that one file from being published:
# check-ai/ok is left when it passed).
#   bash app/android_checks.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf check check-ai          # a second try starts clean: nothing an earlier try saw counts for this one
bash "$HERE/android_check.sh" Electo.apk check
if [ -f Electo-with-AI.apk ]; then
  adb uninstall org.electo.app >/dev/null 2>&1 || true
  if bash "$HERE/android_check.sh" Electo-with-AI.apk check-ai; then touch check-ai/ok
  else echo "::warning::Electo-with-AI.apk did not pass the emulator check; it is not published"; fi
fi
