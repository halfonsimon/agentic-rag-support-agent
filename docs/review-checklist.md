# Manual review before pushing

- [ ] Read all files and local commits; confirm the work is yours to share publicly.
- [ ] Confirm the original source is intact and excluded materials and real customer records are absent.
- [ ] Rotate or revoke the credential embedded in the original source; do not reuse it.
- [ ] Check `.env` and `local_data/` stay ignored; keep keys, resource URLs and private data out of Git.
- [ ] Run the documented clean install, Ruff and pytest in a fresh Python 3.11/3.12 environment.
- [ ] Run the eight live evals with your own test key and only fictional credentials; read every answer.
- [ ] Review the approved lookup redaction, calculator bounds and strict request limit.
- [ ] Review demo authentication and model-transcript limitations before using any real customer data.
- [ ] Verify external dataset licensing and column mapping before connecting a larger catalog.
- [ ] Create the destination repository yourself and explicitly set its visibility to **Public**.
- [ ] Check the local Git remote and intended destination carefully before your first manual push.
