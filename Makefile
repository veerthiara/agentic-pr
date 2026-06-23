CONFIG ?= config/agent-test.env
PYTHON ?= python3
PYTHONPATH := src

.PHONY: doctor ensure-labels run-once run-followup-once poll list-runs show-last-run ci-summary install-service start-service stop-service restart-service status-service uninstall-service tail-service-logs test health list-runs show-last-run show-run cleanup-dry-run cleanup list-configs doctor-all health-all config-path

doctor:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli doctor --config $(CONFIG)

ensure-labels:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli ensure-labels --config $(CONFIG)

run-once:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli run-once --config $(CONFIG)

run-followup-once:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli run-followup-once --config $(CONFIG)

poll:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli poll --config $(CONFIG)

list-runs:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli list-runs --config $(CONFIG)

show-last-run:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli show-last-run --config $(CONFIG)

show-run:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli show-run --config $(CONFIG) --run-id $(RUN_ID)

ci-summary:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli ci-summary --config $(CONFIG) --pr $(PR)

health:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli health --config $(CONFIG)

cleanup-dry-run:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli cleanup --config $(CONFIG) --dry-run

cleanup:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli cleanup --config $(CONFIG) --apply

install-service:
	bin/install-launchd.sh $(CONFIG)

start-service:
	launchctl enable gui/$$(id -u)/com.veer.agentic-pr.agent-test
	launchctl kickstart -k gui/$$(id -u)/com.veer.agentic-pr.agent-test

stop-service:
	launchctl disable gui/$$(id -u)/com.veer.agentic-pr.agent-test
	launchctl kill TERM gui/$$(id -u)/com.veer.agentic-pr.agent-test

restart-service:
	$(MAKE) stop-service || true
	$(MAKE) start-service

status-service:
	bin/service-status.sh

uninstall-service:
	bin/uninstall-launchd.sh

tail-service-logs:
	tail -f logs/launchd.out.log logs/launchd.err.log

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests

# Rev 12: Multi-repo config registry
list-configs:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli list-configs

doctor-all:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli doctor-all

health-all:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli health-all

config-path:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli config-path --repo $(REPO)
