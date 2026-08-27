# Ausgemusterte Patches

Diese Patches liefen bis Bulwark 1.8.1 im Build-Workflow und sind seit
**1.9.x upstream enthalten**. Sie werden hier aufbewahrt, falls Upstream
eine Aenderung zurueckdreht — nicht wieder einbauen, ohne vorher gegen den
aktuellen Upstream-Stand zu pruefen.

| Datei | Was es war | Upstream-Ersatz |
|---|---|---|
| `patch6.py`  | iOS-Auto-Zoom in Eingabefeldern | in 1.9.0 |
| `patch7.py`  | Unified-Reload: leere Liste nach Refresh | in 1.9.0 |
| `patch8.py`  | Konto-Scope fuer Email-IDs (Id-Kollision) | #847 — deckt mehr ab (Identitaetsvergleich + Stamp-Match statt bare-id, kein stiller Client-Fallback) |
| `patch9.py`  | Signatur bei wiedergeoeffneten Entwuerfen | in 1.9.0 |
| `patch10.py` | Anhaenge bei wiedergeoeffneten Entwuerfen | in 1.9.0 |
| `patch11.py` | Draft-Replace-Save ohne Datenverlust | in 1.9.0 |
| `patch13.py` | Einladungs-Banner kontoscharf parsen | in 1.9.0 |
| `patch14.py` | PDF-Vorschau: Bytes statt `blob:`-URL (CSP) | #871 — identische Loesung inkl. Begruendung im Code |
| `totp-toggle.step.yml` | Manuellen 2FA-Toggle auf der Login-Seite entfernen | Env-Var `LOGIN_SHOW_TOTP=false` (1.9.x) — in `.env.local` auf rg-storage gesetzt |

Aktiv bleiben im Workflow: Server-URL-Anzeige (Org-Trennung), Favicon-Route
(Absender-Domain direkt, DDG nur Fallback), Patch 5 (feste Kontofarben),
Patch 12 (PDF-Vorschau in installierten PWA-Fenstern).

## Korrektur 27.08.2026: Patch 12 gehoert NICHT hierher

Patch 12 war beim Aufraeumen als "ohnehin wirkungslos" mit ausgemustert worden.
Das war falsch. Richtig ist: Patch 12 *allein* war wirkungslos, solange die
eigene CSP den pdf.js-Pfad blockierte (das loeste erst Patch 14 / upstream #871).
Seit #871 upstream ist, ist Patch 12 der einzige, der den Pfad ueberhaupt
aktiviert: Upstream schaltet nur bei iOS und bei `pdfViewerEnabled === false`
auf pdf.js um; ein installiertes PWA-Fenster meldet aber weiterhin `true`,
waehrend Chromium dort keinen PDF-Viewer bereitstellt -> leeres `<iframe>`.
Patch 12 ergaenzt die `display-mode`-Erkennung und ist damit wieder im Workflow.
