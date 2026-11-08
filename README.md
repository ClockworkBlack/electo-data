# electo-data

**The Electo site:** https://clockworkblack.github.io/electo-data/

**Android app:** not published here yet. Once its signed build is (Electo's apk-public workflow, which needs the
PUBLIC_DATA_TOKEN secret), it will be at [the "android" release](https://github.com/ClockworkBlack/electo-data/releases/tag/android):
on the phone, open that link, download Electo.apk, open it and allow installs from this source when Android asks.

**The open AI model the crawler uses:** [Qwen3-8B, 4-bit GGUF](https://github.com/ClockworkBlack/electo-data/releases/tag/qwen3-8b)
(by the Qwen team, Apache License 2.0, unchanged from the official Qwen/Qwen3-8B-GGUF repository; about 5 GB in parts of
at most 1.9 GB: download every part and join them as HOW-TO-JOIN.txt says, then check SHA256SUMS). It writes the News
tab's marked summaries and sorts the positions on candidate profiles; everything it writes is checked against its
source before the site shows it. A model fine-tuned on that checked work will be added to the same page later.

Generated data files for the site and its Check for updates. `current.json` names the branch that holds the newest
complete build; the crawler replaces it after every import, and the Pages workflow deploys it. Public records only;
not for editing.
