# Libre DevOps Ansible role libre_devops.standalone_package_installer. Run `just` to list the recipes.
#
# CI runs these same recipes, so a local run shows what CI will do. You need uv
# (https://docs.astral.sh/uv/) and podman. Install just with `uv tool install rust-just`
# or `brew install just`.

set shell := ["bash", "-euo", "pipefail", "-c"]

role := "libre_devops.standalone_package_installer"
github_owner := "libre-devops"
github_repo := "ansible-role-standalone-package-installer"

# Prefix of the Molecule container names, so tests of different roles can run side by side.
platform_prefix := "spi-"

# List the recipes.
default:
    @just --list

# Install the pinned Python tools and the collections the tests use.
deps:
    uv sync --locked
    uv run ansible-galaxy collection install -r requirements.yml -p .ansible/collections

# Lint the YAML, the role (ansible-lint, production profile) and the workflows (zizmor).
lint: deps
    uv run yamllint .
    uv run ansible-lint
    uv run zizmor --offline .github/workflows

# List the Molecule platforms.
platforms:
    @uv run --quiet python -c "import yaml; print('\n'.join(p['name'].removeprefix('{{ platform_prefix }}') for p in yaml.safe_load(open('.config/molecule/config.yml'))['platforms']))"

# List the Molecule scenarios.
scenarios:
    @find molecule -mindepth 2 -maxdepth 2 -name molecule.yml -printf '%h\n' | xargs -n1 basename | sort

# Run one scenario on one platform, or on every platform: just test default rhel9
test scenario="default" platform="": deps
    if [ -n '{{ platform }}' ]; then \
        uv run molecule test -s '{{ scenario }}' --platform-name '{{ platform_prefix }}{{ platform }}'; \
    else \
        for p in $(just platforms); do uv run molecule test -s '{{ scenario }}' --platform-name '{{ platform_prefix }}'"$p"; done; \
    fi

# Run every scenario on every platform, one at a time. Slow: CI runs these in parallel.
test-all: deps
    for s in $(just scenarios); do just test "$s"; done

# Run a scenario on one platform and leave the instance running, pass or fail: just converge default debian12
# (molecule converge cannot pick a platform, so this runs the whole test and skips the destroy)
converge scenario platform: deps
    uv run molecule test -s '{{ scenario }}' --platform-name '{{ platform_prefix }}{{ platform }}' --destroy never

# Open a shell in a running instance: just login default debian12
login scenario platform:
    uv run molecule login -s '{{ scenario }}' --host '{{ platform_prefix }}{{ platform }}'

# Remove the instances of a scenario.
destroy scenario="default":
    uv run molecule destroy -s '{{ scenario }}'

# Run the example playbook against real hosts, checks included: just live inventory.ini -e @vars.yml
live inventory *args: deps
    uv run ansible-playbook -i '{{ inventory }}' examples/playbook.yml {{ args }}

# Scan the full git history for secrets (needs gitleaks on PATH).
secrets:
    gitleaks git --redact --verbose .

# Tag a release and push the tag. CI then imports it into Galaxy: just release 1.0.0
release version:
    [[ '{{ version }}' =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "version must be semver, for example 1.0.0" >&2; exit 1; }
    git tag -a '{{ version }}' -m 'Release {{ version }}'
    git push origin '{{ version }}'

# scripts/galaxy-import.py says why this does not use `ansible-galaxy role import`.
# Import a release tag into Galaxy, then install it from Galaxy to check (needs GALAXY_API_KEY): just galaxy-import 1.0.0
galaxy-import tag:
    [[ '{{ tag }}' =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "tag must be semver, for example 1.0.0" >&2; exit 1; }
    uv run --no-project python scripts/galaxy-import.py '{{ role }}' '{{ github_owner }}' '{{ github_repo }}' '{{ tag }}'
    dir="$(mktemp -d)" && trap 'rm -rf "$dir"' EXIT && uv run ansible-galaxy role install --roles-path "$dir" '{{ role }},{{ tag }}'
