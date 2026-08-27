#!/usr/bin/env python3
"""Patch 12: PDF-Vorschau in der installierten PWA ist weiss.

Chromium stellt den eingebauten PDF-Viewer in Standalone-App-Fenstern
(installierte PWA) nicht bereit - ein <iframe> mit blob:-PDF bleibt dort
leer. navigator.pdfViewerEnabled spiegelt aber nur die Browser-Einstellung
und meldet auch im PWA-Fenster true, deshalb greift Bulwarks Detection nicht
(fuer iOS/Android nutzen sie laengst den pdf.js-Canvas-Pfad, der
Desktop-Standalone-Fall fehlt).

Fix: display-mode standalone/minimal-ui/window-controls-overlay (plus iOS
navigator.standalone) => pdf.js-Viewer statt iframe.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
check = '--check' in sys.argv

REPLACEMENTS = [
    (
        'components/files/file-preview-modal.tsx',
        """  useEffect(() => {
    const nav = navigator as Navigator & { pdfViewerEnabled?: boolean };
    const isIOS =
      /iPad|iPhone|iPod/.test(nav.userAgent) ||
      (nav.maxTouchPoints > 1 && /Macintosh/.test(nav.userAgent));
    if (isIOS) {
      setPdfInlineSupported(false);
    } else if (typeof nav.pdfViewerEnabled === "boolean") {
      setPdfInlineSupported(nav.pdfViewerEnabled);
    }
  }, []);""",
        """  useEffect(() => {
    const nav = navigator as Navigator & { pdfViewerEnabled?: boolean; standalone?: boolean };
    const isIOS =
      /iPad|iPhone|iPod/.test(nav.userAgent) ||
      (nav.maxTouchPoints > 1 && /Macintosh/.test(nav.userAgent));
    // Patched (bulkwart-default-de): installed PWA windows (standalone /
    // minimal-ui / window-controls-overlay) don't get Chromium's built-in
    // PDF viewer - the <iframe> stays blank - while pdfViewerEnabled still
    // reports the browser-level setting (true). Route them to pdf.js like
    // the mobile browsers.
    const isStandalonePwa =
      nav.standalone === true ||
      ["standalone", "minimal-ui", "window-controls-overlay"].some(
        (m) => window.matchMedia?.(`(display-mode: ${m})`).matches
      );
    if (isIOS || isStandalonePwa) {
      setPdfInlineSupported(false);
    } else if (typeof nav.pdfViewerEnabled === "boolean") {
      setPdfInlineSupported(nav.pdfViewerEnabled);
    }
  }, []);""",
    ),
]

for rel, old, new in REPLACEMENTS:
    p = root / rel
    src = p.read_text()
    n = src.count(old)
    assert n == 1, f"{rel}: Anker {n}x statt 1x gefunden: {old[:60]!r}"
    if check:
        print(f"ok  {rel}: 1x {old.splitlines()[0][:60]}")
    else:
        p.write_text(src.replace(old, new))
        print(f"patched  {rel}")

if check:
    print("--check: alle Anker eindeutig, nichts geschrieben.")
