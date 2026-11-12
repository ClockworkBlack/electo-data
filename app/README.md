# Electo as a phone app

The app is the site this repository publishes, wrapped with [Capacitor](https://capacitorjs.com) for Android and iOS.
The **apps** workflow (`.github/workflows/apps.yml`) builds it here, on GitHub's own machines, from the branch
`current.json` names: the page, all of its data, and the offline AI's library. Nothing comes from a private
repository, and no secret is needed to build.

| | File | Where | What it is |
|---|---|---|---|
| Android | `Electo.apk` | [android release](https://github.com/ClockworkBlack/electo-data/releases/tag/android) | The site and its data. The offline AI's model is downloaded the first time it is turned on. |
| Android | `Electo-with-AI.apk` | same | The same app with the offline AI's model and the dictation and voice models inside. |
| iPhone, iPad | `Electo-unsigned.ipa` | [ios release](https://github.com/ClockworkBlack/electo-data/releases/tag/ios) | The site and its data, unsigned: an iPhone installs it only after it is signed (below). |

The workflow runs every Monday, on a change to `app/`, and by hand (Actions → apps → Run workflow; `what`: android,
ios or both). A phone that has the app does not need each new build: the page and its data update inside the app (the **Data** button; the app
also checks when it opens). A new build matters for a first install and when the wrapper changes.

## What a build does

1. `site.sh` checks out the published site and sets the version from the clock (`2026.11.12`, Android version code
   `26111214`, so a later build always carries a larger number).
2. `bundle.py` makes the app's web folder `www/`: the page as `page.html` behind the start page `start.html` (which
   boots the newest page the device has: this one, or a newer one the Data button downloaded), every data file marked
   as already saved, no service worker. With `--models`, the offline AI's files go inside.
3. `npx cap add android` / `ios` generates the native project (never committed), and `android.sh` / `ios.sh` patch
   it: Electo's activity (`android-patches/MainActivity.java`: the page restarts instead of the app closing when
   Android kills it, Back closes pop-ups first, the system bars take the page's colours), the icon and opening screen
   (`icon/`, drawn by `icon/make.sh`), the version, and the permissions behind **Speak** (microphone) and **Use my
   location**. Both are asked for only when the reader uses them.
4. The app is opened in an Android emulator (`android_checks.sh`; Android 15, or the version `android_api` names
   in a run by hand) and an iPhone simulator (`ios_check.sh`), and `shot_check.py` reads the screenshot: the page's
   own mark must be at the top, on a page with text, with no title bar of Android's own over it. Only then is
   anything published. An emulator that fails to start or hangs gets one more try. The screenshot is kept on the
   [app-check release](https://github.com/ClockworkBlack/electo-data/releases/tag/app-check) either way.
5. `notes.py` writes the release's text (sizes, SHA-256, what was checked) and the files replace the last build's.

## Android signing

Android installs an update only over an app signed with the same key.

- **With the project's key** (four secrets on this repository, below) every build is signed with it, and a newer
  download installs over the last one.
- **Without it** each build is signed with a key made for that build alone and thrown away. The APK installs and
  works, but not over an earlier Electo: the earlier one has to be uninstalled first. The release says which it is
  ("Test signature").

The key is never in this repository, public or not: a published key would let anyone sign an "update" that Android
accepts over the real app. To make one (once, on any computer with Java):

    keytool -genkeypair -keystore electo.keystore -storetype PKCS12 -alias electo -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Electo"
    base64 -w0 electo.keystore        # macOS: base64 -i electo.keystore

and add, under Settings → Secrets and variables → Actions: `ANDROID_KEYSTORE_B64` (that base64 text),
`ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS` (`electo`) and `ANDROID_KEY_PASSWORD` (the same password for a
PKCS12 keystore). Keep a copy of the keystore file somewhere safe: GitHub does not give a secret back.

## The offline AI inside (`Electo-with-AI.apk`)

`models.py` gets the files, checked against their published hashes:

- **the model trained on Electo's data** from this repository's **app-models** release (`Electo-*.zip`, the
  Qwen team's Qwen2.5-1.5B trained further on the site's data, 4-bit for WebLLM). The private Electo repository's
  **copy-model-public** workflow puts the newest one there each morning when it changed (it needs the secret
  `PUBLIC_DATA_TOKEN` there: Contents read and write on this repository, Actions too to start the Android build);
- when that release has no model, the stock Qwen2.5-1.5B from Hugging Face instead (`models.json`, at a pinned
  commit);
- the dictation and voice models (Whisper tiny, Kokoro) from Hugging Face, pinned the same way, only the 8-bit files a
  phone loads.

`models-LICENSES.txt` travels inside the app as `models/LICENSES.txt`. The files are kept between builds (the
workflow's cache, keyed to what is on the app-models release).

## iPhone and iPad

The build makes the app, opens it in a simulator and publishes it unsigned. An iPhone installs only signed apps, so
the file is for a sideloading tool (which signs it with the user's own Apple ID) or for an Apple Developer account.
The offline AI there needs iOS 26 or newer (WebGPU) and downloads its model when turned on; no model is put inside
the iOS app.

With an Apple Developer account, four secrets make the workflow also sign the build and send it to TestFlight:
`APPLE_TEAM_ID`, `ASC_KEY_ID`, `ASC_ISSUER_ID` and `ASC_KEY_P8` (an App Store Connect API key with the Admin role;
the app `org.electo.app` has to exist in App Store Connect first). **That step has never been run**: there has been
no account to try it with.

**GitHub is short of Macs at times.** On the afternoon of Nov. 12, 2026 try after try found no Mac of either
kind, and [other projects report the same](https://github.com/orgs/community/discussions/211885) since Nov. 2,
one of them mostly in the European evening. A job that no Mac takes within a quarter of an hour is dropped before
any step runs. So the workflow tries up
to four times, the Intel kind and the Apple-chip kind taking turns, and its last job, `ios (how it ended)`, says
whether the app was built. GitHub marks a run failed as soon as one try was dropped, even when a later try built and
published the app, so a red run is not the answer: that last job is. When none of the four tries got a Mac, nothing
is wrong with the app and the last published build stays on the release. GitHub keeps the Intel Macs
[until the fall of 2027](https://github.blog/changelog/2025-09-19-github-actions-macos-13-runner-image-is-closing-down/);
after that the Apple-chip kind has to go first (the `mac` default in the workflow).

A second small workflow, **apps-catch-up**, looks at the two releases every morning (07:23 UTC, Mondays left to
the weekly build). When the iOS app is missing or more than three hours older than the Android app, and no build is
under way, it starts the apps workflow for iOS alone; otherwise it does nothing.

## By hand

    bash app/site.sh site                      # the published site into ./site
    python3 app/bundle.py site                 # app/www
    cd app && npm ci
    npx cap add android && bash android.sh && npx cap sync android && (cd android && ./gradlew assembleRelease)
    npx cap add ios && bash ios.sh && npx cap sync ios && npx cap open ios        # on a Mac

## Kept the same in two places

The private Electo repository has its own test build (`build-android` there: a debug APK with the trained model
inside, from that repository's copy of the site). `start.html` is the same file as its `tools/app_start.html`, and
`android-patches/MainActivity.java` the same as its `app/android-patches/MainActivity.java`; `bundle.py` follows its
`tools/app_bundle.sh`. A change to one belongs in the other.
