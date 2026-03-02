# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

SPHINXAPIDOC ?= sphinx-apidoc

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile apidoc checkdocstrings

apidoc:
	@$(SPHINXAPIDOC) -o "$(SOURCEDIR)" -e --no-toc -f ../ifsbench

# Check docstrings for Sphinx compatibility
# This target builds documentation with nitpicky mode enabled and reports all warnings
checkdocstrings: apidoc
	@echo "Checking docstrings for Sphinx compatibility..."
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" -n -W --keep-going $(SPHINXOPTS) $(O) 2>&1 | tee checkdocstrings.log || true
	@echo ""
	@echo "Docstring check complete. See checkdocstrings.log for details."
	@if grep -q "WARNING:" checkdocstrings.log; then \
		echo "Found warnings in docstrings. Review the log above."; \
		exit 1; \
	else \
		echo "All docstrings are Sphinx compatible!"; \
	fi

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile apidoc
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
