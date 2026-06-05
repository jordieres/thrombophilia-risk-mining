SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = ../docs
DOCTREEDIR    = .doctrees

html:
	$(SPHINXBUILD) -d $(DOCTREEDIR) -b html $(SOURCEDIR) $(BUILDDIR)

clean:
	rm -rf $(DOCTREEDIR) $(BUILDDIR)
