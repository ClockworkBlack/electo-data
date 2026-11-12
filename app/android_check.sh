#!/bin/bash
# In a running emulator (or a phone on adb): install the APK, open it, and check that the page came up: its tab names
# are on the screen and the screenshot shows the page, not a blank or crashed app. Leaves shot-android.png and
# ui-android.xml in the output folder.
#   bash app/android_check.sh <apk> [output folder]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APK="$1"; OUT="${2:-.}"; ID=org.electo.app
[ -f "$APK" ] || { echo "no APK at $APK"; exit 1; }
mkdir -p "$OUT"
adb install -r "$APK"
adb logcat -c || true
adb shell am start -W -n "$ID/.MainActivity"
found=no
for i in $(seq 1 30); do           # up to two and a half minutes: a CI emulator is slow, and the page is 5 MB
  sleep 5
  adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1 || continue
  adb pull /sdcard/ui.xml "$OUT/ui-android.xml" >/dev/null 2>&1 || continue
  if grep -q "Live results" "$OUT/ui-android.xml"; then found=yes; break; fi
done
sleep 3
adb exec-out screencap -p > "$OUT/shot-android.png"
ok=0
if [ -z "$(adb shell pidof "$ID" | tr -d '\r')" ]; then echo "the app is not running any more"; ok=1; fi
if [ "$found" = yes ]; then echo "the page's tabs are on the screen (after about $((i * 5)) seconds)"; else echo "the page's tabs never appeared on the screen"; ok=1; fi
python3 "$HERE/shot_check.py" "$OUT/shot-android.png" || ok=1
if [ "$ok" != 0 ]; then
  echo "---- what Android logged for the app ----"
  adb logcat -d -t 400 | grep -iE "capacitor|chromium|electo|AndroidRuntime|FATAL" | tail -80 || true
fi
exit "$ok"
