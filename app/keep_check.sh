#!/bin/bash
# The last check's screenshot (and, on Android, the screen's text) on the "app-check" release, whether the check
# passed or not, so a failed build can be looked at without signing in: <platform>-shot.png, <platform>-ui.xml, and
# <platform>-icon.png (the app's icon as the system shows it).
#   bash app/keep_check.sh android|ios [folder]        (needs GH_TOKEN and the gh CLI)
P="$1"; D="${2:-check}"
[ -d "$D" ] || { echo "nothing to keep: no $D folder"; exit 0; }
T=$(mktemp -d); n=0
for f in "$D"/shot-*.png; do [ -f "$f" ] && { cp "$f" "$T/$P-shot.png"; n=$((n+1)); }; done
for f in "$D"/ui-*.xml; do [ -f "$f" ] && { cp "$f" "$T/$P-ui.xml"; n=$((n+1)); }; done
for f in "$D"/icon-*.png; do [ -f "$f" ] && { cp "$f" "$T/$P-icon.png"; n=$((n+1)); }; done
[ "$n" -gt 0 ] || { echo "nothing to keep: the check left no files"; exit 0; }
gh release view app-check >/dev/null 2>&1 || gh release create app-check --prerelease --latest=false --title "App checks (latest screenshots)" \
  --notes "What the apps workflow saw the last time it opened each app before publishing: a screenshot from the Android emulator and from the iPhone simulator. Kept for looking into a failed build; the apps themselves are on the android and ios releases." || true
gh release upload app-check "$T"/* --clobber && echo "kept on the app-check release: $(ls "$T" | tr '\n' ' ')" || echo "could not keep the check's files"
exit 0
