# Changelog

Notable changes to this role. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

## 1.0.0 - 2026-11-12

### Added

- First release.
- Pushes RPM or DEB files from the control node and installs them with the host's package manager (`dnf`, `zypper`, `apt-get` or `dpkg`), with or without the host's repositories for dependencies.
- RPM signature checks against the host's RPM database, after importing key files from the control node, and SHA-256 checks on the control node.
- Reads each package's name and version inside the file on the control node (`files/package_info.py`), so nothing is pushed when every package is installed already, whatever the files are called.
- Molecule tests on RHEL 8, 9 and Rocky 10, Debian 12 and 13, Ubuntu 24.04 and 26.04, and SLES 15 and 16, installing with the repositories switched off.
- `docs/using-without-galaxy.md`.
