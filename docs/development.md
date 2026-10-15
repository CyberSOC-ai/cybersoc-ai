# Development setup

This guide covers the S1-T01 development environment and checks. Start commands from the repository root. The current container provides Python tools; it does not start the application or SOC lab.

## 1. Prerequisites

Install Git and Docker with Compose. Start Docker before continuing. Linux can use Docker Engine with the Compose plugin; Windows uses Docker Desktop with WSL 2. The commands below are verified on Linux x86_64; other platforms still need team validation.

```sh
git --version
docker info
docker compose version
```

These commands check Git, the running Docker engine and Compose respectively. Internet access is needed to download images and packages during the first build.

## 2. Get the project

```sh
git clone https://github.com/CyberSOC-ai/cybersoc-ai.git
cd cybersoc-ai
```

If you already cloned the project, open its existing folder instead. Until the S1-T01 PR merges, check out `feature/9-reproducible-local-environment` after that branch is published.

## 3. Build the development image

```sh
docker compose build dev
docker compose run --rm dev
```

The first command builds the toolbox from [Dockerfile.dev](../infrastructure/docker/Dockerfile.dev). The second runs its default command: expect `Python 3.12.x`. `--rm` removes the container after it exits; the image remains available. Commands run as the regular `dev` user.

Python 3.12 is recorded in [.python-version](../.python-version). Node.js 24 is recorded in [.nvmrc](../.nvmrc) for future frontend work; Node is not included in this Python image. No local Python installation or virtual environment is required for these Docker checks.

## 4. Run the checks

```sh
docker compose run --rm -T dev ruff check --no-cache .
docker compose run --rm -T dev python -B -m unittest discover -s tests/contracts -v
```

Run the commands in order. Ruff reports common Python mistakes without editing files; expect `All checks passed!`. The second command runs the contract tests; the current suite has 17 test methods and should finish with `OK`.

| Option | Meaning |
|---|---|
| `-T` | Disable the interactive terminal, matching CI usage |
| `--no-cache` | Keep Ruff from writing cache files into the read-only project mount |
| `-B` | Keep Python from writing bytecode files |
| `-m unittest discover` | Find and run tests using Python's built-in test framework |
| `-s tests/contracts` | Look for tests in this directory |
| `-v` | Show individual test names and results |

## 5. Changes and rebuilding

Compose mounts your project at `/workspace` read-only. Source edits are visible on the next run without rebuilding. Rebuild after changing [requirements.txt](../requirements.txt) or the Dockerfile.

The root requirements file records exact Python package versions, including supporting libraries. Review dependency updates in a clean Docker environment and rerun the checks. The base image tag selects the Python 3.12 family and can receive updates; it is not an immutable image pin. Deliberately refresh it with `docker compose build --pull dev`, then rerun the checks.

[.dockerignore](../.dockerignore) limits build inputs to the Dockerfile and dependency list. It does not filter the runtime bind mount: local files such as `.env` remain readable to container processes through that mount.

## 6. Configuration and secrets

[.env.example](../.env.example) is a shared template. The current checks need no environment variables, so there is no need to create `.env`. Future services must document their settings and receive only the secrets they need. Keep real credentials out of code, images, examples and reports; follow the [security policy](../security/README.md).

Before committing, review staged changes and scan them using an installed [Gitleaks CLI](https://github.com/gitleaks/gitleaks#installing):

```sh
gitleaks git --pre-commit --staged --redact --no-banner .
```

This checks staged changes only; stage intended files before scanning. The CLI is separate from the Python image. `--redact` hides suspected secret values. If a real credential was exposed, revoke/rotate it and remove the exposure; deleting a line alone does not invalidate a credential.

## 7. GitHub Actions

The [CI workflow](../.github/workflows/ci.yml) runs on pull requests and pushes to `main`. It checks secrets and repository integrity, builds the development image, then runs the same Ruff and test commands shown above. Repository integrity checks local Markdown file links and unresolved merge-conflict markers.

The Gitleaks Action reads the repository secret `GITLEAKS_LICENSE`; a maintainer must configure it in GitHub's Actions secrets settings. `GITHUB_TOKEN` is provided automatically. Neither value belongs in `.env` for these checks. Automatic PR comments are disabled. Hosted CI is separate evidence from a local successful run.

## 8. Troubleshooting and cleanup

| Problem | What to check |
|---|---|
| Cannot connect to Docker | Start Docker and confirm `docker info` works |
| Permission denied on Docker socket | Follow your platform's Docker access setup; ask the machine owner rather than changing socket permissions broadly |
| Package missing or old version | Rebuild `dev` after changing requirements |
| Ruff cache or Python bytecode write error | Use the documented `--no-cache` and `-B` options |
| Project file cannot be read | Check Docker file-sharing settings and file/directory permissions; the container runs with user ID 1000 |
| First build cannot download dependencies | Check Internet/proxy access to the image registry and package index |
| Gitleaks Action reports a license problem | Confirm `GITLEAKS_LICENSE` is available to this repository and workflow |

The check containers exit after each command and are removed by `--rm`. Run `docker compose down` to remove the project's Compose network. Avoid broad Docker cleanup commands that could delete other projects' resources.
