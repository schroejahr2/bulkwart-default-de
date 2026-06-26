# bulkwart-default-de

Rebuild von [Bulwark Webmail](https://github.com/bulwarkmail/webmail) mit
**deutschem Default-Locale** (`NEXT_PUBLIC_DEFAULT_LOCALE=de`).

## Warum
`NEXT_PUBLIC_*`-Vars werden in Next.js zur **Build-Zeit** ins Client-Bundle
einkompiliert — das offizielle `:latest`-Image hat `en` fest gebacken, ein
Runtime-env wirkt nicht. Darum bauen wir selbst mit `de` als Default.

## Wie
`.github/workflows/build.yml` pollt täglich den neuesten Upstream-Tag, baut ihn
(falls noch nicht gebaut) mit dem Build-Arg `NEXT_PUBLIC_DEFAULT_LOCALE=de` und
pusht nach GHCR:

- `ghcr.io/schroejahr2/bulkwart-default-de:latest`
- `ghcr.io/schroejahr2/bulkwart-default-de:<upstream-tag>`

Deploy: rg-storage `bulwark`-Stack zieht `:latest` via Watchtower.
Manueller Build: Actions -> "build-bulkwart-default-de" -> Run workflow.
