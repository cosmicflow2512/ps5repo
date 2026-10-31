# ps5repo – PS5 Payload Manager Quelle

Eigene Quelle für den [PS5 Payload Manager](https://github.com/itsPLK/ps5-payload-manager) (itsPLK).
Die Payloads werden automatisch aus den offiziellen Upstream-Releases aktualisiert.

In pldmgr hinzufügen (Settings → Manage Sources → Add Source):

```
https://raw.githubusercontent.com/cosmicflow2512/ps5repo/main/payloads.json
```

## Wie es funktioniert

- `sources.json` legt fest, welche Payloads drin sind und woher sie kommen (GitHub- oder Forgejo-Releases, Asset-Muster, Pre-Releases ja/nein).
- `scripts/update.py` holt das neueste passende Release, prüft den ELF-Header, legt die Datei unter `payloads/` ab und schreibt `payloads.json` mit SHA-256.
- `scripts/build_main.sh` baut Quellen vom Typ `build` aus dem Upstream-Branch mit dem ps5-payload-sdk, sobald sich der Commit ändert (Stand in `build-state.json`).
- `.github/workflows/update.yml` läuft alle 6 Stunden, bei Änderungen an `sources.json` und manuell (Actions → „Payloads aktualisieren“ → Run workflow).
- Ist eine Quelle nicht erreichbar, bleibt der letzte Stand erhalten. Die Vorversion einer Datei bleibt einen Lauf lang liegen, damit gecachte JSONs nicht ins Leere zeigen.

## Payload hinzufügen

Eintrag in `sources.json` ergänzen und committen, der Workflow läuft dann automatisch.
`"type": "manual"` für Dateien ohne Upstream-Release: Datei nach `payloads/` legen, `file` und `version` setzen.

## Enthaltene Payloads

| Payload | Quelle |
|---|---|
| ftpsrv | [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv) |
| ftpsrv (drakmor) | [drakmor/ftpsrv](https://github.com/drakmor/ftpsrv) (nur `*-ng-stable`) |
| ps5-web-file-manager | [owendswang/ps5-web-file-manager](https://github.com/owendswang/ps5-web-file-manager) |
| ShadowMountPlus | [drakmor/ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus) |
| nanoDNS | [drakmor/nanoDNS](https://github.com/drakmor/nanoDNS) |
| garlic-savemgr | [earthonion/garlic-savemgr](https://git.etawen.dev/earthonion/garlic-savemgr) (Forgejo) |
| Webkit-Autoloader-Installer | [itsPLK/ps5-webkit-autoloader](https://github.com/itsPLK/ps5-webkit-autoloader) |
| Pkg Manager | [itsPLK/ps5-pkg-manager](https://github.com/itsPLK/ps5-pkg-manager) |
| PS5 Linux Loader (offiziell) | [ps5-linux/ps5-linux-loader](https://github.com/ps5-linux/ps5-linux-loader) |
| PS5 Linux Loader (offiziell, main) | Build aus [ps5-linux/ps5-linux-loader](https://github.com/ps5-linux/ps5-linux-loader) main, bei jedem neuen Commit |
| PS5 Linux Loader (rmuxwashere) | [rmuxwashere/ps5-linux-loader](https://github.com/rmuxwashere/ps5-linux-loader) |
| PS5 Linux Loader (SonicIso) | [soniciso1/ps5-linux-loader](https://github.com/soniciso1/ps5-linux-loader) |
| Kstuff 1.13 Fpkg Dr Test | manuell (Test-Build drakmor) |
| BlueV | [0xZ3n0x/BlueV](https://github.com/0xZ3n0x/BlueV) |
| ghost-toothAPI | manuell (Forum-Release StonedModder) |

Rechte und Credits liegen bei den jeweiligen Autoren.
