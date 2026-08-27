#!/usr/bin/env python3
"""Patch 13: Einladungs-Banner parst gegen das falsche Konto.

CalendarInvitationBanner nimmt den global aktiven Client
(useAuthStore(s => s.client)) und dessen getCalendarsAccountId(). Gehoert die
geoeffnete Mail einem anderen angemeldeten Konto (Multi-Account/Unified) oder
einem freigegebenen Postfach, liegt der ICS-Blob in DESSEN Account:
CalendarEvent/parse gegen die falsche accountId liefert einen JMAP-`error`,
der Client wirft, das Banner zeigt nur "Einladung konnte nicht gelesen werden"
(verifiziert: parse mit fremder accountId -> error, mit eigener -> parsed).

Fix wie Patch 8: Client und accountId aus den Source-Stamps der Mail
aufloesen, mit Rueckfall auf das bisherige Verhalten wenn keine Stamps da sind
(Einzelkonto bleibt damit unveraendert).
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
check = '--check' in sys.argv

REPLACEMENTS = [
    (
        'components/email/calendar-invitation-banner.tsx',
        "import { useState, useEffect, useCallback, useRef } from 'react';",
        "import { useState, useEffect, useCallback, useRef, useMemo } from 'react';",
    ),
    (
        'components/email/calendar-invitation-banner.tsx',
        """  const client = useAuthStore((s) => s.client);
  const currentUserEmail = useAuthStore((s) => s.primaryIdentity?.email);""",
        """  const activeClient = useAuthStore((s) => s.client);
  // Patched (bulkwart-default-de): the ICS blob lives in the account that owns
  // the message, not necessarily the active one. Route through the source
  // stamp when present (multi-account / unified view / shared mailbox).
  const client = useMemo(() => {
    const stampedClientId = email.sourceClientAccountId;
    if (!stampedClientId) return activeClient;
    return useAuthStore.getState().getClientForAccount(stampedClientId) ?? activeClient;
  }, [activeClient, email.sourceClientAccountId]);
  const currentUserEmail = useAuthStore((s) => s.primaryIdentity?.email);""",
    ),
    (
        'components/email/calendar-invitation-banner.tsx',
        """      const [events, rawText] = await Promise.all([
        client.parseCalendarEvents(client.getCalendarsAccountId(), attachment.blobId),""",
        """      // Patched (bulkwart-default-de): parse against the account the blob
      // belongs to - a foreign accountId makes Stalwart return a JMAP error
      // and the banner degrades to "invitation could not be read".
      const blobAccountId = email.sourceAccountId ?? client.getCalendarsAccountId();
      const [events, rawText] = await Promise.all([
        client.parseCalendarEvents(blobAccountId, attachment.blobId),""",
    ),
    (
        'components/email/calendar-invitation-banner.tsx',
        """            const blob = await client.fetchBlob(attachment.blobId, 'invite.ics', 'text/calendar');""",
        """            const blob = await client.fetchBlob(attachment.blobId, 'invite.ics', 'text/calendar', email.sourceAccountId);""",
    ),
    (
        'components/email/calendar-invitation-banner.tsx',
        """  }, [calendarInvitationParsingEnabled, client, attachment, supportsCalendar]);""",
        """  }, [calendarInvitationParsingEnabled, client, attachment, supportsCalendar, email.sourceAccountId]);""",
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
