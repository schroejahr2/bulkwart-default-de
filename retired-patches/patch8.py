#!/usr/bin/env python3
"""Scoped-Email-Id-Patch fuer Bulwark (JMAP-Id-Kollision ueber Konten hinweg).

Stalwart vergibt Email-Ids pro Konto aus ueberlappenden Nummernkreisen. Bulwark
haelt alle Konten in einer flachen `emails: Email[]`-Liste mit rohen JMAP-Ids und
loest den Detail-Fetch per id-only-`find` auf -> bei Kollision wird die Mail des
falschen Kontos geholt und angezeigt.

Aufruf:  python3 bulwark-id-scope-patch.py <repo-root> [--check]
--check verifiziert nur, dass alle Anker genau einmal vorkommen.
"""

import io
import os
import sys

# (Datei, alt, neu, erwartete Trefferzahl)
PATCHES = [
    # ---------------------------------------------------------------- Fix 1
    # Das geklickte Email-Objekt nicht mehr auf seine Id reduzieren.
    (
        "components/mail/mail-app.tsx",
        "  const handleEmailSelect = async (email: { id: string }) => {",
        "  const handleEmailSelect = async (email: { id: string } & Partial<Email>) => {",
        1,
    ),
    (
        "components/mail/mail-app.tsx",
        "    const listEmail = activeEmails.find(e => e.id === email.id);",
        "    // JMAP-Email-Ids sind kontoskopiert und Stalwart vergibt ueberlappende\n"
        "    // Nummernkreise, d.h. `activeEmails` kann zwei verschiedene Mails unter\n"
        "    // derselben Id halten. Ein id-only-Lookup trifft dann die Zeile des\n"
        "    // anderen Kontos und der Fetch unten geht an den falschen Server.\n"
        "    const clicked = email as Email;\n"
        "    const listEmail = clicked.sourceAccountId\n"
        "      ? clicked\n"
        "      : activeEmails.find(e => e.id === email.id);",
        1,
    ),
    # ---------------------------------------------------------------- Fix 2
    # Source-Stamp gilt immer, nicht nur solange `isUnifiedView` gesetzt ist.
    (
        "components/mail/mail-app.tsx",
        "      const sourceClientId = isUnifiedView ? listEmail?.sourceClientAccountId : undefined;",
        "      // Der Stamp gewinnt, wann immer er da ist: er ueberlebt den\n"
        "      // Boot-Snapshot, in dem `isUnifiedView` noch nicht wiederhergestellt ist.\n"
        "      const sourceClientId = listEmail?.sourceClientAccountId;",
        1,
    ),
    (
        "components/mail/mail-app.tsx",
        "      const accountId = isUnifiedView\n"
        "        ? listEmail?.sourceAccountId\n"
        "        : (() => {",
        "      const accountId = listEmail?.sourceAccountId\n"
        "        ?? (() => {",
        1,
    ),
    # ---------------------------------------------------------------- Fix 3a
    # handleEmailSelect: kein stiller Rueckfall auf den aktiven Client, und ohne
    # Stamp gilt das gerade angezeigte (Pro-Sidebar-)Konto statt des aktiven.
    (
        "components/mail/mail-app.tsx",
        "      const perAccountClient = sourceClientId\n"
        "        ? useAuthStore.getState().getClientForAccount(sourceClientId)\n"
        "        : undefined;\n"
        "      const fetchClient = perAccountClient ?? client;",
        "      const perAccountClient = sourceClientId\n"
        "        ? useAuthStore.getState().getClientForAccount(sourceClientId)\n"
        "        : undefined;\n"
        "      // Ein gestempeltes Quellkonto ohne auffindbaren Client darf NICHT auf\n"
        "      // den aktiven Client zurueckfallen - genau so wird eine fremde Id im\n"
        "      // falschen Konto aufgeloest. Ohne Stamp gilt das Konto, dessen Ordner\n"
        "      // gerade angezeigt wird (Pro-Sidebar), nicht zwingend das aktive.\n"
        "      const viewingClient = viewingAccountId\n"
        "        ? useAuthStore.getState().getClientForAccount(viewingAccountId)\n"
        "        : null;\n"
        "      const fetchClient = sourceClientId ? perAccountClient : (viewingClient ?? client);\n"
        "      if (!fetchClient) return;",
        1,
    ),
    # ---------------------------------------------------------------- Fix 3b
    # Auto-Select-Effekt: gleiche Regel.
    (
        "components/mail/mail-app.tsx",
        "      const perAccountClient = isUnifiedView && selectedEmail.sourceClientAccountId\n"
        "        ? useAuthStore.getState().getClientForAccount(selectedEmail.sourceClientAccountId)\n"
        "        : undefined;\n"
        "      const fetchClient = perAccountClient ?? client;",
        "      // Stamp gilt unabhaengig von `isUnifiedView` (er ueberlebt den\n"
        "      // Boot-Snapshot); ohne auffindbaren Client wird NICHT auf den aktiven\n"
        "      // Client zurueckgefallen, sonst wird eine fremde Id dort aufgeloest.\n"
        "      const stampedClientId = selectedEmail.sourceClientAccountId;\n"
        "      const perAccountClient = stampedClientId\n"
        "        ? useAuthStore.getState().getClientForAccount(stampedClientId)\n"
        "        : (viewingAccountId\n"
        "            ? useAuthStore.getState().getClientForAccount(viewingAccountId)\n"
        "            : undefined);\n"
        "      const fetchClient = perAccountClient ?? (stampedClientId ? null : client);\n"
        "      if (!fetchClient) return;",
        1,
    ),
    # ---------------------------------------------------------------- Fix 3c
    # Re-Stamp der Source-Referenz auf die geoeffnete Mail ebenfalls entkoppeln,
    # sonst verlieren Folgeaktionen (Delete/Archive/Keywords) nach einem Restore
    # ihr Routing. Bei ungestempelten Zeilen werden nur undefined-Felder
    # zugewiesen - fuer den Normalfall ein No-op.
    (
        "components/mail/mail-app.tsx",
        "        if (isUnifiedView && listEmail) {",
        "        if (listEmail) {",
        1,
    ),
    # ---------------------------------------------------------------- Fix 4
    # Store-seitige Aktions-Aufloesung ebenfalls entkoppeln.
    (
        "stores/email-store.ts",
        "  if (state.isUnifiedView && email.sourceClientAccountId && email.sourceAccountId) {",
        "  if (email.sourceClientAccountId && email.sourceAccountId) {",
        1,
    ),
    # ---------------------------------------------------------------- Fix 5
    # fetchEmailContent: Routing-Referenz aus der Selektion, nicht per Id-Suche.
    (
        "stores/email-store.ts",
        "      const listEmail = get().emails.find(e => e.id === emailId);\n"
        "      let actionClient: IJMAPClient;",
        "      // Der Source-Stamp der aktuellen Selektion schlaegt die Id-Suche:\n"
        "      // `emails` kann zwei Mails gleicher Id aus verschiedenen Konten halten.\n"
        "      const selected = get().selectedEmail;\n"
        "      const listEmail = (selected?.id === emailId && selected.sourceAccountId)\n"
        "        ? selected\n"
        "        : get().emails.find(e => e.id === emailId);\n"
        "      let actionClient: IJMAPClient;",
        1,
    ),
    # ---------------------------------------------------------------- Fix 6
    # Thread-Routing: Stamp gilt auch ohne aktiven Unified-View.
    (
        "lib/thread-routing.ts",
        "  isUnifiedView,\n"
        "  ref,\n"
        "  mailboxes,\n"
        "  selectedMailbox,\n"
        "}: {",
        "  isUnifiedView: _isUnifiedView,\n"
        "  ref,\n"
        "  mailboxes,\n"
        "  selectedMailbox,\n"
        "}: {",
        1,
    ),
    (
        "lib/thread-routing.ts",
        "  if (isUnifiedView && ref?.sourceClientAccountId && ref?.sourceAccountId) {",
        "  if (ref?.sourceClientAccountId && ref?.sourceAccountId) {",
        1,
    ),
    # ---------------------------------------------------------------- Fix 7
    # Boot-Snapshot: gemischte Unified-Liste nie persistieren ...
    (
        "stores/email-store.ts",
        "      if (s.searchQuery || s.selectedKeyword || s.isScheduledView || s.viewingAccountId) return;",
        "      // Unified-/Cross-Views mischen mehrere Konten in eine Liste, aber der\n"
        "      // Zustand, der sie routbar macht (isUnifiedView / unifiedRole /\n"
        "      // crossView), wird nicht persistiert. Ein Restore ohne ihn laesst\n"
        "      // Fremdkonto-Zeilen zurueck, die gegen das aktive Konto aufgeloest\n"
        "      // werden - genau die Id-Kollision.\n"
        "      if (s.searchQuery || s.selectedKeyword || s.isScheduledView || s.viewingAccountId || s.isUnifiedView) return;",
        1,
    ),
    # ... und bereits vergiftete Snapshots von Bestandsnutzern verwerfen.
    (
        "stores/email-store.ts",
        "const EMAIL_SNAPSHOT_VERSION = 1;",
        "const EMAIL_SNAPSHOT_VERSION = 2;",
        1,
    ),
]


