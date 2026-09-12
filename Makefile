BOOTSTRAP_PYTHON ?= python3
VENV             := .venv
PYTHON           := $(VENV)/bin/python
DEPS             := $(VENV)/.installed
REGISTRY         ?= localhost
SDK_IMAGE        ?= $(REGISTRY)/geotriage/sdk:0.1
BASE_ARG          = --build-arg BASE=$(SDK_IMAGE)

.DEFAULT_GOAL := help
.PHONY: help venv install test fmt fmt-check check image builtins build clean

help:  ## print this help
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(PYTHON):
	$(BOOTSTRAP_PYTHON) -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip

$(DEPS): $(PYTHON) pyproject.toml
	$(PYTHON) -m pip install -e '.[dev,test]'
	@touch $(DEPS)

venv: $(PYTHON)  ## create .venv if missing

install: $(DEPS)  ## install the contract with its dev and test extras

test: $(DEPS)  ## run the test suite
	$(PYTHON) -m pytest

fmt: $(DEPS)  ## format with black
	$(PYTHON) -m black geotriage tests examples templates

fmt-check: $(DEPS)  ## check formatting without changing anything
	$(PYTHON) -m black --check geotriage tests examples templates

check: fmt-check test  ## everything CI would run

image:  ## build the base image authors build FROM
	docker build -t $(SDK_IMAGE) .

builtins: image  ## build the four images the platform registers as its defaults
	docker build -q $(BASE_ARG) -t $(REGISTRY)/geotriage/ndwi-water:0.1 \
		-f examples/models/Dockerfile.ndwi examples/models
	docker build -q $(BASE_ARG) -t $(REGISTRY)/geotriage/lst:0.1 \
		-f examples/models/Dockerfile.lst examples/models
	docker build -q $(BASE_ARG) -t $(REGISTRY)/geotriage/earth-search:0.1 \
		-f examples/providers/Dockerfile.earthsearch examples/providers
	docker build -q $(BASE_ARG) -t $(REGISTRY)/geotriage/planetary-computer:0.1 \
		-f examples/providers/Dockerfile.planetarycomputer examples/providers
	@echo "built under $(REGISTRY)/geotriage/ : ndwi-water, lst, earth-search, planetary-computer"

build: $(DEPS)  ## build a wheel and an sdist into dist/
	$(PYTHON) -m pip install --quiet build
	$(PYTHON) -m build

clean:  ## remove the venv, caches and build artifacts (leaves docker alone)
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.egg-info' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(VENV) .pytest_cache dist build
