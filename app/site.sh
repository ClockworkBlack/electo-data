#!/bin/bash
# The site as published, for an app build: a checkout of the branch main's current.json names, into <folder>, and
# this build's version from the clock (a later build always carries a larger number). Inside GitHub Actions the
# values also go to the job's environment: SITE_BRANCH, SITE_BUILT, SITE_COMMIT, APP_VERSION_CODE, APP_VERSION_NAME,
# APP_BUILD.
#   bash app/site.sh [folder]        (default: site)
set -e
DEST="${1:-site}"
REPO="${GITHUB_REPOSITORY:-ClockworkBlack/electo-data}"; URL="https://github.com/$REPO"
ok=""
for try in 1 2 3 4; do
  # read the pointer fresh each time: the crawler replaces the branch several times an hour and deletes old ones
  CUR=$(git ls-remote "$URL" refs/heads/main | cut -f1)
  [ -n "$CUR" ] || { sleep 10; continue; }
  rm -rf "$DEST.ptr"; mkdir -p "$DEST.ptr"
  ( cd "$DEST.ptr" && git init -q && git fetch -q --depth 1 "$URL" "$CUR" && git show FETCH_HEAD:current.json > current.json )
  BR=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['branch'])" "$DEST.ptr/current.json")
  rm -rf "$DEST"
  if git clone -q --depth 1 --branch "$BR" "$URL" "$DEST" 2>/dev/null && [ -f "$DEST/index.html" ] && [ -f "$DEST/offline.json" ]; then ok=1; break; fi
  echo "branch $BR was not there (replaced by a newer build?); reading the pointer again"; sleep 15
done
rm -rf "$DEST.ptr"
[ -n "$ok" ] || { echo "could not get the published site"; exit 1; }
rm -rf "$DEST/.git"
BUILT=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('built',''))" "$DEST/offline.json")
COMMIT=$(python3 -c "import json,sys,os; p=sys.argv[1]; print(json.load(open(p)).get('commit','') if os.path.exists(p) else '')" "$DEST/updates.json")
CODE=$(date -u +%y%m%d%H); NAME=$(date -u +%Y.%-m.%-d); BUILD=$(date -u +%Y%m%d%H%M)
echo "the site: branch $BR, built $BUILT ($(find "$DEST" -type f | wc -l | tr -d ' ') files); app version $NAME ($CODE)"
if [ -n "${GITHUB_ENV:-}" ]; then
  { echo "SITE_BRANCH=$BR"; echo "SITE_BUILT=$BUILT"; echo "SITE_COMMIT=$COMMIT"; echo "APP_VERSION_CODE=$CODE"; echo "APP_VERSION_NAME=$NAME"; echo "APP_BUILD=$BUILD"; } >> "$GITHUB_ENV"
fi
