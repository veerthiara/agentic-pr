CONFIG ?= config/agent-test.env
PYTHON ?= python3
PYTHONPATH := src

.PHONY: doctor ensure-labels run-once poll install-service start-service stop-service restart-service status-service uninstall-service tail-service-logs test

doctor:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli doctor --config $(CONFIG)

ensure-labels:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli ensure-labels --config $(CONFIG)

run-once:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli run-once --config $(CONFIG)

poll:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli poll --config $(CONFIG)

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
