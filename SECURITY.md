# Security policy

## Reporting a vulnerability

Report vulnerabilities in this role privately, through [GitHub's private vulnerability reporting](https://github.com/libre-devops/ansible-role-standalone-package-installer/security/advisories/new). Do not open a public issue.

## What the role checks

| Check | Where | Notes |
|---|---|---|
| RPM signatures | On the host, by `dnf` or `zypper`, against its RPM database | On by default (`standalone_package_installer_verify_signatures`). Keys you list in `standalone_package_installer_gpg_keys` are imported first, so check where they came from: Microsoft's are at `https://packages.microsoft.com/keys/`. |
| SHA-256 | On the control node, before anything is pushed | Only for files listed in `standalone_package_installer_checksums`, or every file with `standalone_package_installer_require_checksums`. DEB files carry no signature of their own, so this is the check for them. |

The files wait in `standalone_package_installer_remote_dir`, owned by root with mode 0700, and are deleted afterwards by default. `files/package_info.py` only reads the files' headers on the control node; it never runs anything from them.
