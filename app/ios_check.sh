#!/bin/bash
# In a booted iOS simulator: install the app, open it, and check that the page came up (the screenshot shows the
# page, not a blank or crashed app). Leaves shot-ios.png in the output folder.
#   bash app/ios_check.sh <simulator id> <App.app> [output folder]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SIM="$1"; APP="$2"; OUT="${3:-.}"; ID=org.electo.app
[ -d "$APP" ] || { echo "no app at $APP"; exit 1; }
mkdir -p "$OUT"
xcrun simctl install "$SIM" "$APP"
xcrun simctl launch "$SIM" "$ID"
ok=1
for i in $(seq 1 18); do           # up to three minutes: a CI simulator is slow, and the page is 5 MB
  sleep 10
  xcrun simctl io "$SIM" screenshot "$OUT/shot-ios.png" >/dev/null 2>&1 || continue
  if python3 "$HERE/shot_check.py" "$OUT/shot-ios.png" >/dev/null 2>&1; then ok=0; break; fi
done
python3 "$HERE/shot_check.py" "$OUT/shot-ios.png" || true
if [ "$ok" = 0 ]; then
  echo "the page came up in the simulator (after about $((i * 10)) seconds)"
  xcrun simctl spawn "$SIM" launchctl list 2>/dev/null | grep -q "$ID" || { echo "the app is not running any more"; ok=1; }
else
  echo "the page never came up in the simulator"
  echo "---- what the simulator logged for the app ----"
  xcrun simctl spawn "$SIM" log show --last 4m --predicate 'process == "App"' 2>/dev/null | tail -60 || true
fi
exit "$ok"
