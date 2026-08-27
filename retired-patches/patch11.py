#!/usr/bin/env python3
"""Patch 11: Draft-Replace-Save zerstoert Entwuerfe mit hydrierten Anhaengen.

Hergang (live auf 1.8.1+Patch10 beobachtet, Console-Beweis "blobId ... does
not exist on this server"):
- Patch 10 hydriert beim Draft-Reopen die Anhaenge mit den PART-BlobIds der
  bestehenden Draft-Version (nicht mit stabilen Upload-Blobs).
- createDraft() ersetzt den Draft per EINEM Email/set mit create+destroy.
  Save 1 geht gut (create sieht die Blobs noch, destroy toetet danach die
  Quellversion samt Part-Blobs) - der Composer behaelt aber die toten IDs.
- Save 2: create scheitert (blobNotFound), der destroy der letzten guten
  Version laeuft im selben Call TROTZDEM durch -> Entwurf weg, roter Banner.

Fix A (lib/jmap/client.ts): destroy erst NACH erfolgreichem create als
zweiter Call. Schlimmster Fall ist jetzt ein verwaister Alt-Draft statt
Datenverlust.

Fix B (email-composer.tsx): nach jedem erfolgreichen Save die Anhang-BlobIds
gegen die neu erstellte Draft-Version aufloesen (Match Name+Groesse). Damit
referenziert der naechste Save immer lebende Blobs und Fix A muss nie greifen.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
check = '--check' in sys.argv

REPLACEMENTS = [
    # Fix A1: kein destroy mehr im create-Call
    (
        'lib/jmap/client.ts',
        """    // Use a single Email/set call with both destroy and create for atomicity
    const setArgs: Record<string, unknown> = {
      accountId: this.accountId,
      create: { [emailId]: emailData },
    };
    if (draftId) {
      setArgs.destroy = [draftId];
    }""",
        """    // Patched (bulkwart-default-de): create and destroy were one Email/set
    // "for atomicity" - but JMAP processes them independently, so a failed
    // create (e.g. stale attachment blobId) still destroyed the previous
    // draft version: data loss. Create first, destroy afterwards; the worst
    // case is now an orphaned old draft instead of a lost one.
    const setArgs: Record<string, unknown> = {
      accountId: this.accountId,
      create: { [emailId]: emailData },
    };""",
    ),
    # Fix A2: destroy nach erfolgreichem create
    (
        'lib/jmap/client.ts',
        """      if (result.created?.[emailId]) {
        return result.created[emailId].id;
      }
    }

    console.error('Unexpected draft save response:', response);
    throw new Error('Failed to save draft');""",
        """      if (result.created?.[emailId]) {
        if (draftId) {
          try {
            await this.request([["Email/set", { accountId: this.accountId, destroy: [draftId] }, "0"]]);
          } catch {
            // Orphaned previous version is acceptable; never fail the save
            // over cleanup.
          }
        }
        return result.created[emailId].id;
      }
    }

    console.error('Unexpected draft save response:', response);
    throw new Error('Failed to save draft');""",
    ),
    # Fix B: BlobIds nach Save gegen neue Draft-Version aufloesen
    (
        'components/email/email-composer.tsx',
        """      // Update the ref synchronously so a queued save sees the new id and
      // doesn't try to destroy the just-replaced draft.
      draftIdRef.current = savedDraftId;
      setDraftId(savedDraftId);""",
        """      // Update the ref synchronously so a queued save sees the new id and
      // doesn't try to destroy the just-replaced draft.
      draftIdRef.current = savedDraftId;
      setDraftId(savedDraftId);
      // Patched (bulkwart-default-de): replacing the draft destroys the
      // previous version and with it the part blobs our hydrated attachments
      // may reference. Re-resolve every attachment blobId against the newly
      // created draft so the next save/send always references live blobs.
      if (savedDraft.attachments?.length) {
        composerClient.getEmail(savedDraftId).then((fresh) => {
          const parts = fresh?.attachments;
          if (!parts?.length) return;
          setAttachments(prev => prev.map(att => {
            if (!att.blobId || att.uploading) return att;
            const m = parts.find(p => (p.name || 'attachment') === att.name && p.size === att.size);
            return m?.blobId ? { ...att, blobId: m.blobId } : att;
          }));
          // Sync the change-detection hash with the remapped blobIds -
          // otherwise the refresh itself reads as a user edit and the
          // autosave replaces the draft in an endless loop (new version ->
          // new part blobIds -> new "change" -> next save ...).
          try {
            const synced = JSON.parse(lastSavedDataRef.current || '{}');
            if (Array.isArray(synced.attachments)) {
              synced.attachments = synced.attachments.map((ua: { blobId: string; name: string; type: string; size: number }) => {
                const m = parts.find(p => (p.name || 'attachment') === ua.name && p.size === ua.size);
                return m?.blobId ? { ...ua, blobId: m.blobId } : ua;
              });
              lastSavedDataRef.current = JSON.stringify(synced);
            }
          } catch {
            // Keep the old hash; worst case is one redundant (no-op) save.
          }
        }).catch(() => {
          // Best effort - on failure the old ids stay and Fix A in
          // createDraft prevents data loss on the next save.
        });
      }""",
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
