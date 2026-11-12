#!/usr/bin/env python3
"""The offline AI's files for the app that carries them inside (Electo-with-AI.apk), into a folder bundle.py takes.

    python3 app/models.py <site dir> <out dir>
    python3 app/models.py --key            a short name for exactly these files, for keeping them between builds

Where they come from, in this order:
  1. This repository's "app-models" release, when it exists: a pack made for the app (a model trained on Electo's
     data as Electo-*.zip, speech-phone.tar, LICENSES.txt). Nothing is on it until the owner puts one there.
  2. Otherwise the public originals on Hugging Face, as app/models.json names them: the stock model phones run
     (its repository is read from the site's own vendor/ai-manifest.json) and the speech models, only the 8-bit files
     a phone loads. Every file is checked against the hash Hugging Face lists for it. Each "rev" in models.json is
     a commit there; "main" takes the newest and prints its commit so it can be pinned.

Leaves <out dir>/<model id>/..., <out dir>/speech/<owner>/<name>/..., LICENSES.txt and models-used.json."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("GITHUB_REPOSITORY", "ClockworkBlack/electo-data")
HF = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
UA = {"User-Agent": "electo-app-build (+https://github.com/%s)" % REPO}
# a phone runs speech on the CPU with the 8-bit graphs (the page asks for dtype q8 there): Whisper's encoder and merged
# decoder, Kokoro's model; the full-precision and the unmerged graphs are never loaded in the app
ONNX_KEEP = ("encoder_model_quantized.onnx", "decoder_model_merged_quantized.onnx", "model_quantized.onnx")


def get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (i + 1))
    raise SystemExit("could not read %s: %s" % (url, last))


def download(url, dest, want_sha256=None, want_git=None, tries=4):
    """Fetch url into dest; want_sha256 (a large file's hash) or want_git (a small file's git blob hash) must match."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last = None
    for i in range(tries):
        try:
            n = 0
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(dest + ".part", "wb") as f:
                if want_git:                       # small files only: read whole
                    body = r.read()
                    f.write(body)
                    n = len(body)
                    got = hashlib.sha1(b"blob %d\0" % n + body).hexdigest()
                    if got != want_git:
                        raise ValueError("git hash %s, expected %s" % (got, want_git))
                else:
                    h = hashlib.sha256()
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            break
                        h.update(b)
                        f.write(b)
                        n += len(b)
                    if want_sha256 and h.hexdigest() != want_sha256:
                        raise ValueError("SHA-256 %s, expected %s" % (h.hexdigest(), want_sha256))
            os.replace(dest + ".part", dest)
            return n
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (i + 1))
    raise SystemExit("could not fetch %s: %s" % (url, last))


def hf_repo(repo, rev, dest, keep):
    """Every file of a Hugging Face model repository that keep(path) wants, checked; returns (commit, files, bytes)."""
    info = json.loads(get("%s/api/models/%s/revision/%s" % (HF, repo, rev)))
    sha = info.get("sha") or rev
    tree = json.loads(get("%s/api/models/%s/tree/%s?recursive=true" % (HF, repo, sha)))
    n = size = 0
    for x in tree:
        if x.get("type") != "file" or not keep(x["path"]):
            continue
        lfs = x.get("lfs") or {}
        size += download("%s/%s/resolve/%s/%s" % (HF, repo, sha, x["path"]), os.path.join(dest, x["path"]),
                         want_sha256=lfs.get("oid"), want_git=None if lfs else x.get("oid"))
        n += 1
    if not n:
        raise SystemExit("nothing to take from %s at %s" % (repo, sha))
    print("  %s at %s: %d files, %.0f MB, each checked against its hash" % (repo, sha[:12], n, size / 1e6))
    return sha, n, size


