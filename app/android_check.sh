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
UI="$OUT/ui-android.xml"
adb install -r "$APK"
adb logcat -c || true
adb shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS >/dev/null 2>&1 || true   # a slow emulator's own "isn't responding" boxes
adb shell am start -W -n "$ID/.MainActivity"
# One of Android's own boxes ("... isn't responding", "... keeps stopping") lies over the app and is all the screen's
# text says while it is up. About Electo itself: wait when it is only slow (a CI emulator is); a crash is left on
# the screen and fails the check below. About another program (the emulator's own launcher, mostly: Android 14 puts
# the box back every five seconds for as long as that program hangs, Nov. 12, 2026): wait once, then close that
# program, which Android starts again by itself when it is needed.
others=0; crashed=no
answer() {
  local says b xy
  says=$(python3 "$HERE/ui_text.py" "$UI" | cut -c1-200); echo "Android says: $says"
  case "$says" in
    *Electo\ isn*) b="Wait" ;;
    *Electo\ keeps\ stopping*|*Electo\ has\ stopped*) crashed=yes; return 0 ;;
    *) others=$((others + 1)); b="Close app"
       if [ "$others" -le 1 ] && [ -n "$(python3 "$HERE/ui_text.py" "$UI" "Wait")" ]; then b="Wait"; fi ;;
  esac
  xy=$(python3 "$HERE/ui_text.py" "$UI" "$b")
  if [ -n "$xy" ]; then echo "  answered: $b"; adb shell input tap $xy || true; fi
}
found=no
for i in $(seq 1 30); do           # up to about three minutes: a CI emulator is slow, and the page is 5 MB
  sleep 5
  adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1 || continue
  adb pull /sdcard/ui.xml "$UI" >/dev/null 2>&1 || continue
  if grep -q "Live results" "$UI"; then found=yes; break; fi
  if grep -Eq "isn(&apos;|')t responding|keeps stopping|has stopped" "$UI"; then answer; fi
  if [ "$crashed" = yes ]; then break; fi
done
sleep 3
adb exec-out screencap -p > "$OUT/shot-android.png"
ok=0
if [ -z "$(adb shell pidof "$ID" | tr -d '\r')" ]; then echo "the app is not running any more"; ok=1; fi
if [ "$found" = yes ]; then echo "the page's tabs are on the screen (after about $((i * 5)) seconds)"
else echo "the page's tabs never appeared; the screen says: $(python3 "$HERE/ui_text.py" "$UI" 2>/dev/null || echo '(nothing readable)')"; ok=1; fi
python3 "$HERE/shot_check.py" "$OUT/shot-android.png" || ok=1
# nothing of Android's own over the page: a title bar there means the window was built with the wrong theme
if grep -q 'resource-id="android:id/action_bar_container"' "$UI" 2>/dev/null; then echo "a title bar of Android's own is over the page"; ok=1; fi
# the app's icon and name as Android shows them (its "App info" screen), for a person to look at
adb shell am start -W -a android.settings.APPLICATION_DETAILS_SETTINGS -d "package:$ID" >/dev/null 2>&1 && sleep 4 \
  && adb exec-out screencap -p > "$OUT/icon-android.png" || true
adb shell am start -n "$ID/.MainActivity" >/dev/null 2>&1 || true
if [ "$ok" != 0 ]; then
  echo "---- what Android logged for the app ----"
  adb logcat -d -t 3000 | grep -iE "capacitor|chromium|cr_|electo|FATAL|WebView" | grep -v "nativeloader" | tail -80 || true
fi
exit "$ok"
