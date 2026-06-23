# Rev 12: Multi-Repo Config Registry

## Goal
Add multi-repo config registry support while keeping existing single-config commands working.

## Files Changed

### New Files
- `config/repos/agent-test.env` - Moved from config/agent-test.env
- `config/repos.example/repo.env.example` - Template with all config keys
- `src/agentic_pr/config_registry.py` - Config discovery and parsing
- `tests/test_config_registry.py` - Unit tests
- `plan/rev-12.md` - This file

### Modified Files
- `src/agentic_pr/cli.py` - Added list-configs, doctor-all, health-all, config-path commands
- `Makefile` - Added list-configs, doctor-all, health-all, config-path targets
- `README.md` - Added Rev 12 documentation section

## Commands Added

### CLI Commands
```bash
python -m agentic_pr.cli list-configs [--include-disabled]
python -m agentic_pr.cli doctor-all [--include-disabled]
python -m agentic_pr.cli health-all [--include-disabled]
python -m agentic_pr.cli config-path --repo <name>
```

### Makefile Targets
```bash
make list-configs
make doctor-all
make health-all
make config-path REPO=<name>
```

## Acceptance Tests

1. **Run tests:**
   ```bash
   make test
   ```

2. **List configs:**
   ```bash
   make list-configs
   ```
   Expected: Shows agent-test config with name, owner_repo, repo_path, base_branch, enabled

3. **Doctor all:**
   ```bash
   make doctor-all
   ```
   Expected: Runs doctor for enabled configs, prints compact result per config

4. **Health all:**
   ```bash
   make health-all
   ```
   Expected: Shows health for enabled configs

5. **Backward compatibility:**
   ```bash
   make doctor CONFIG=config/agent-test.env
   make doctor CONFIG=config/repos/agent-test.env
   ```
   Expected: Both work identically

## Migration Notes

- Existing `config/agent-test.env` is kept for backward compatibility
- New configs should be placed in `config/repos/<name>.env`
- Each repo should have separate directories for:
  - `LOG_DIR`
  - `RUN_DIR`
  - `RUN_RECORD_DIR`
  - `LOCK_FILE`
  - `COMMENT_STATE_DIR`
- Or use shared folders with repo-safe filenames

## Rollback Notes

To rollback:
1. Remove `config/repos/` and `config/repos.example/`
2. Revert `src/agentic_pr/cli.py` to previous version
3. Revert `Makefile` to previous version
4. Remove `src/agentic_pr/config_registry.py`
5. Remove `tests/test_config_registry.py`
6. Remove Rev 12 section from README.md

## Important Notes

- Rev 12 is a separate commit from Rev 11
- Does not add poll-all background service (left for future revision)
- Does not auto-enable launchd per repo
- Does not change core agent behavior
- Does not add new coding engines