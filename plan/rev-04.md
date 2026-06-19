Rev 04 — macOS user LaunchAgent

Goal: run the Rev 03 poller in the background after user login so a GitHub issue labeled `agent-run` can be picked up by the Mac Studio without a foreground terminal.

Important constraints:

- Use a user LaunchAgent, not a root LaunchDaemon.
- Do not use sudo.
- Run as the logged-in user so `gh` auth is available.
- Keep Aider as the coding engine.
- Keep GitHub operations through `gh`.
- Do not auto-merge PRs.

Files added:

- `launchd/com.veer.agentic-pr.agent-test.plist.template`
- `bin/run-poller-launchd.sh`
- `bin/install-launchd.sh`
- `bin/uninstall-launchd.sh`
- `bin/service-status.sh`

Commands:

```sh
make install-service CONFIG=config/agent-test.env
make start-service
make status-service
make tail-service-logs
make stop-service
make uninstall-service
```

Acceptance test:

1. Run `make test`.
2. Run `plutil -lint launchd/com.veer.agentic-pr.agent-test.plist.template`.
3. Run `make install-service CONFIG=config/agent-test.env`.
4. Run `make start-service`.
5. Run `make status-service`.
6. Create a GitHub issue in `veerthiara/agent-test-local-ai` with label `agent-run`.
7. Confirm the service creates a PR and the issue moves to `agent-pr-created`.

Rollback:

```sh
make stop-service
make uninstall-service
```

Troubleshooting:

- Check `logs/launchd.out.log` for startup diagnostics and poller messages.
- Check `logs/launchd.err.log` for Python, `gh`, Aider, Ollama, or macOS permission failures.
- Run `make doctor CONFIG=config/agent-test.env` in a normal terminal to compare foreground behavior with launchd behavior.
- If the project in `Documents` is blocked by macOS privacy permissions, logs should show file access failures. A later revision may move the project to `~/Developer`.
- If the service restarts repeatedly, Rev 03 lock file protection should prevent overlapping poller work.
