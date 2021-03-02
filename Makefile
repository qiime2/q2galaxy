.PHONY: all lint test install dev clean distclean

PYTHON ?= python
PREFIX ?= $(CONDA_PREFIX)

all: ;

lint:
	flake8
	q2lint

stew: all
	q2galaxy template tests ./rendered/tests/

tools: all
	q2galaxy template all ./rendered/tools/

builtins: all
	q2galaxy template builtins ./rendered/tools/

test: stew
	planemo test --install_galaxy \
	  --galaxy_branch qiime2 \
	  --galaxy_source https://github.com/ebolyen/galaxy.git \
	  --no_conda_auto_install \
	  --test_output ./rendered/tests/tool_test_output.html \
	  --test_output_json ./rendered/tests/tool_test_output.json \
	  ./rendered/tests/suite_qiime2_mystery-stew/

install: all
	$(PYTHON) setup.py install

dev: all
	pip install -e .

clean: distclean
	rm -r ./rendered/tests/suite_*; \
	rm -r ./rendered/tools/suite_*

distclean: ;

