## What is this

- [ ] New plugin entry
- [ ] New theme entry
- [ ] Update to an existing entry (version bump / metadata fix)
- [ ] Removal of an entry

## Entry

- id:
- version:
- package/descriptor URL:

## Checklist

- [ ] I read [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] The package/descriptor is hosted at a stable `https://` URL I control.
- [ ] `sha256` in `entry.json` matches the file at that URL
      (`shasum -a 256 <file>`).
- [ ] For a plugin: license is open-source and `source_url`/`pricing` are set
      (closed-source or paid plugins cannot be listed here).
- [ ] For a version bump: the new version is strictly greater than what is
      currently merged.
- [ ] I ran `python3 scripts/validate.py` locally and it passed.
