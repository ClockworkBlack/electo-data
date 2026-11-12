# electo-data

**The Electo site:** https://clockworkblack.github.io/electo-data/

**The Electo app** is built here from the site ([how](app/README.md)):

- **Android:** [the "android" release](https://github.com/ClockworkBlack/electo-data/releases/tag/android). On the
  phone, open that link, download **Electo.apk**, open it and allow installs from this source when Android asks.
  **Electo-with-AI.apk** is the same app with the offline AI's model inside (much larger; nothing else to download).
- **iPhone and iPad:** [the "ios" release](https://github.com/ClockworkBlack/electo-data/releases/tag/ios) has an
  unsigned build. An iPhone does not install it as it is; the release says what it takes. Without that, the site
  works as an app: open it in Safari, then Share → Add to Home Screen.

**The open AI model the crawler uses:** [Qwen3-8B, 4-bit GGUF](https://github.com/ClockworkBlack/electo-data/releases/tag/qwen3-8b)
(by the Qwen team, Apache License 2.0, unchanged from the official Qwen/Qwen3-8B-GGUF repository; about 5 GB in parts of
at most 1.9 GB: download every part and join them as HOW-TO-JOIN.txt says, then check SHA256SUMS). It writes the News
tab's marked summaries and sorts the positions on candidate profiles; everything it writes is checked against its
source before the site shows it. A model fine-tuned on that checked work will be added to the same page later.

Generated data files for the site and its Check for updates. `current.json` names the branch that holds the newest
complete build; the crawler replaces it after every import, and the Pages workflow deploys it. Public records only;
not for editing.
