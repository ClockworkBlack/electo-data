#!/usr/bin/env python3
"""The app's web folder (app/www) from a checkout of the public site.

    python3 app/bundle.py <site dir> [--models <dir>] [--out <dir>]

<site dir> is the branch main's current.json names: the whole public site (the page, its data, the offline AI's
library and kernels). Without --models the app carries no model; the page downloads one when the reader turns the
offline AI on, as the website does. With --models <dir> (one folder per model as WebLLM reads it, plus speech/ for the
dictation and voice models) those travel inside the app and nothing is downloaded.

The same steps as tools/app_bundle.sh in the Electo repository, which builds from that repository's own copy."""
import argparse
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SPEECH = ("onnx-community/whisper-tiny.en", "onnx-community/whisper-tiny", "onnx-community/Kokoro-82M-v1.0-ONNX")
SW = """/* Electo app: no service worker. One registered by an older build replaces itself with this, which clears what it kept and unregisters. */
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil((async()=>{for(const k of await caches.keys())if(k.startsWith('electo-'))await caches.delete(k); await self.registration.unregister(); for(const c of await self.clients.matchAll({type:'window'}))try{c.navigate(c.url)}catch(x){}})()));
"""


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site")
    ap.add_argument("--models", default="")
    ap.add_argument("--out", default=os.path.join(HERE, "www"))
    a = ap.parse_args(argv)
    site, models, out = a.site, a.models, a.out
    for need in ("index.html", "offline.json", "vendor/ai-manifest.json"):
        if not os.path.isfile(os.path.join(site, need)):
            sys.exit("not a build of the site (no %s): %s" % (need, site))
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(site, out, ignore=shutil.ignore_patterns(".git"))
    for extra in ("README.md", ".nojekyll", "updates.json"):       # the branch's own notes and the feed's list, not the page's
        p = os.path.join(out, extra)
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(os.path.join(out, "models"), ignore_errors=True)

    # the offline AI's weights, when they travel inside the app
    ids = []
    if models:
        if not os.path.isdir(models):
            sys.exit("no models folder at " + models)
        for name in sorted(os.listdir(models)):
            src = os.path.join(models, name)
            if not os.path.isdir(src):
                if name == "LICENSES.txt":         # the models' notices travel with them
                    os.makedirs(os.path.join(out, "models"), exist_ok=True)
                    shutil.copy(src, os.path.join(out, "models", name))
                continue
            dst = os.path.join(out, "models", name)
            shutil.copytree(src, dst)
            if name == "speech":
                continue
            ids.append(name)
            mark = os.path.join(dst, ".electo-model.json")
            if os.path.exists(mark):
                os.remove(mark)
            # WebLLM 0.2.80+ reads tensor-cache.json; older packs only have ndarray-cache.json (same format)
            if not os.path.exists(os.path.join(dst, "tensor-cache.json")) and os.path.exists(os.path.join(dst, "ndarray-cache.json")):
                shutil.copy(os.path.join(dst, "ndarray-cache.json"), os.path.join(dst, "tensor-cache.json"))
            if not os.path.exists(os.path.join(dst, "mlc-chat-config.json")):
                sys.exit("not a model as WebLLM reads it (no mlc-chat-config.json): " + src)

    # the app's manifest lists only what is inside it: stock models under models, trained ones under custom, all under bundled
    mp = os.path.join(out, "vendor", "ai-manifest.json")
    m = json.load(open(mp, encoding="utf-8"))
    m["models"] = {i: "models/" + i + "/" for i in ids if not i.startswith("Electo-")}
    m["custom"] = [c for c in m.get("custom", []) if c.get("model_id") in ids]
    missing = [i for i in ids if i.startswith("Electo-") and i not in {c["model_id"] for c in m["custom"]}]
    if missing:
        sys.exit("the site's vendor/ai-manifest.json does not list (custom): " + ", ".join(missing))
    m["bundled"] = ids
    speech = os.path.join(out, "models", "speech")
    if m.get("speech"):
        here = {d: "models/speech/" + d + "/" for d in SPEECH if os.path.isdir(os.path.join(speech, d))}
        if here:
            m["speech"]["models"] = here
        else:
            m["speech"].pop("models", None)          # not inside: the page takes them from the internet when asked
    json.dump(m, open(mp, "w", encoding="utf-8"), indent=1)

    # the app has every data file itself: the site's data is marked as already saved for offline use
    man = json.load(open(os.path.join(out, "offline.json"), encoding="utf-8"))
    json.dump({"files": {f["p"]: f["h"] for f in man["files"]}, "at": int(time.time() * 1000), "v": man["v"],
               "n": len(man["files"]), "bytes": man["bytes"], "bundled": True},
              open(os.path.join(out, "offline-meta.json"), "w", encoding="utf-8"))

    # the page knows it is the app before any of its scripts run; the app opens on the start page, which boots the
    # newest page the device has (this one, or a newer one "Refresh data" took from the public feed)
    ip = os.path.join(out, "index.html")
    t = open(ip, encoding="utf-8").read()
    flag = "<script>window.ELECTO_APP=1;window.ELECTO_APP_AI=%d</script>" % (1 if ids else 0)
    i = t.index("<head>") + len("<head>")
    open(os.path.join(out, "page.html"), "w", encoding="utf-8").write(t[:i] + flag + t[i:])
    start = open(os.path.join(HERE, "start.html"), encoding="utf-8").read()
    one = "window.ELECTO_APP_AI = 1;"
    if start.count(one) != 1:
        sys.exit("start.html: expected one line setting window.ELECTO_APP_AI")
    open(ip, "w", encoding="utf-8").write(start if ids else start.replace(one, "window.ELECTO_APP_AI = 0;"))

    # a service worker an older build registered removes itself (and what it kept) the next time it checks for updates
    open(os.path.join(out, "sw.js"), "w", encoding="utf-8").write(SW)

    n = size = 0
    for root, _, names in os.walk(out):
        for f in names:
            n += 1
            size += os.path.getsize(os.path.join(root, f))
    print("app web folder: %d files, %.0f MB; site built %s; offline AI inside: %s%s" % (
        n, size / 1e6, man.get("built", "?"), ", ".join(ids) or "none (downloads when asked for)",
        "; speech models inside" if os.path.isdir(speech) else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
