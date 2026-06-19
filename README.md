# agentic-pr

Local one-shot GitHub issue runner for an Aider + Ollama workflow.

Rev 02 uses a small Python CLI while keeping `make` as the entrypoint. GitHub operations still go through the `gh` CLI, and code generation still runs Aider as an external command.

## Requirements

- Python 3.11+
- `git`
- `gh`, authenticated against the target repository
- `aider`
- Ollama running the configured model

## Setup

Edit `config/agent-test.env` and set `OWNER_REPO` to the GitHub repository, for example `octocat/hello-world`.

Then check the local environment:

```sh
make doctor CONFIG=config/agent-test.env
```

Create the GitHub labels if needed:

```sh
make ensure-labels CONFIG=config/agent-test.env
```

## Run Once

Create or pick a GitHub issue, add the `agent-run` label, then run:

```sh
make run-once CONFIG=config/agent-test.env
```

Expected flow:

1. Find one open issue with `agent-run`.
2. Move it to `agent-running`.
3. Update the base branch and create `agent/issue-<number>-<timestamp>`.
4. Run Aider with the configured Ollama model.
5. Commit with a `REV02:` commit message and push the branch.
6. Open a PR.
7. Comment on the issue with the PR URL.
8. Replace `agent-running` with `agent-pr-created`.

## Test

```sh
make test
```

The tests cover local Python helpers and do not call GitHub, Aider, or Ollama.
