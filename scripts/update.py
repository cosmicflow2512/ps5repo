#!/usr/bin/env python3
"""Aktualisiert payloads.json und payloads/ aus den Upstream-Releases in sources.json."""
import hashlib, io, json, os, re, subprocess, sys, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAY = os.path.join(ROOT, "payloads")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
UA = {"User-Agent": "ps5repo-updater"}


def get(url, api=False):
    h = dict(UA)
    if api and TOKEN and "api.github.com" in url:
        h["Authorization"] = f"Bearer {TOKEN}"
        h["Accept"] = "application/vnd.github+json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120) as r:
        return r.read()


def releases(src):
    if src["type"] == "github":
        data = json.loads(get(f"https://api.github.com/repos/{src['repo']}/releases?per_page=30", api=True))
        return [{"tag": r["tag_name"], "pre": r["prerelease"], "draft": r["draft"], "date": r.get("published_at") or "",
                 "assets": [(a["name"], a["browser_download_url"]) for a in r["assets"]],
                 "page": r["html_url"]} for r in data]
    if src["type"] == "forgejo":
        data = json.loads(get(f"{src['host']}/api/v1/repos/{src['repo']}/releases?limit=30"))
        return [{"tag": r["tag_name"], "pre": r["prerelease"], "draft": r["draft"], "date": r.get("published_at") or "",
                 "assets": [(a["name"], a["browser_download_url"]) for a in r["assets"]],
                 "page": r["html_url"]} for r in data]
    raise ValueError(src["type"])


def pick(src, rels):
    inc = re.compile(src["tag_include"]) if src.get("tag_include") else None
    exc = re.compile(src["tag_exclude"]) if src.get("tag_exclude") else None
    asset = re.compile(src["asset"])
    cands = []
    for r in rels:
        if r["draft"] or (r["pre"] and not src.get("prerelease")):
            continue
        if inc and not inc.search(r["tag"]) or exc and exc.search(r["tag"]):
            continue
        hits = [a for a in r["assets"] if asset.search(a[0])]
        if hits:
            cands.append((r["date"], r, hits[0]))
    if not cands:
        return None
    cands.sort(key=lambda c: c[0], reverse=True)
    return cands[0][1], cands[0][2]


def safe(s):
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


def main():
    cfg = json.load(open(os.path.join(ROOT, "sources.json")))
    old_path = os.path.join(ROOT, "payloads.json")
    old = {p["id"]: p for p in json.load(open(old_path))["payloads"]} if os.path.exists(old_path) else {}
    out, changes, errors = [], [], []
    for src in cfg["sources"]:
        sid = src["id"]
        prev = old.get(sid)
        try:
            if src["type"] == "manual":
                fn, ver, page, date = src["file"], src["version"], src.get("source"), (prev or {}).get("last_update")
                data = open(os.path.join(PAY, fn), "rb").read()
            elif src["type"] == "build":
                st = json.load(open(os.path.join(ROOT, "build-state.json"))).get(sid)
                if not st or not os.path.exists(os.path.join(PAY, st["file"])):
                    raise RuntimeError("noch kein erfolgreicher Build")
                fn, ver, page, date = st["file"], st["version"], st["source"], st["date"]
                data = open(os.path.join(PAY, fn), "rb").read()
                if (prev or {}).get("version") != ver:
                    changes.append(f"{src['name']}: {(prev or {}).get('version', '-')} -> {ver}")
            else:
                res = pick(src, releases(src))
                if not res:
                    raise RuntimeError("kein passendes Release/Asset")
                rel, (aname, aurl) = res
                ver, page, date = rel["tag"], rel["page"], rel["date"][:10]
                fn = f"{safe(sid)}_{safe(ver)}.elf"
                fpath = os.path.join(PAY, fn)
                if prev and prev.get("version") == ver and os.path.exists(fpath):
                    data = open(fpath, "rb").read()
                else:
                    data = get(aurl)
                    if aname.lower().endswith(".zip"):
                        z = zipfile.ZipFile(io.BytesIO(data))
                        inner = [n for n in z.namelist() if re.search(src.get("zip_member", r"\.elf$"), n)]
                        data = z.read(inner[0])
                    if data[:4] != b"\x7fELF":
                        raise RuntimeError(f"{aname} ist keine ELF")
                    open(fpath, "wb").write(data)
                    changes.append(f"{src['name']}: {(prev or {}).get('version', '-')} -> {ver}")
            entry = {"id": sid, "name": src["name"], "filename": fn, "url": cfg["base_url"] + fn,
                     "version": ver, "category": src["category"], "author": src["author"],
                     "description": src["description"], "checksum": hashlib.sha256(data).hexdigest()}
            if page:
                entry["source"] = page
            if date:
                entry["last_update"] = date
            out.append(entry)
        except Exception as e:  # Quelle nicht erreichbar: letzten Stand behalten
            errors.append(f"{src['name']}: {e}")
            if prev and os.path.exists(os.path.join(PAY, prev["filename"])):
                out.append(prev)
    out.sort(key=lambda p: (p["category"], p["name"]))
    json.dump({"name": cfg["name"], "payloads": out}, open(old_path, "w"), indent=2, ensure_ascii=False)
    open(old_path, "a").write("\n")
    # Aufraeumen: behalten wird, was jetzt oder im letzten Stand referenziert ist
    keep = {p["filename"] for p in out} | {p["filename"] for p in old.values()}
    keep |= {s["file"] for s in cfg["sources"] if s["type"] == "manual"}
    for f in os.listdir(PAY):
        if f not in keep:
            os.remove(os.path.join(PAY, f))
            changes.append(f"entfernt: {f}")
    print("\n".join(["Aenderungen:"] + (changes or ["keine"]) + ["Fehler:"] + (errors or ["keine"])))
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        open(summ, "a").write("### Aenderungen\n" + "\n".join(f"- {c}" for c in changes or ["keine"]) +
                              "\n### Fehler\n" + "\n".join(f"- {e}" for e in errors or ["keine"]) + "\n")
    open(os.path.join(ROOT, ".update-msg"), "w").write("; ".join(changes) or "")


if __name__ == "__main__":
    main()
