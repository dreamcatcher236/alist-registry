# Contributing

One pull request per plugin or theme listing. CI validates every submission;
a maintainer merges once it's green and the package looks reasonable on
inspection.

## Before you start

- Your plugin or theme must already be built, packaged, and hosted
  somewhere you control — your own GitHub Releases, a CDN, object storage,
  anywhere reachable over plain HTTPS. This repository indexes packages; it
  does not build or host them (the `com.example.demoplugin` and
  `dev.alist.registry.minimal` entries are the exception, kept only to prove
  the format works).
- Read [README.md](README.md)'s "Index schema" first — the fields below are
  copied field-for-field from `alist-org/alist`'s Go source, and a
  submission that doesn't match exactly will fail to install even after
  passing this repo's CI.

## Submitting a plugin

1. Package your plugin the way `alist plugin pack` does: a directory with
   `plugin.json` plus your compiled binary (or `.wasm` module), tarred and
   gzipped. See `tools/demo-plugin` and `tools/frp-plugin` in
   `alist-org/alist` for two working examples, including their `pack.sh`
   scripts.
2. Upload the `.tar.gz` to a stable HTTPS URL (a GitHub Release asset on
   your own plugin's repo is the common choice).
3. Compute its sha256: `shasum -a 256 your-plugin-0.1.0.tar.gz`.
4. Add `plugins/<your-plugin-id>/entry.json`, where `<your-plugin-id>` is
   your manifest's own `id` (reverse-domain, e.g. `com.example.myplugin`)
   and the file's `id` matches it exactly:

   ```json
   {
     "id": "com.example.myplugin",
     "name": "My Plugin",
     "version": "0.1.0",
     "kind": "StorageDriver",
     "core_api": "^0.1.0",
     "sha256": "<64 hex chars>",
     "url": "https://example.com/my-plugin-0.1.0.tar.gz",
     "license": "MIT",
     "source_url": "https://github.com/you/my-plugin",
     "pricing": "free"
   }
   ```

   `sig` is optional — see "Signing and trust" below; omit it if you are not
   self-signing.

   `license` must be a real open-source license, `source_url` must be
   non-empty, and `pricing` must be `"free"`. Closed-source or paid plugins
   cannot be listed here: `alist-org/alist`'s `ClosedOrPaid` check forces
   them to the least-trusted tier regardless of signature. Distribute a
   closed or paid plugin by direct URL install instead.

5. Open a PR. `.github/workflows/validate.yml` checks:
   - every required field is present and well-formed,
   - the URL is `https://` and nothing else,
   - the package downloads and hashes to your declared `sha256`,
   - the version is a plain `MAJOR.MINOR.PATCH`,
   - if you are updating an existing entry, the new version is strictly
     greater than the merged one.

## Submitting a theme

1. Write a theme descriptor JSON — `id` is the only field the backend
   requires; see `themes/dev.alist.registry.minimal/theme.json` for a
   minimal example, and the AList docs site for the full token vocabulary
   the frontend renders.
2. Host it at a stable HTTPS URL.
3. Add `themes/<your-theme-id>/entry.json`:

   ```json
   {
     "id": "your.theme.id",
     "name": "Your Theme",
     "author": "you",
     "version": "1.0.0",
     "url": "https://example.com/your-theme.json",
     "sha256": "<64 hex chars>",
     "has_js": false
   }
   ```

   Set `has_js: true` only if your descriptor carries a `js` field. A theme
   with custom JS installs only from a signed, verified source — see below.

4. Open a PR; the same CI job validates theme entries (https-only, sha256
   match, version monotonicity).

## Signing and trust

`alist-org/alist` classifies every plugin/theme source into a trust tier by
who signed it, not by which registry lists it.

- **Plugin sources require a public key**
  (`extension.PluginSource.PubKey` is not optional). This registry's public
  key is in [README.md](README.md#signing-and-trust) — import it to see
  entries a maintainer has personally reviewed and re-signed as
  source-verified (🟡). Everything else in `plugins/` installs as
  third-party (🔴): installable, just unattributed. This registry does not
  auto-sign every PR.
- **Theme sources may omit a public key**
  (`thememarket.Source.PubKey` is optional); without one, every theme
  installs as `untrusted`. To have your theme entries verify against your
  own key instead of this registry's, sign them yourself: the signed bytes
  are `id|version|sha256|url` (`canonicalEntrySigningInput` in
  `internal/thememarket/thememarket.go`), hex-encoded into the entry's
  `signature` field. The admin importing your source supplies your key, not
  this registry's.

A registry-held private key is never committed to this repository and never
stored as a CI secret. Signing is a manual, offline action a maintainer
performs after reviewing and rebuilding a submission. Ask in your PR if you
want yours reviewed and signed — it does not happen automatically.

## Removing or updating an entry

Open a PR editing or deleting the relevant `entry.json`. Deleting an entry
here does not uninstall it for anyone who already added it — sources are
fetched live, so it simply stops appearing in future browse/index calls.
