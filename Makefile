.PHONY: all lint test install dev clean distclean

PYTHON ?= python
PREFIX ?= $(CONDA_PREFIX)

all: ;

lint: stew
	flake8
	q2lint

planemo-lint: clean stew tools
	planemo lint ./rendered/tests/suite_* --fail_level warn
	planemo lint ./rendered/tools/suite_* --fail_level error

stew: all
	q2galaxy template tests ./rendered/tests/

tools: all
	q2galaxy template all ./rendered/tools/ --distro core --metapackage qiime2-core

builtins: all
	q2galaxy template builtins ./rendered/tools/ --distro core --metapackage qiime2-core

test: stew
	planemo test --install_galaxy \
	  --galaxy_branch release_22.05 \
	  --galaxy_source https://github.com/galaxyproject/galaxy.git \
	  --no_conda_auto_install \
	  --no_conda_auto_init \
	  --test_output ./rendered/tests/tool_test_output.html \
	  --test_output_json ./rendered/tests/tool_test_output.json \
	  ./rendered/tests/suite_qiime2__mystery_stew/

serve: tools
	planemo serve --install_galaxy \
	  --galaxy_branch release_22.05 \
	  --galaxy_source https://github.com/galaxyproject/galaxy.git \
	  --no_conda_auto_install \
	  --no_conda_auto_init \
	  ./rendered/tools/

install: all
	$(PYTHON) setup.py install

dev: all
	pip install -e .

clean: distclean
	rm -rf ./rendered/tests/suite_*; \
	rm -rf ./rendered/tools/suite_*

distclean: ;
