#!/usr/bin/env python3
"""The text of a release (what each file is, how to install it, what was checked), written by the apps workflow.

    python3 app/notes.py android > notes.md      (reads Electo.apk and, when it is there, Electo-with-AI.apk)
    python3 app/notes.py ios > notes.md          (reads Electo-unsigned.ipa)

From the build's environment: APP_VERSION_NAME, APP_VERSION_CODE, APP_BUILD, SITE_BUILT, GITHUB_REPOSITORY; for
Android also SIGNING (project or one-time), CERT_SHA256, EMULATOR_API, and models/models-used.json for what the
offline AI's files are."""
import datetime as dt
import hashlib
import json
import os
import sys

ENV = os.environ
REPO = ENV.get("GITHUB_REPOSITORY", "ClockworkBlack/electo-data")
ANDROID = {"33": "13", "34": "14", "35": "15", "36": "16"}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def size(path):
    n = os.path.getsize(path)
    return "%.1f GB" % (n / 1e9) if n >= 1e9 else "%d MB" % round(n / 1e6)


def when(iso):
    try:
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        return "%s %d, %d, %02d:%02d UTC" % (t.strftime("%B"), t.day, t.year, t.hour, t.minute)
    except ValueError:
        return iso


def now():
    return when(dt.datetime.now(dt.timezone.utc).isoformat())


def ai_inside():
    """What the offline AI's files are, for one sentence."""
    try:
        u = json.load(open(os.path.join("models", "models-used.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return "the offline AI's model and the dictation and voice models"
    if u.get("model"):
        name = u["model"]["id"].split("-Instruct")[0].split("-q4")[0]
        return "the offline AI's model (%s, the stock model by the Qwen team) and the dictation and voice models" % name
    ids = [f[:-4] for f in u.get("files", []) if f.endswith(".zip")]
    trained = [i for i in ids if i.startswith("Electo-")]
    if trained:
        return "the offline AI's model (%s, trained on Electo's data) and the dictation and voice models" % ", ".join(
            i.replace("Electo-", "").split("-q4")[0] for i in trained)
    return "the offline AI's model (%s) and the dictation and voice models" % ", ".join(ids)


def android():
    ai = os.path.exists("Electo-with-AI.apk")
    api = ENV.get("EMULATOR_API", "35")
    out = []
    out.append("**Electo for Android.** On the phone, download %s below, open it, and allow installs from this source when "
               "Android asks. It is not from the Play Store." % ("one of the two files" if ai else "**Electo.apk**"))
    out.append("")
    out.append("| File | Size | What is inside |")
    out.append("|---|---|---|")
    out.append("| **Electo.apk** | %s | The site and all of its data. The offline AI is optional: the app downloads its model "
               "(about 1 GB) the first time you turn it on in AI settings. |" % size("Electo.apk"))
    if ai:
        out.append("| **Electo-with-AI.apk** | %s | The same app with %s inside, so nothing else is downloaded. Needs about "
                   "3 GB free. |" % (size("Electo-with-AI.apk"), ai_inside()))
    out.append("")
    out.append("- %s without a connection. The **Data** button at the top brings newer data and newer versions of the "
               "page; the app also checks by itself when it opens." % ("Both open" if ai else "It opens"))
    out.append("- The offline AI needs a phone with WebGPU: a recent Android with Chrome and Android System WebView up to date.")
    out.append("- Speak and \"Use my location\" ask Android for the microphone and the location the first time you use them.")
    if ENV.get("SIGNING") == "project":
        out.append("- Signed with Electo's own key: a newer download installs over this one and keeps its settings.")
    else:
        out.append("- **Test signature.** This build is signed with a key made for it alone, so it does not install over "
                   "an earlier Electo: uninstall the earlier one first (its saved settings go with it). %s" % (
                       "The two files here share the key, so one installs over the other." if ai else ""))
    out.append("")
    out.append("Version %s (%s), built %s from the site as of %s." % (
        ENV.get("APP_VERSION_NAME", "?"), ENV.get("APP_VERSION_CODE", "?"), now(), when(ENV.get("SITE_BUILT", "?"))))
    checked = ["**Electo.apk** was installed and opened in an Android %s emulator, and the page came up (screenshot below)" % ANDROID.get(api, "(API %s)" % api)]
    if ai:
        checked.append("so was **Electo-with-AI.apk**" if os.path.exists(os.path.join("check-ai", "ok")) else "**Electo-with-AI.apk** was not checked this way")
    out.append("Checked before publishing: %s. The offline AI was not run there: an emulator has no WebGPU." % "; ".join(checked))
    out.append("")
    out.append("SHA-256 of Electo.apk: `%s`" % sha("Electo.apk"))
    if ai:
        out.append("SHA-256 of Electo-with-AI.apk: `%s`" % sha("Electo-with-AI.apk"))
    out.append("Signing certificate (SHA-256): `%s`" % ENV.get("CERT_SHA256", "?"))
    out.append("")
    out.append("![Electo in the Android emulator](https://github.com/%s/releases/download/android/Electo-android.png)" % REPO)
    return "\n".join(out)


def ios():
    f = "Electo-unsigned.ipa"
    out = []
    out.append("**Electo for iPhone and iPad (unsigned build).** An iPhone installs only apps signed with an Apple developer "
               "certificate, so **%s** cannot be opened on the phone the way an Android APK can. Two ways to use it:" % f)
    out.append("")
    out.append("- With a sideloading tool on a computer (AltStore or Sideloadly, for example), which signs the file with "
               "your own Apple ID and puts it on your phone. With a free Apple ID the app has to be refreshed every 7 days.")
    out.append("- With an Apple Developer account, to sign it or to send it to TestFlight and the App Store.")
    out.append("")
    out.append("Without either, the site itself works as an app on an iPhone: open https://clockworkblack.github.io/electo-data/ "
               "in Safari, then Share → Add to Home Screen.")
    out.append("")
    out.append("- The site and all of its data are inside (%s). The **Data** button at the top brings newer data and newer "
               "versions of the page." % size(f))
    out.append("- The offline AI is optional and needs iOS 26 or newer; the app downloads its model (about 1 GB) the first "
               "time you turn it on.")
    out.append("")
    out.append("Version %s (%s), built %s from the site as of %s." % (
        ENV.get("APP_VERSION_NAME", "?"), ENV.get("APP_BUILD", "?"), now(), when(ENV.get("SITE_BUILT", "?"))))
    out.append("Checked before publishing: the app was opened in an %s simulator, and the page came up (screenshot below). "
               "It has not been run on a real iPhone." % ENV.get("SIM_NAME", "iPhone"))
    out.append("")
    out.append("SHA-256 of %s: `%s`" % (f, sha(f)))
    out.append("")
    out.append("![Electo in the iPhone simulator](https://github.com/%s/releases/download/ios/Electo-ios.png)" % REPO)
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("android", "ios"):
        sys.exit(__doc__)
    print(android() if sys.argv[1] == "android" else ios())
