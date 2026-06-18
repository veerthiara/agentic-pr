Rev 1 — Manual one-shot issue runner

Purpose: prove the current script works.

You manually run:

make run-once

Expected result:

GitHub issue with agent-run label → branch → commit → PR

Files:

agentic-pr/
├── README.md
├── Makefile
├── config/
│   └── agent-test.env.example
├── bin/
│   └── run-agent-issue.sh
└── logs/

Acceptance test:

Create GitHub issue from browser/app.
Add label agent-run.
Run make run-once.
GitHub PR appears.
Issue label changes from agent-run to agent-pr-created.