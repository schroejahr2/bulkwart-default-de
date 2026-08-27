#!/usr/bin/env python3
"""Patch 14: PDF-Vorschau bleibt leer, weil die CSP den Blob-Abruf blockiert.

Beobachtet in der macOS-Safari-Web-App: statt der Seiten erscheint der
Fehler-Zustand von PdfMobileViewer ("In neuem Tab oeffnen").

Ursache: pdf.js bekommt nur die blob:-URL und holt das Dokument daraus per
fetch. Die CSP der App erlaubt blob: bei img-/frame-/object-/media-src, aber
connect-src steht auf "'self' https:" - der Abruf wird also blockiert und
getDocument wirft. In Chromium faellt das nie auf, weil dort der
<iframe>-Zweig laeuft und frame-src blob: erlaubt.

Fix: Das Modal hat den Blob laengst im Speicher (getFileContent). Statt einer
URL werden die Bytes durchgereicht - getDocument({data}) laedt nichts nach,
damit ist die CSP nicht mehr beteiligt. Die blob:-URL bleibt fuer den
"In neuem Tab oeffnen"-Fallback erhalten.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
check = '--check' in sys.argv

REPLACEMENTS = [
    # --- pdf-mobile-viewer: Bytes akzeptieren -----------------------------
    (
        'components/files/pdf-mobile-viewer.tsx',
        """export function PdfMobileViewer({ url }: { url: string }) {""",
        """// Patched (bulkwart-default-de): `data` carries the already-fetched bytes.
// Loading from the blob: URL instead goes through fetch, which our CSP blocks
// (connect-src lacks blob:) - the viewer then only ever showed its error state.
export function PdfMobileViewer({ url, data }: { url: string; data?: Uint8Array | null }) {""",
    ),
    (
        'components/files/pdf-mobile-viewer.tsx',
        """        loadingTask = pdfjs.getDocument({ url });""",
        """        // Copy the buffer: pdf.js transfers ownership, so a re-run of this
        // effect would otherwise hand it a detached array.
        loadingTask = pdfjs.getDocument(
          data ? { data: new Uint8Array(data) } : { url },
        );""",
    ),
    (
        'components/files/pdf-mobile-viewer.tsx',
        """      void loadingTask?.destroy().catch(() => {});
    };
  }, [url]);""",
        """      void loadingTask?.destroy().catch(() => {});
    };
  }, [url, data]);""",
    ),
    # --- file-preview-modal: Bytes behalten und durchreichen ---------------
    (
        'components/files/file-preview-modal.tsx',
        """  const [emlContent, setEmlContent] = useState<ParsedEml | null>(null);""",
        """  const [emlContent, setEmlContent] = useState<ParsedEml | null>(null);
  // Raw PDF bytes for the pdf.js path - see PdfMobileViewer.
  const [pdfBytes, setPdfBytes] = useState<Uint8Array | null>(null);""",
    ),
    (
        'components/files/file-preview-modal.tsx',
        """    setLoading(true);
    setError(false);
    setResolvedFileType(getFilePreviewKind(name));""",
        """    setLoading(true);
    setError(false);
    setPdfBytes(null);
    setResolvedFileType(getFilePreviewKind(name));""",
    ),
    (
        'components/files/file-preview-modal.tsx',
        """          revokeUrl = URL.createObjectURL(typedBlob);
          if (!cancelled) {
            setObjectUrl(revokeUrl);
            setCanOpenInNewTab(isMimeTypeSafeForInlinePreview(effectiveType));
          }""",
        """          revokeUrl = URL.createObjectURL(typedBlob);
          if (!cancelled) {
            setObjectUrl(revokeUrl);
            setCanOpenInNewTab(isMimeTypeSafeForInlinePreview(effectiveType));
          }
          if (previewType === "pdf") {
            // Hand pdf.js the bytes directly; fetching the blob: URL back is
            // what the CSP blocks.
            const bytes = new Uint8Array(await typedBlob.arrayBuffer());
            if (!cancelled) setPdfBytes(bytes);
          }""",
    ),
    (
        'components/files/file-preview-modal.tsx',
        """            <PdfMobileViewer url={objectUrl} />""",
        """            <PdfMobileViewer url={objectUrl} data={pdfBytes} />""",
    ),
]

for rel, old, new in REPLACEMENTS:
    p = root / rel
    src = p.read_text()
    n = src.count(old)
    assert n == 1, f"{rel}: Anker {n}x statt 1x: {old[:60]!r}"
    if check:
        print(f"ok  {rel}: 1x {old.splitlines()[0].strip()[:60]}")
    else:
        p.write_text(src.replace(old, new))
        print(f"patched  {rel}")

if check:
    print("--check: alle Anker eindeutig, nichts geschrieben.")
