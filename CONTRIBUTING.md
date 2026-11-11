# Contributing

Issues and pull requests are welcome. Open an issue first for anything large, so we can agree the approach before you write it.

## Set up

You need [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just) and [podman](https://podman.io/). Then:

```bash
just deps      # pinned Python tools and the test collections
just lint      # yamllint, ansible-lint (production profile), zizmor
just test default rhel9
```

`just` on its own lists every recipe.

## Rules

- Every variable is in `defaults/main.yml`, `meta/argument_specs.yml` and the README variables table, with the same default and description in all three.
- Internal variables start with `__standalone_package_installer_` and live in `vars/main.yml` or are registered in tasks.
- Anything that runs on the control node (`files/package_info.py`, delegated tasks) uses only the standard library and `ansible_playbook_python`.
- Use fully qualified module names, name every task, and keep `ansible-lint` on the production profile clean. A `noqa` needs a comment saying why.
- Tasks must be idempotent: `just test` runs an idempotence check on every platform.
- Never commit package files, real host names or internal URLs. Tests download what they install.
- Docs and comments are in British English.

## Commits and releases

Write commit subjects in the imperative, wrapped at 72 characters. Add an entry under Unreleased in `CHANGELOG.md`.

Maintainers release with `just release 1.2.3`, which tags and pushes. The Release workflow then creates the GitHub release and imports the tag into Galaxy.
