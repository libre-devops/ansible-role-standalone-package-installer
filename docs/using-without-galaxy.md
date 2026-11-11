# Using libre_devops.standalone_package_installer without Galaxy

You do not need Ansible Galaxy, or even the `ansible-galaxy` command, to use this role. A role is a directory: Ansible looks for `libre_devops.standalone_package_installer` in a `roles/` directory next to your playbook, then in each directory on `roles_path`. Getting the directory there is the whole job, from GitHub or from a copy inside your own network.

> **Tested:** methods 1 to 3, the offline collections and the git server copy were run on 11 November 2026 with ansible-core 2.16 and 2.21 while Galaxy was unreachable, using `libre_devops.mde_linux` 1.0.0. The steps are the same for every libre_devops role. The AWX, Automation Controller, execution environment and automation hub notes follow those products' documentation and were not tested here.

## Contents

- [Before you start](#before-you-start)
- [Choose a method](#choose-a-method)
- [Method 1: clone it with git](#method-1-clone-it-with-git)
- [Method 2: unpack a release archive](#method-2-unpack-a-release-archive)
- [Method 3: a requirements file](#method-3-a-requirements-file)
- [Collections](#collections)
- [Publishing it inside your organisation](#publishing-it-inside-your-organisation)
- [Checking what you install](#checking-what-you-install)
- [Python and ansible-core versions](#python-and-ansible-core-versions)

## Before you start

**Pick a release.** Releases are git tags such as `1.0.0`, listed on the [releases page](https://github.com/libre-devops/ansible-role-standalone-package-installer/releases). Pin one. `main` is where changes land before they are released.

**Keep the name.** The README and every example call the role `libre_devops.standalone_package_installer`, so the directory must have that name: `roles/libre_devops.standalone_package_installer`. If you give it another name, use that name in your playbooks instead, including in any `include_role`.

## Choose a method

| Method | Needs on the control node | Good for |
|---|---|---|
| [1. Clone it with git](#method-1-clone-it-with-git) | `git` | Keeping the role in your playbook repository as a submodule, or updating with `git`. |
| [2. Unpack a release archive](#method-2-unpack-a-release-archive) | `curl` (or a browser) and `tar` | Control nodes without `git`, and carrying the role into a network with no internet access. |
| [3. A requirements file](#method-3-a-requirements-file) | `ansible-galaxy`, which comes with ansible-core | Installing several roles and collections in one step, from GitHub or your own servers, as CI, AWX, Automation Controller and execution environment builds do. It never contacts Galaxy for an entry that names its own source. |

## Method 1: clone it with git

```bash
mkdir -p roles
git clone --branch 1.0.0 https://github.com/libre-devops/ansible-role-standalone-package-installer.git roles/libre_devops.standalone_package_installer
```

`--branch` takes a tag too. Git says the checkout is a detached HEAD, which is what you want for a fixed release. To move to a later release:

```bash
git -C roles/libre_devops.standalone_package_installer fetch --tags
git -C roles/libre_devops.standalone_package_installer checkout 1.1.0
```

If your playbooks are in a git repository, a submodule records the exact commit in it, so everyone who clones the repository gets the same role:

```bash
git submodule add https://github.com/libre-devops/ansible-role-standalone-package-installer.git roles/libre_devops.standalone_package_installer
git -C roles/libre_devops.standalone_package_installer checkout 1.0.0
git add .gitmodules roles/libre_devops.standalone_package_installer
git commit -m "Add libre_devops.standalone_package_installer 1.0.0"
```

Anyone who clones your repository then runs `git submodule update --init`.

## Method 2: unpack a release archive

GitHub serves every release tag as an archive. No `git` is needed, and the file can be copied anywhere.

```bash
curl -fsSL -o ansible-role-standalone-package-installer-1.0.0.tar.gz https://github.com/libre-devops/ansible-role-standalone-package-installer/archive/refs/tags/1.0.0.tar.gz
sha256sum ansible-role-standalone-package-installer-1.0.0.tar.gz
mkdir -p roles/libre_devops.standalone_package_installer
tar -xzf ansible-role-standalone-package-installer-1.0.0.tar.gz --strip-components=1 -C roles/libre_devops.standalone_package_installer
```

Keep the SHA-256 from the first download and compare it whenever you install the same file again. `--strip-components=1` drops the archive's top directory, which is named after the repository and version, so the files land straight in the role's directory. To update, delete the directory and unpack the new release.

## Method 3: a requirements file

`ansible-galaxy` ships with ansible-core. Despite its name, it only contacts Galaxy for an entry that is just a name. Give each entry a source and it fetches from there:

```yaml
---
roles:
  # From GitHub, or from your own git server (see Publishing it inside your organisation).
  - name: libre_devops.standalone_package_installer
    src: https://github.com/libre-devops/ansible-role-standalone-package-installer.git
    scm: git
    version: 1.0.0

  # Or from an archive on any HTTPS server, such as an artifact store:
  # - name: libre_devops.standalone_package_installer
  #   src: https://artifacts.example.internal/ansible/ansible-role-standalone-package-installer-1.0.0.tar.gz
```

```bash
ansible-galaxy role install -r requirements.yml -p roles
```

Add `--force` after changing `version`, or the copy already installed stays. With `scm: git`, `version` also takes a full commit hash, the strictest pin there is.

## Collections

This role needs:

| Collection | When |
|---|---|
| `community.general` | On SUSE hosts only, where packages install with `community.general.zypper`. |

The `ansible` package (as opposed to `ansible-core` alone) already includes `ansible.posix` and `community.general`.

Without Galaxy, get collections one of these ways:

- **From your own automation hub.** Red Hat's private automation hub, or a galaxy_ng server, hosts collections. List it under `[galaxy] server_list` in `ansible.cfg`, as its documentation describes, and `ansible-galaxy collection install` uses it instead of Galaxy.
- **With no server at all.** Download the collections once on a machine that can reach Galaxy, and carry the files across:

  ```bash
  # On a machine that can reach Galaxy
  ansible-galaxy collection download community.general -p collections-offline

  # Copy collections-offline/ to the control node, then
  cd collections-offline
  ansible-galaxy collection install -r requirements.yml
  ```

  `download` also fetches the collections they depend on, and writes a `requirements.yml` beside the archives that installs from those files. Add a version to pin one, such as `ansible.posix:2.2.2`.

## Publishing it inside your organisation

### On your own git server

Copy the repository with its tags, then point method 1 or 3 at your copy:

```bash
git clone --bare https://github.com/libre-devops/ansible-role-standalone-package-installer.git
cd ansible-role-standalone-package-installer.git
git push --all https://git.example.internal/ansible/ansible-role-standalone-package-installer.git
git push --tags https://git.example.internal/ansible/ansible-role-standalone-package-installer.git
```

To pick up new releases later, run in the same directory:

```bash
git fetch --prune --tags origin '+refs/heads/*:refs/heads/*'
git push --all https://git.example.internal/ansible/ansible-role-standalone-package-installer.git
git push --tags https://git.example.internal/ansible/ansible-role-standalone-package-installer.git
```

Run that on a schedule, or use your git server's own pull mirroring where it has one. Your requirements file then names your server:

```yaml
roles:
  - name: libre_devops.standalone_package_installer
    src: https://git.example.internal/ansible/ansible-role-standalone-package-installer.git
    scm: git
    version: 1.0.0
```

### As an archive in an artifact store

Download the release archive and record its SHA-256 as in [method 2](#method-2-unpack-a-release-archive), then upload it to anything that serves files over HTTPS: a generic repository in Artifactory or Nexus, or an internal web server. Install it with method 2 from your URL, or with the archive form of [method 3](#method-3-a-requirements-file).

### Private automation hub cannot hold it

Red Hat's private automation hub holds collections and execution environments, not standalone roles like this one. Keep the role on a git server or in an artifact store, and use the hub for the collections.

### AWX and Automation Controller

When they sync a project, AWX and Automation Controller install the roles listed in the project's `roles/requirements.yml`, from the sources it names. Point those at your git server or artifact store. Or commit the role into the project's `roles/` directory with method 1 or 2, and nothing is fetched at all.

### Execution environments

`ansible-builder` installs the roles and collections in the requirements file that the definition names under `dependencies.galaxy`, from the sources that file gives. Use the same requirements file as method 3.

## Checking what you install

- **Pin the commit, not only the tag.** This shows the commit a release tag points at:

  ```bash
  git ls-remote https://github.com/libre-devops/ansible-role-standalone-package-installer.git refs/tags/1.0.0
  ```

  Use that hash as `version` in a requirements file, or with `git checkout` in method 1, and the role cannot change under you.
- **Signed commits.** Every commit on `main` is signed, and GitHub shows it as Verified.
- **Archives.** Compare the SHA-256 you recorded every time you install an archive.

## Python and ansible-core versions

### On the control node

`ansible --version` shows both: the first line is the ansible-core version, and `python version` is the Python that ansible-core itself runs on, on the control node. That is not your servers' Python.

This role needs ansible-core 2.16 or later. Distribution packages are often older, and older still on long-lived control nodes, such as Ansible 2.9. A current ansible-core can sit beside them without touching the system's Python:

```bash
python3.12 -m venv ~/ansible
~/ansible/bin/pip install ansible-core
~/ansible/bin/ansible --version
```

RHEL 8 and RHEL 9 both have `python3.12` in AppStream (`dnf install python3.12`).

### On managed nodes

ansible-core runs its modules with the Python on each managed node, and each release drops older versions of Python:

| ansible-core | Oldest Python it can run modules with |
|---|---|
| 2.16 (out of support since May 2025) | 3.6 |
| 2.17 | 3.7 |
| 2.18 and 2.19 | 3.8 |
| 2.20 to 2.22 | 3.9 |

| Distribution | Its own Python | With a current ansible-core |
|---|---|---|
| RHEL 8 and its rebuilds | 3.6 (`/usr/libexec/platform-python`) | Does not work until you add a newer Python. |
| RHEL 9 and its rebuilds | 3.9 | Works. |
| RHEL 10 and its rebuilds | 3.12 | Works. |
| SLES 15 | 3.6 | Does not work until you add a newer Python. |
| Debian 12 and 13, Ubuntu 24.04 and later | 3.11 or later | Works. |

With ansible-core 2.17 or later, a RHEL 8 host fails on its first task, usually Gathering Facts, before this role runs at all. The message is `The module interpreter '/usr/bin/python3' was not found`, because RHEL 8 has no `/usr/bin/python3` unless you install one. Pointing `ansible_python_interpreter` at `/usr/libexec/platform-python` gives `Module result deserialization failed` instead. Every module fails the same way, not only this role's.

There are three ways round it.

**Use [libre_devops.python](https://github.com/libre-devops/ansible-role-python) (recommended).** It finds or installs a Python the running ansible-core accepts, from the host's repositories (Satellite included), package files pushed from the control node, or a self-contained build, and sets `ansible_python_interpreter` for the rest of the run. Put it first in the same play, with `gather_facts: false`:

```yaml
- name: This role on RHEL 8
  hosts: rhel8
  become: true
  # Gathering facts would fail on Python 3.6. libre_devops.python gathers them
  # once it has installed Python 3.12.
  gather_facts: false
  roles:
    - role: libre_devops.python
    - role: libre_devops.standalone_package_installer
```

The README's [RHEL 8 hosts with only Python 3.6](../README.md#rhel-8-hosts-with-only-python-36) example has the requirements file and this role's variables.

**Or install one with a play of your own.** `raw` runs a plain command and needs no Python on the host, so it can install one:

```yaml
---
- name: Give RHEL 8 hosts a Python that current ansible-core supports
  hosts: rhel8
  become: true
  gather_facts: false
  tasks:
    - name: Install Python 3.12 from AppStream
      ansible.builtin.raw: test -x /usr/bin/python3.12 || dnf -y install python3.12
      args:
        executable: /bin/sh
      register: bootstrap_python
      changed_when: "'Installed:' in bootstrap_python.stdout"
```

Then tell Ansible to use it, for example in `group_vars/rhel8.yml`:

```yaml
ansible_python_interpreter: /usr/bin/python3.12
```

On SLES 15, install `python311` (`zypper --non-interactive install python311`) and use `/usr/bin/python3.11`.

**Or run ansible-core 2.16 on the control node.** It is the last release that can manage Python 3.6, but it has had no fixes, security ones included, since May 2025:

```bash
python3.12 -m venv ~/ansible-2.16
~/ansible-2.16/bin/pip install 'ansible-core>=2.16,<2.17'
```

This role's CI tests current ansible-core only, not 2.16, so prefer the first way.
