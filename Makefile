CONFIG ?= config/agent-test.env
PYTHON ?= python3
PYTHONPATH := src

.PHONY: doctor ensure-labels run-once poll test

doctor:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli doctor --config $(CONFIG)

ensure-labels:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli ensure-labels --config $(CONFIG)

run-once:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli run-once --config $(CONFIG)

poll:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentic_pr.cli poll --config $(CONFIG)

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests
