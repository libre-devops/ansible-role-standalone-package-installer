<div align="center">
  <a href="https://libredevops.org">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://libredevops.org/assets/libre-devops-white.png">
      <img alt="Libre DevOps" src="https://libredevops.org/assets/libre-devops-black.png" width="300">
    </picture>
  </a>
</div>

# Ansible Role: Standalone package installer

Pushes `.rpm` or `.deb` files you already have from the control node to each host, and installs them with the host's own package manager. RPM signatures are checked, and so are checksums when you give them. A quick way to debug, test, or install something once on hosts that cannot reach its repository, such as an agent package before the agent's own role configures it.

[![CI](https://github.com/libre-devops/ansible-role-standalone-package-installer/actions/workflows/ci.yml/badge.svg)](https://github.com/libre-devops/ansible-role-standalone-package-installer/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/libre-devops/ansible-role-standalone-package-installer?sort=semver&label=release)](https://github.com/libre-devops/ansible-role-standalone-package-installer/releases/latest)
[![Galaxy](https://img.shields.io/badge/galaxy-libre__devops.standalone__package__installer-EE0000?logo=ansible&logoColor=white)](https://galaxy.ansible.com/ui/standalone/roles/libre_devops/standalone_package_installer/documentation/)
[![Licence](https://img.shields.io/github/license/libre-devops/ansible-role-standalone-package-installer)](./LICENSE)

---

## What it does

1. Finds the files on the control node (paths or globs), checks they are the host's package type, and checks their SHA-256 against `standalone_package_installer_checksums`.
2. Reads the package name and version inside each file on the control node, and asks the host what it has. When every package is already installed at that version, it stops there: nothing is pushed.
3. Otherwise copies the files to the host, imports any signing keys you give into the RPM database, and installs them with `dnf`, `zypper`, `apt-get` or `dpkg`, from the files alone or with the host's repositories for missing dependencies.
4. Deletes the files from the host.

It is for debugging, testing and one-offs. For anything you keep, give the hosts a repository (a mirror, Satellite, or the vendor's) and use the software's own role.

## Contents

- [Requirements](#requirements)
- [Supported platforms](#supported-platforms)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Role variables](#role-variables)
- [How it decides what to push](#how-it-decides-what-to-push)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Developing](#developing)
- [Releasing](#releasing)

## Requirements

| What | Detail |
|---|---|
| Control node | `ansible-core` 2.16 or later. `community.general` for SUSE hosts only (`community.general.zypper`). |
| Managed nodes | A Python your `ansible-core` supports. RHEL 8 and SLES 15 ship Python 3.6, which ansible-core 2.17 and later cannot use: run [libre_devops.python](https://github.com/libre-devops/ansible-role-python) first, which can itself install Python from pushed packages. |
| Files | Packages built for the hosts' distribution and release, with the dependencies the hosts cannot get from their repositories. |
| Privileges | `become: true`. |

## Supported platforms

Each platform below runs in CI on every pull request: it downloads `jq` and its dependencies from its own repositories, then the role pushes and installs them with the repositories switched off.

| Distribution | Package type | Installed with |
|---|---|---|
| RHEL 8 and 9 (UBI), Rocky 10 | `.rpm` | `dnf`, signatures checked |
| SLES 15 SP7 and 16 | `.rpm` | `community.general.zypper`, signatures checked |
| Debian 12 and 13, Ubuntu 24.04 and 26.04 | `.deb` | `apt-get` (or `dpkg` without repositories), checksums checked |

Outside CI, on 11 November 2026, it pushed Microsoft's `mdatp` 101.26101.0000 and `azcmagent` 1.70.03595 RPMs to AlmaLinux 9 with their signatures checked, chained with `libre_devops.mde_linux` (install only, `mde_linux_onboard: false`) and `libre_devops.azure_arc` (`azure_arc_connect: false`), both with their repository management off. A second run of each changed nothing. Onboarding and connecting were not part of that test: see [Examples](#examples).

## Installation

From Galaxy:

```bash
ansible-galaxy role install libre_devops.standalone_package_installer
ansible-galaxy collection install community.general   # SUSE hosts only
```

Or pin a release from GitHub, as in [`examples/requirements.yml`](./examples/requirements.yml).

Without Galaxy, or to keep a copy inside your organisation, see [Using the role without Galaxy](./docs/using-without-galaxy.md).

## Quick start

```yaml
- name: Install the package files I brought in
  hosts: rhel9_servers
  become: true
  roles:
    - role: libre_devops.standalone_package_installer
      vars:
        standalone_package_installer_files:
          - files/rhel9/*.rpm
```

## Role variables

Every variable is validated against [`meta/argument_specs.yml`](./meta/argument_specs.yml) when the role starts. Defaults are in [`defaults/main.yml`](./defaults/main.yml).

| Variable | Default | Description |
|---|---|---|
| `standalone_package_installer_files` | `[]` | Package files on the control node, as paths or globs. RPMs for the Red Hat and SUSE families, DEBs for the Debian family, so give each group of hosts its own list. Every entry must match a file. |
| `standalone_package_installer_use_repos` | `true` | Let the package manager fetch missing dependencies from the host's own repositories (the distribution's, Satellite or a mirror). `false` installs from the files alone. |
| `standalone_package_installer_verify_signatures` | `true` | RPMs: check each signature against the host's RPM database. |
| `standalone_package_installer_gpg_keys` | `[]` | Key files on the control node to import into the host's RPM database first, such as Microsoft's (`https://packages.microsoft.com/keys/microsoft.asc`). |
| `standalone_package_installer_checksums` | `{}` | SHA-256 by file name, checked on the control node before anything is pushed. DEB files carry no signature, so this is how to check them. |
| `standalone_package_installer_require_checksums` | `false` | Refuse any file without a checksum entry. |
| `standalone_package_installer_allow_downgrade` | `false` | Let a file replace a newer installed version. |
| `standalone_package_installer_remote_dir` | `/var/tmp/standalone-package-installer` | Where the files wait on the host. |
| `standalone_package_installer_cleanup` | `true` | Delete them afterwards. |

| Fact | What it holds |
|---|---|
| `standalone_package_installer_result` | `files` (the file names), `packages` (name to version) and `pushed` (whether anything went to the host this run). |

## How it decides what to push

On the control node, [`files/package_info.py`](./files/package_info.py) reads each package's name and version from inside the file: the header of an RPM, the `control` file of a DEB. File names are not trusted, because they vary: Microsoft names its RPMs `mdatp_101.23072.0021.x86_64.rpm`, for example. The role then asks the host (`rpm -q`, `dpkg-query`) and pushes only when a package is missing or at another version. A second run therefore copies nothing, even for an agent of a hundred megabytes or more.

Ubuntu builds its own packages with zstd compression, which Python reads only from 3.14. On an older control node the role falls back to the conventional file name (`name_version_arch.deb`), which Ubuntu's own downloads follow. A file it can read neither way is pushed every run, and the package manager decides whether anything changes.

## Examples

### Defender for Endpoint on hosts without Microsoft's repository

Push the agent, then let [libre_devops.mde_linux](https://github.com/libre-devops/ansible-role-mde-linux) onboard and configure it without adding the repository:

```yaml
- name: Defender for Endpoint from package files
  hosts: rhel9
  become: true
  roles:
    - role: libre_devops.standalone_package_installer
      vars:
        standalone_package_installer_files:
          - files/mde/mdatp-101.26101.0000-1.x86_64.rpm
        standalone_package_installer_gpg_keys:
          - files/keys/microsoft.asc
          - files/keys/microsoft-2025.asc
    - role: libre_devops.mde_linux
      vars:
        mde_linux_manage_repository: false
        mde_linux_onboarding_file: files/mdatp_onboard.json
        mde_linux_expected_org_id: 00000000-0000-0000-0000-000000000000
```

Get the RPM on a machine that can reach Microsoft's repository, with the same release:

```bash
dnf --repofrompath=ms,https://packages.microsoft.com/rhel/9/prod --setopt=ms.gpgcheck=0 \
  install --downloadonly --downloaddir=files/mde mdatp
```

`gpgcheck=0` only skips the check during the download: the role checks the signature on each host against Microsoft's keys before installing. The dependencies (`audit`, `policycoreutils` and so on) come from the hosts' own repositories; with none, add them to the files and set `standalone_package_installer_use_repos: false`.

### Azure Arc agent the same way

```yaml
- name: Azure Arc agent from package files
  hosts: rhel9
  become: true
  roles:
    - role: libre_devops.standalone_package_installer
      vars:
        standalone_package_installer_files:
          - files/arc/azcmagent-*.x86_64.rpm
        standalone_package_installer_gpg_keys:
          - files/keys/microsoft.asc
          - files/keys/microsoft-2025.asc
    - role: libre_devops.azure_arc
      vars:
        azure_arc_manage_repository: false
        # ... the target and sign-in variables from libre_devops.azure_arc's Quick start
```

### Ubuntu, with checksums for the DEB files

```yaml
standalone_package_installer_files:
  - files/ubuntu2404/mdatp_101.26101.0000_amd64.deb
standalone_package_installer_checksums:
  mdatp_101.26101.0000_amd64.deb: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
standalone_package_installer_require_checksums: true
```

### RHEL 8 hosts with only Python 3.6

RHEL 8 ships Python 3.6, which ansible-core 2.17 and later cannot use, so put [libre_devops.python](https://github.com/libre-devops/ansible-role-python) first. It can install Python 3.12 from the host's repositories, or push it as package files too.

```yaml
# requirements.yml
roles:
  - name: libre_devops.python
    src: https://github.com/libre-devops/ansible-role-python.git
    scm: git
    version: 1.0.0
  - name: libre_devops.standalone_package_installer
    src: https://github.com/libre-devops/ansible-role-standalone-package-installer.git
    scm: git
    version: 1.0.0
```

```yaml
- name: Packages on RHEL 8
  hosts: rhel8
  become: true
  # Gathering facts would fail on Python 3.6. libre_devops.python gathers them once it has
  # installed Python 3.12.
  gather_facts: false
  roles:
    - role: libre_devops.python
    - role: libre_devops.standalone_package_installer
      vars:
        standalone_package_installer_files:
          - files/rhel8/*.rpm
```

## Troubleshooting

| Symptom | What to check |
|---|---|
| `... matches no file on the control node` | The path is relative to where you run `ansible-playbook`, or the glob matches nothing. |
| `installs .rpm files, but was given ...` | A DEB went to a Red Hat or SUSE host, or the other way round. Give each group of hosts its own list. |
| `Depsolve Error ... nothing provides ...` | A dependency is in neither the files nor the host's repositories. Add it to the files, or point the host at a repository that has it. Minimal images such as UBI lack many. |
| `public key ... is not installed`, or a signature error | Add the vendor's key to `standalone_package_installer_gpg_keys`, or check the files came from the vendor. |
| `Unsupported version of key: V6` | A key file holds a key the host's `rpm` cannot read, such as RHEL 9's post-quantum key. Import only the keys you need. |
| `SHA-256 ... does not match` | The file changed since you recorded its checksum. |

## Developing

You need [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just) and [podman](https://podman.io/). CI runs the same recipes.

| Recipe | What it does |
|---|---|
| `just deps` | Installs the pinned Python tools (`uv.lock`) and the collections in `requirements.yml` into `.ansible/`. |
| `just lint` | `yamllint`, `ansible-lint` on the production profile, and `zizmor` on the workflows. |
| `just test [scenario] [platform]` | Runs a Molecule scenario on one platform, or on all of them. `just test default rhel9`. |
| `just converge <scenario> <platform>` | Runs a scenario on one platform and leaves the container running, pass or fail. `just login` opens a shell in it, `just destroy` removes it. |
| `just live <inventory> [args]` | Runs [`examples/playbook.yml`](./examples/playbook.yml) against real hosts. |
| `just secrets` | Scans the git history with gitleaks. |

The `default` scenario downloads `jq` and what it needs on each platform, copies the files and the distribution's signing key to the control node, then runs the role with the repositories switched off, checking RPM signatures after importing the key, and DEB checksums. A second run must push nothing.

## Releasing

1. Move the Unreleased entries in [`CHANGELOG.md`](./CHANGELOG.md) under the new version.
2. Run `just release 1.2.3`. It tags the commit and pushes the tag.
3. The Release workflow creates the GitHub release, imports the tag into Galaxy, which takes the version from the tag, and installs it back from Galaxy to check. It needs the `GALAXY_API_KEY` secret, which the libre-devops organisation provides. The import goes through Galaxy's API with [`scripts/galaxy-import.py`](./scripts/galaxy-import.py), not `ansible-galaxy role import`, because Galaxy namespaces cannot contain a hyphen: the role namespace is `libre_devops` and the GitHub organisation is `libre-devops`, which that command cannot handle. If the import fails, fix the cause and run the Release workflow by hand with the tag to import it again.

## Licence

[MIT](./LICENSE).