# Anker fuer Features, die im aktuell gebauten Tag noch fehlen koennen
# (lib/thread-routing.ts + Boot-Snapshot kamen erst nach 1.8.1). Fehlen sie,
# wird der jeweilige Fix mit Warnung uebersprungen statt zu failen.
OPTIONAL_FILES = {"lib/thread-routing.ts"}
OPTIONAL_ANCHOR_STARTS = (
    "      if (s.searchQuery || s.selectedKeyword",
    "const EMAIL_SNAPSHOT_VERSION = 1;",
)


def is_optional(rel: str, old: str) -> bool:
    return rel in OPTIONAL_FILES or old.startswith(OPTIONAL_ANCHOR_STARTS)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = sys.argv[1]
    check_only = "--check" in sys.argv[2:]

    problems = []
    edits: dict[str, str] = {}

    for rel, old, new, expect in PATCHES:
        path = os.path.join(root, rel)
        if path not in edits:
            if not os.path.exists(path):
                if is_optional(rel, old):
                    print(f"skip (optional, Datei fehlt in diesem Tag): {rel}")
                else:
                    problems.append(f"FEHLT: {rel}")
                continue
            edits[path] = io.open(path, encoding="utf-8").read()
        text = edits[path]
        found = text.count(old)
        if found != expect:
            if found == 0 and is_optional(rel, old):
                print(f"skip (optional, Anker fehlt in diesem Tag): {rel}: {old.splitlines()[0][:60]}")
                continue
            problems.append(
                f"ANKER {rel}: {found} Treffer, erwartet {expect} -> {old.splitlines()[0][:70]}"
            )
            continue
        edits[path] = text.replace(old, new)
        print(f"ok  {rel}: {found}x {old.splitlines()[0].strip()[:64]}")

    if problems:
        print("\nFEHLER:")
        for p in problems:
            print("  " + p)
        return 1

    if check_only:
        print("\n--check: alle Anker eindeutig, nichts geschrieben.")
        return 0

    for path, text in edits.items():
        io.open(path, "w", encoding="utf-8").write(text)
    print(f"\n{len(edits)} Dateien gepatcht.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
