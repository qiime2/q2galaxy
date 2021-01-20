.PHONY: all lint test install dev clean distclean

PYTHON ?= python
PREFIX ?= $(CONDA_PREFIX)

all: ;

lint:
	flake8
	q2lint

stew: all
	q2galaxy template tests ./tests/

test: stew
	planemo test --install_galaxy \
	  --galaxy_branch qiime2 \
	  --galaxy_source https://github.com/ebolyen/galaxy.git \
	  --no_conda_auto_install \
	  --test_output ./tests/tool_test_output.html \
	  --test_output_json ./tests/tool_test_output.json \
	  ./tests/q2-mystery-stew/

install: all
	$(PYTHON) setup.py install

dev: all
	pip install -e .

clean: distclean

distclean: ;

