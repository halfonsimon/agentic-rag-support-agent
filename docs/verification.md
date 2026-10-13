# Local verification

- **41 offline pytest tests passed**, without any model credentials or model downloads.
- **Ruff 0.11.13:** 16 Python files checked and formatted with Astral's official WebAssembly
  build; zero findings, using the same rule selection, target version, line length and
  first-party import configuration as `pyproject.toml`.
- **Real Chroma 0.5.5 smoke:** all 10 fictional catalog rows indexed and retrieved with
  deterministic local embeddings. This checks the database integration, not semantic quality.
- **Packaging smoke:** a wheel built successfully and its bundled data worked after installation
  outside the checkout; product filtering and customer authentication both passed.
- **Live eval guard:** the script skipped with no key, making no API requests. Its eight
  expected-answer cases are present, but live answer quality has not been measured.
- **Source integrity:** metadata for all 46,717 original files matched the initial snapshot;
  cryptographic digests of the three permitted source files also matched.
- **Safety scan:** gitleaks was unavailable. A whole-target text scan covered the requested
  patterns, and source-specific secret and identity strings were checked without printing
  them. Reachable Git objects were also decoded and scanned. No original secrets, resource
  endpoint or personal identifiers were found. Ordinary configuration names, authentication
  documentation and fictional demo questions account for the text-pattern matches.
- **File sizes:** no working-tree or Git metadata file exceeded 500 KB.

The network-restricted session could not perform a fresh PyPI dependency installation, so
pytest and smoke checks read installed dependency packages from the existing local runtime.
Bytecode generation was disabled to protect the original folder. No environment or course
files were copied into this repository. The full no-secret CI workflow is defined but has
not run remotely. The local runtime emits a `pkg_resources` deprecation warning from mongomock;
Chroma also logs telemetry-library compatibility errors, while its indexing/query smoke succeeds.

No GitHub repository was created, no remote was configured, and nothing was pushed.
Git commits use a neutral local contributor identity, without the original personal header.

## Verification after relocation

The user completed dependency installation and reported successful native Ruff checks,
16 correctly formatted Python files, and 41 passing tests. The seven warnings were
dependency deprecations. A further publication scan checked all 32 tracked files and
59 Git objects without finding original credentials, resource endpoints or personal
identifiers. Local configuration and virtual environments remain ignored.
