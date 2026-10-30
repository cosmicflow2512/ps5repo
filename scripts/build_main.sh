#!/bin/bash
# Baut Quellen vom Typ "build" (sources.json) aus dem aktuellen Upstream-Branch,
# wenn sich der Commit geaendert hat. Ergebnis: payloads/<id>_main-<datum>-<sha>.elf + build-state.json
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$ROOT/build-state.json"; [ -f "$STATE" ] || echo '{}' > "$STATE"
SDK="${PS5_PAYLOAD_SDK:-/opt/ps5-payload-sdk}"
python3 - "$ROOT" <<'PY' > /tmp/build-list.txt
import json,sys
for s in json.load(open(sys.argv[1]+"/sources.json"))["sources"]:
    if s["type"]=="build": print(s["id"], s["repo"], s.get("branch","main"), s["output"])
PY
while read -r ID REPO BRANCH OUT; do
  SHA=$(git ls-remote "https://github.com/$REPO.git" "refs/heads/$BRANCH" | cut -f1)
  [ -n "$SHA" ] || { echo "::warning::$ID: Branch $BRANCH nicht gefunden"; continue; }
  OLD=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],{}).get('sha',''))" "$STATE" "$ID")
  if [ "$OLD" = "$SHA" ]; then echo "$ID: unveraendert ($SHA)"; continue; fi
  W=$(mktemp -d)
  git clone -q --depth 1 -b "$BRANCH" "https://github.com/$REPO.git" "$W/src"
  if ! PS5_PAYLOAD_SDK="$SDK" make -C "$W/src" -j"$(nproc)" > "$W/build.log" 2>&1; then
    echo "::warning::$ID: Build fehlgeschlagen"; tail -40 "$W/build.log"; continue
  fi
  [ "$(head -c4 "$W/src/$OUT" | od -An -c | tr -d ' ')" = "177ELF" ] || { echo "::warning::$ID: keine ELF"; continue; }
  DATE=$(git -C "$W/src" log -1 --format=%cs); SHORT=${SHA:0:7}
  VER="main-${DATE//-/}-$SHORT"; FN="${ID}_${VER}.elf"
  cp "$W/src/$OUT" "$ROOT/payloads/$FN"
  python3 - "$STATE" "$ID" "$SHA" "$VER" "$FN" "$DATE" "$REPO" <<'PY'
import json,sys
p,i,sha,ver,fn,date,repo=sys.argv[1:]
d=json.load(open(p)); d[i]={"sha":sha,"version":ver,"file":fn,"date":date,"source":f"https://github.com/{repo}/commit/{sha}"}
json.dump(d,open(p,"w"),indent=2); open(p,"a").write("\n")
PY
  echo "$ID: gebaut $VER"
done < /tmp/build-list.txt
