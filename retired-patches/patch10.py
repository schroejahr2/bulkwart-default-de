#!/usr/bin/env python3
"""Patch 10: Wiedergeoeffnete Entwuerfe verlieren ihre Anhaenge.

Bug: mail-app.tsx uebergibt beim Draft-Reopen (setPendingDraft) nur
Empfaenger/Betreff/Body - draft.attachments fehlt komplett. Der Composer
startet mit leerem Attachment-State; das naechste Speichern/Senden
ueberschreibt den Entwurf ohne Anhaenge (stiller Datenverlust).

Fix: attachments in ComposerDraftData aufnehmen, beim Reopen aus dem
vollen Draft uebergeben und im Composer als blobId-Attachments hydrieren
(gleiche Mechanik wie der bestehende Forward-Pfad; Save/Send uebernehmen
blobId-Eintraege bereits: filter att.blobId && !att.uploading).
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
check = '--check' in sys.argv

REPLACEMENTS = [
    # 1) ComposerDraftData um attachments erweitern
    (
        'components/email/email-composer.tsx',
        """  fromOverrideEnabled?: boolean;
}""",
        """  fromOverrideEnabled?: boolean;
  /** Existing server-side attachments of a re-opened draft (blobId refs). */
  attachments?: Array<{ blobId: string; name?: string; type?: string; size: number; cid?: string; disposition?: string }>;
}""",
    ),
    # 2) Attachment-State aus initialData hydrieren (vor dem Forward-Zweig)
    (
        'components/email/email-composer.tsx',
        """  const [attachments, setAttachments] = useState<ComposerAttachment[]>(() => {
    if (mode === 'forward' && replyTo?.attachments?.length) {""",
        """  const [attachments, setAttachments] = useState<ComposerAttachment[]>(() => {
    // Re-opened draft: restore its existing server-side attachments as
    // blobId entries (same shape the forward path below produces). Without
    // this the next save/send silently strips them from the draft. Inline
    // cid-referenced images stay out of the chip list - they live in the
    // body HTML, mirroring the forward filter.
    if (initialData?.attachments?.length) {
      const embeddedCids = collectInlineImageCids(body);
      return initialData.attachments
        .filter(att => !(att.cid && (
          embeddedCids.has(att.cid) ||
          (att.disposition === 'inline' && (att.type || '').startsWith('image/'))
        )))
        .map(att => ({
          name: att.name || 'attachment',
          type: att.type || 'application/octet-stream',
          size: att.size,
          blobId: att.blobId,
        }));
    }
    if (mode === 'forward' && replyTo?.attachments?.length) {""",
    ),
    # 3) Draft-Reopen: Anhaenge des vollen Drafts mitgeben
    (
        'components/mail/mail-app.tsx',
        """      mode: 'compose',
      draftId: draft.id,
    });""",
        """      mode: 'compose',
      draftId: draft.id,
      attachments: (draft.attachments ?? []).filter(a => !!a.blobId),
    });""",
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