def from_release(out):
    """The pack on this repository's app-models release, when there is one."""
    try:
        rel = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://api.github.com/repos/%s/releases/tags/app-models" % REPO,
            headers=dict(UA, **({"Authorization": "Bearer " + os.environ["GH_TOKEN"]} if os.environ.get("GH_TOKEN") else {}))), timeout=60).read())
    except Exception:  # noqa: BLE001
        return None
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    zips = [n for n in assets if n.endswith(".zip")]
    if not zips:
        return None
    used = {"from": "the app-models release of " + REPO, "files": sorted(assets)}
    tmp = out + ".dl"
    os.makedirs(tmp, exist_ok=True)
    for name, url in sorted(assets.items()):
        p = os.path.join(tmp, name)
        download(url, p)
        if name.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                z.extractall(out)
        elif name.endswith(".tar"):
            with tarfile.open(p) as t:
                try:
                    t.extractall(out, filter="data")
                except TypeError:                  # a Python before the filter existed
                    t.extractall(out)
        elif name == "LICENSES.txt":
            shutil.copy(p, os.path.join(out, name))
        os.remove(p)
    shutil.rmtree(tmp, ignore_errors=True)
    return used


def from_hugging_face(site, out):
    cfg = json.load(open(os.path.join(HERE, "models.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(site, "vendor", "ai-manifest.json"), encoding="utf-8"))
    mid = cfg["model"]["id"]
    entry = next((m for m in man.get("model_list", []) if m.get("model_id") == mid), None)
    if not entry or mid not in (man.get("models") or {}):
        raise SystemExit("the site's vendor/ai-manifest.json does not list %s (the page would not use it)" % mid)
    repo = re.sub(r"^https?://huggingface\.co/", "", entry["model"]).strip("/")
    used = {"from": "Hugging Face", "model": {}, "speech": {}}
    sha, n, size = hf_repo(repo, cfg["model"].get("rev", "main"), os.path.join(out, mid), lambda p: not p.startswith(".git"))
    used["model"] = {"id": mid, "repo": repo, "rev": sha, "files": n, "bytes": size}
    for s in cfg["speech"]:
        keep = lambda p: not p.startswith(".git") and (not p.endswith(".onnx") or os.path.basename(p) in ONNX_KEEP)  # noqa: E731
        sha, n, size = hf_repo(s["repo"], s.get("rev", "main"), os.path.join(out, "speech", s["repo"]), keep)
        used["speech"][s["repo"]] = {"rev": sha, "files": n, "bytes": size}
    shutil.copy(os.path.join(HERE, "models-LICENSES.txt"), os.path.join(out, "LICENSES.txt"))
    return used


def key():
    """A short name for exactly these files (the workflow keeps them between builds under it): the pack on the
    app-models release as it is now, or else models.json."""
    h = hashlib.sha256(open(os.path.join(HERE, "models.json"), "rb").read())
    try:
        rel = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://api.github.com/repos/%s/releases/tags/app-models" % REPO,
            headers=dict(UA, **({"Authorization": "Bearer " + os.environ["GH_TOKEN"]} if os.environ.get("GH_TOKEN") else {}))), timeout=60).read())
        h.update(json.dumps(sorted((a["name"], a["updated_at"], a["size"]) for a in rel.get("assets", []))).encode())
    except Exception:  # noqa: BLE001
        pass
    return h.hexdigest()[:16]


def main(argv):
    if argv == ["--key"]:
        print(key())
        return
    if len(argv) != 2:
        sys.exit(__doc__)
    site, out = argv
    stamp = os.path.join(out, "models-used.json")
    if os.path.exists(stamp):                      # kept from an earlier build (the workflow's cache)
        print("the offline AI's files are here already: " + json.dumps(json.load(open(stamp)))[:300])
        return
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    used = from_release(out)
    if used:
        print("the offline AI's files: the pack on the app-models release (%s)" % ", ".join(used["files"]))
    else:
        print("the offline AI's files: the public originals on Hugging Face (no pack on the app-models release)")
        used = from_hugging_face(site, out)
    json.dump(used, open(stamp, "w", encoding="utf-8"), indent=1)
    total = int(subprocess.run(["du", "-sk", out], capture_output=True, text=True).stdout.split()[0]) / 1000
    print("in %s: %s, %.0f MB" % (out, ", ".join(sorted(d for d in os.listdir(out) if os.path.isdir(os.path.join(out, d)))), total))


if __name__ == "__main__":
    main(sys.argv[1:])
