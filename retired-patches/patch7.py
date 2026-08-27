#!/usr/bin/env python3
"""Patch 7 (bulkwart-default-de): Reload-Pfade kennen die Unified-Ansicht nicht.

Im Unified-View ist selectedMailbox eine virtuelle ID ('__unified_inbox__',
'__cross_all__', ...) und keine echte JMAP-Mailbox. fetchEmails() und
refreshCurrentMailbox() reichen sie unveraendert an getEmails() weiter, bekommen
nichts zurueck und ueberschreiben die Liste mit leer.

Sichtbar als: Pull-to-Refresh / F5 / Cmd-R / Rueckkehr aus Kalender+Kontakten
leeren das gemeinsame Postfach ("keine neuen Mails"), bis man den Ordner im
Menue neu anklickt.

Der Fix ist kein neuer Code - loadMoreEmails() und undoSpam() im selben Store
machen es bereits richtig. Die Weiche wird nur an die zwei Stellen gehoben, die
sie nicht haben. Der Guard in fetchEmails() sitzt am Choke-Point und deckt damit
auch Aufrufer ab, die wir nicht einzeln patchen (u.a. handleManualRefresh in
components/mail/mail-app.tsx).
"""

p = 'stores/email-store.ts'
s = open(p).read()

MARKER = 'Patched (bulkwart-default-de): virtuelle Unified-'
assert MARKER not in s, 'Patch 7 bereits angewandt?'
assert 'isUnifiedMailboxId, isCrossViewId' in s, 'isUnifiedMailboxId/isCrossViewId nicht importiert - Patch anpassen'
assert 'export async function buildUnifiedAccountClients(' in s, 'buildUnifiedAccountClients fehlt - Patch anpassen'

# --- A: fetchEmails ----------------------------------------------------
anchor_a = """      const targetMailboxId = mailboxId || get().selectedMailbox;
      if (targetMailboxId === VIRTUAL_SCHEDULED_MAILBOX_ID) {"""
assert anchor_a in s, 'Anker A (fetchEmails) nicht gefunden - Upstream geaendert, Patch anpassen'

replacement_a = """      const targetMailboxId = mailboxId || get().selectedMailbox;
      // Patched (bulkwart-default-de): virtuelle Unified-/Cross-IDs sind keine
      // JMAP-Mailboxen. Ohne diese Weiche laedt getEmails() ins Leere und die
      // Liste wird geloescht (Pull-to-Refresh, F5, Rueckkehr aus dem Kalender).
      if (targetMailboxId && (isUnifiedMailboxId(targetMailboxId) || isCrossViewId(targetMailboxId))) {
        const includeGroup = useSettingsStore.getState().includeGroupInUnified;
        const accounts = await buildUnifiedAccountClients({ includeGroup });
        if (isCrossViewId(targetMailboxId) && get().crossView) {
          await get().fetchCrossView(accounts, get().crossView!);
        } else if (get().unifiedRole) {
          await get().fetchUnifiedEmails(accounts, get().unifiedRole!);
        } else {
          set({ isLoading: false });
        }
        return;
      }
      if (targetMailboxId === VIRTUAL_SCHEDULED_MAILBOX_ID) {"""

s = s.replace(anchor_a, replacement_a, 1)
print('7A: fetchEmails-Guard gesetzt')

# --- B: refreshCurrentMailbox ------------------------------------------
anchor_b = """    if (selectedMailbox === VIRTUAL_SCHEDULED_MAILBOX_ID) {
      await get().fetchScheduledEmails(client);
      return;
    }"""
assert anchor_b in s, 'Anker B (refreshCurrentMailbox) nicht gefunden - Upstream geaendert, Patch anpassen'

replacement_b = anchor_b + """

    // Patched (bulkwart-default-de): siehe Guard in fetchEmails - hier laeuft
    // der Reload direkt gegen client.getEmails(), die virtuelle ID findet keine
    // Mailbox. Gleiche Weiche wie in loadMoreEmails()/undoSpam().
    if (isUnifiedMailboxId(selectedMailbox) || isCrossViewId(selectedMailbox)) {
      const includeGroup = useSettingsStore.getState().includeGroupInUnified;
      const accounts = await buildUnifiedAccountClients({ includeGroup });
      if (get().crossView) {
        await get().fetchCrossView(accounts, get().crossView!);
      } else if (get().unifiedRole) {
        await get().fetchUnifiedEmails(accounts, get().unifiedRole!);
      }
      return;
    }"""

s = s.replace(anchor_b, replacement_b, 1)
open(p, 'w').write(s)
print('7B: refreshCurrentMailbox-Weiche gesetzt')
