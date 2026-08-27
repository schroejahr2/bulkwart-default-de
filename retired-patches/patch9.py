#!/usr/bin/env python3
"""Patch 9: Wiedergeoeffnete Entwuerfe verlieren die Signatur (Stand 1.8.1).

Bug: Drafts werden immer im Modus 'compose' wiedergeoeffnet.
`shouldEmbedSignatureInNewMail = mode === 'compose' && hasInitialSignature`
ist dann wahr, obwohl der Body aus initialData kam und getInitialBody (das
die Signatur einbetten wuerde) nie lief. Folgen in 1.8.1 an ZWEI Stellen:
- Send-Pfad: signatureAlreadyInBody true -> Append uebersprungen, Mail geht
  ohne Signatur raus
- Vorschau: gleicher Ausdruck inline im JSX -> graue Signatur-Vorschau fehlt

Fix: Der Embed-Anspruch zaehlt nur, wenn der Body wirklich neu gebaut wurde
(initialData?.body == null). Traegt der wiedergeoeffnete Body die Signatur
bereits eingebettet (Marker data-signature-block aus buildEmbeddedSignatureHtml
/ SignatureBlock), gilt sie weiter als vorhanden - sonst Doppel-Signatur bei
Compose->Speichern->Wiederoeffnen.

Bekannter Rest-Randfall: Plain-Text-Drafts haben keine Marker; dort kann die
Signatur nach Wiederoeffnen doppelt angehaengt werden (sichtbar, loeschbar) -
besser als der stille Verlust vorher.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
check = '--check' in sys.argv

REPLACEMENTS = [
    # A) Send-Pfad
    (
        'components/email/email-composer.tsx',
        """    const signatureAlreadyInBody =
      shouldEmbedSignatureInNewMail ||
      ((mode === 'reply' || mode === 'replyAll' || mode === 'forward') &&
        signaturePosition === 'above_quote');""",
        """    // Patched (bulkwart-default-de): re-opened drafts mount in compose mode
    // with the body from initialData - getInitialBody never ran, so compose
    // mode alone must not claim the signature is embedded. If the draft body
    // carries the embedded signature markers, it still counts as present.
    const draftBodyCarriesSignature =
      initialData?.body != null && initialData.body.includes('data-signature-block');
    const signatureAlreadyInBody =
      (shouldEmbedSignatureInNewMail && initialData?.body == null) ||
      draftBodyCarriesSignature ||
      ((mode === 'reply' || mode === 'replyAll' || mode === 'forward') &&
        signaturePosition === 'above_quote');""",
    ),
    # B) Vorschau (JSX)
    (
        'components/email/email-composer.tsx',
        """        {(shouldEmbedSignatureInNewMail
          || ((mode === 'reply' || mode === 'replyAll' || mode === 'forward') && signaturePosition === 'above_quote')) ? null""",
        """        {((shouldEmbedSignatureInNewMail && initialData?.body == null)
          || (initialData?.body != null && initialData.body.includes('data-signature-block'))
          || ((mode === 'reply' || mode === 'replyAll' || mode === 'forward') && signaturePosition === 'above_quote')) ? null""",
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
