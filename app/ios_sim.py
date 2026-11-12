#!/usr/bin/env python3
"""Which iPhone simulator to open the app in: the newest iOS this Xcode builds for, a plain iPhone before a Pro.

    xcrun simctl list devices available -j | python3 app/ios_sim.py <iphonesimulator SDK version>

Prints "<simulator id> <name> (iOS <version>)"."""
import json
import sys


def pick(devices, sdk):
    best = None
    for runtime, devs in devices.items():
        if "iOS" not in runtime:
            continue
        ver = tuple(int(x) for x in runtime.rsplit("iOS-", 1)[-1].split("-") if x.isdigit())
        if ver[:2] > sdk:          # a newer iOS than this Xcode builds for
            continue
        for x in devs:
            if x.get("isAvailable", True) and x["name"].startswith("iPhone") and "SE" not in x["name"]:
                key = (ver, "Pro" not in x["name"], "Plus" not in x["name"] and "Max" not in x["name"], x["name"])
                if best is None or key > best[0]:
                    best = (key, x["udid"], x["name"], ".".join(map(str, ver)))
    return best


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    b = pick(json.load(sys.stdin)["devices"], tuple(int(x) for x in sys.argv[1].split(".")[:2]))
    if not b:
        sys.exit("no iPhone simulator for iOS %s or older on this Mac" % sys.argv[1])
    print("%s %s (iOS %s)" % (b[1], b[2], b[3]))
