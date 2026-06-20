# AGENTS.md

## Project Direction

This repo is a local Aider + Ollama agent runner. Keep the implementation simple, explicit, and easy to evolve from a manual one-shot runner into a polling service later.

## Engineering Rules

- Keep orchestration in Python under `src/agentic_pr`.
- Keep `make` as the main human entrypoint.
- Keep GitHub operations behind `gh` CLI wrappers in `github_ops.py`.
- Keep git operations behind `git_ops.py`.
- Keep external command execution behind `command.py`.
- Do not add webhooks, Slack, Discord, or multi-repo behavior until the relevant revision asks for it.
- Prefer small modules with clear responsibilities over large all-in-one files.
- Tests must not call GitHub, Aider, Ollama, or real remotes.

## Commit Messages

When committing changes for a revision, use this format:

```text
REV01: short imperative message
REV02: short imperative message
REV03: short imperative message
REV04: short imperative message
REV05: short imperative message
```

Use the current revision prefix for agent-created commits. For this revision, use `REV05: <some message>`.
