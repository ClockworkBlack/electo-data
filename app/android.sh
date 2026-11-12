#!/bin/bash
# After `npx cap add android` (the Android project is generated at build time, never committed): Electo's activity
# (service-worker requests reach the app's own files; a page Android killed restarts instead of closing the app; Back
# closes pop-ups first), the icon and opening screen, the permissions behind Speak and "Use my location", the
# version, and the signing key.
#   cd app && npx cap add android && bash android.sh && npx cap sync android && (cd android && ./gradlew assembleRelease)
# Environment (all optional):
#   APP_VERSION_CODE, APP_VERSION_NAME    this build's number and name; a later build must carry a larger number
#   ANDROID_KEYSTORE_FILE (a path), ANDROID_KEYSTORE_PASSWORD, ANDROID_KEY_ALIAS, ANDROID_KEY_PASSWORD
#                                         the release build is signed with this key (never kept in the repository);
#                                         without them Gradle leaves the release build unsigned
set -e
cd "$(dirname "$0")"
[ -d android/app ] || { echo "Run npx cap add android first (in app/)"; exit 1; }
id=$(python3 -c "import json; print(json.load(open('capacitor.config.json'))['appId'])")
dir="android/app/src/main/java/$(echo "$id" | tr . /)"
mkdir -p "$dir"; cp android-patches/MainActivity.java "$dir/MainActivity.java"
sed -i "1s/^package .*;/package $id;/" "$dir/MainActivity.java"
# the icon and the opening screen (drawn by icon/make.sh)
cp -r android-patches/res/. android/app/src/main/res/
# the manifest: no Android backup of the app's data (AI keys a reader pasted live in its storage), no plain-HTTP
# traffic; the microphone for Speak and the location for "Use my location" (Android asks the reader the first time
# each is used; without these lines the page's own request is refused silently)
python3 - <<'PY'
import re
p = "android/app/src/main/AndroidManifest.xml"; t = open(p, encoding="utf-8").read()
def attr(t, name, val):
    pat = r'android:%s="[^"]*"' % name
    if re.search(pat, t):
        return re.sub(pat, 'android:%s="%s"' % (name, val), t, count=1)
    return t.replace("<application", '<application android:%s="%s"' % (name, val), 1)
for k, v in (("allowBackup", "false"), ("fullBackupContent", "false"), ("usesCleartextTraffic", "false")):
    t = attr(t, k, v)
add = ""
for perm in ("RECORD_AUDIO", "MODIFY_AUDIO_SETTINGS", "ACCESS_COARSE_LOCATION", "ACCESS_FINE_LOCATION"):
    if "android.permission." + perm + '"' not in t:
        add += '    <uses-permission android:name="android.permission.%s" />\n' % perm
for feat in ("microphone", "location", "location.gps"):       # asked for, never required: any phone or tablet may install
    if "android.hardware." + feat + '"' not in t:
        add += '    <uses-feature android:name="android.hardware.%s" android:required="false" />\n' % feat
if add:
    t = t.replace("</manifest>", add + "</manifest>", 1)
open(p, "w", encoding="utf-8").write(t)
PY
g=android/app/build.gradle
if [ -n "${APP_VERSION_CODE:-}" ]; then sed -i -E "s/versionCode [0-9]+/versionCode ${APP_VERSION_CODE}/" "$g"; fi
if [ -n "${APP_VERSION_NAME:-}" ]; then sed -i -E "s/versionName \"[^\"]*\"/versionName \"${APP_VERSION_NAME}\"/" "$g"; fi
grep -q "Electo: build settings" "$g" || cat >> "$g" <<'GRADLE'

// Electo: build settings. The offline AI's files (weights, kernels, speech models) stay uncompressed in the APK, so the
// app reads them in place; the wrapper has no code of its own worth shrinking or linting.
android {
    androidResources {
        noCompress 'bin', 'wasm', 'onnx'
    }
    lint {
        checkReleaseBuilds false
        abortOnError false
    }
    buildTypes {
        release {
            minifyEnabled false
        }
    }
}
GRADLE
if [ -n "${ANDROID_KEYSTORE_FILE:-}" ]; then
  [ -f "$ANDROID_KEYSTORE_FILE" ] || { echo "no keystore at $ANDROID_KEYSTORE_FILE"; exit 1; }
  grep -q "Electo: release signing" "$g" || cat >> "$g" <<'GRADLE'

// Electo: release signing with the key the build was given (app/android.sh; the key is never in the repository)
android {
    signingConfigs {
        electoRelease {
            storeFile file(System.getenv('ANDROID_KEYSTORE_FILE'))
            storePassword System.getenv('ANDROID_KEYSTORE_PASSWORD')
            keyAlias System.getenv('ANDROID_KEY_ALIAS')
            keyPassword System.getenv('ANDROID_KEY_PASSWORD')
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.electoRelease
        }
    }
}
GRADLE
  echo "release signing: the key at $ANDROID_KEYSTORE_FILE"
fi
echo "Android project patched: $dir/MainActivity.java, $g (version $(grep -E 'versionCode|versionName' "$g" | tr -s ' ' | tr '\n' ' ')), AndroidManifest.xml"
