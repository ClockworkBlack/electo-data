#!/bin/bash
# After `npx cap add ios` on a Mac (the Xcode project is generated at build time, never committed): the icon, the
# opening screen, and the sentences iOS shows before the app may use the microphone or the location (without them
# iOS refuses both).
#   cd app && npx cap add ios && bash ios.sh && npx cap sync ios
set -e
cd "$(dirname "$0")"
P=ios/App/App
[ -f "$P/Info.plist" ] || { echo "Run npx cap add ios first (in app/, on a Mac)"; exit 1; }
python3 - "$P/Info.plist" <<'PY'
import plistlib, sys
p = sys.argv[1]
with open(p, "rb") as f:
    d = plistlib.load(f)
d["CFBundleDisplayName"] = "Electo"
d["NSMicrophoneUsageDescription"] = "Electo listens only while you use Speak, to turn what you say into text."
d["NSSpeechRecognitionUsageDescription"] = "If you choose this device's own dictation instead of Electo's, Apple turns what you say into text and may use its online service to do it."
d["NSLocationWhenInUseUsageDescription"] = "Electo uses your location only when you tap Use my location, to find your county and districts in its own data."
d["ITSAppUsesNonExemptEncryption"] = False      # only the system's HTTPS
with open(p, "wb") as f:
    plistlib.dump(d, f)
print("Info.plist:", ", ".join(k for k in d if k.startswith("NS") and k.endswith("UsageDescription")))
PY
n=0; for f in "$P"/Assets.xcassets/AppIcon.appiconset/*.png; do [ -f "$f" ] && { cp ios-patches/AppIcon-512@2x.png "$f"; n=$((n+1)); }; done
m=0; for f in "$P"/Assets.xcassets/Splash.imageset/*.png; do [ -f "$f" ] && { cp ios-patches/splash-2732x2732.png "$f"; m=$((m+1)); }; done
echo "iOS project patched: Info.plist, $n icon file(s), $m opening-screen file(s)"
[ "$n" = 1 ] || echo "note: expected one icon file in AppIcon.appiconset, found $n (a different Capacitor template?)"
