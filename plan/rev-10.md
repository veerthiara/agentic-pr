# REV10: Repo Instructions + Project Memory

## Goal
Add support for repo-local `.agentic-pr/` instructions, giving the agent project-specific memory. This allows the agent to understand repo-specific testing rules, architecture, and examples without hardcoding them into the main agent logic.

## Design

### 1. `src/agentic_pr/repo_instructions.py`
A new module responsible for safely loading repo instructions:
- Parses `instructions.md`, `safety.md`, `examples.md`, and `commands.env` from `.agentic-pr/`.
- Limits file reads to `MAX_BYTES` to avoid exploding the context window.
- Fails gracefully if files or directories are missing.

### 2. `config.py`
- Added config flags `ENABLE_REPO_INSTRUCTIONS`, `REPO_INSTRUCTIONS_DIR`, and `REPO_INSTRUCTIONS_MAX_BYTES`.
- The agent merges `commands.env` values (`TEST_CMD`, `LINT_CMD`) if the main config explicitly doesn't provide them. The main config takes precedence.
- `AgentConfig` now holds a reference to `RepoInstructions` if enabled.

### 3. Prompt Builder and Planner
- The planner prompt includes repo instructions (instructions, safety, examples) when available.
- The Aider implementation prompt and follow-up prompts also include repo instructions.
- Test and lint commands from the repo instructions are clearly highlighted in the prompts so Aider can follow the project's testing methodology.

### 4. Run Records and Preflight
- The `RunRecord` tracks if repo instructions were enabled, what files were found, and the source of the test/lint commands.
- `preflight.py` checks for the presence of `.agentic-pr/safety.md` and mentions it in the success output if found.

## Impact
Real repositories often have unwritten (or written) rules about where to put files, how to run tests, and what directories to avoid. `REV10` empowers the local AI agent to become an integrated team member by reading the same `.agentic-pr/` rulebook that human developers can define for their specific projects.
