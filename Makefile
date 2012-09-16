CHANGELOG_FILENAME="debian.upstream/changelog"
CHANGELOG := ${CHANGELOG_FILENAME}
PREFIX ?= /usr/ # default: /usr/local
PYTHON=python
PYTHON3=python3

all: build

clean: clean-doc clean-lolram clean-lolram3
	rm -R -f html
	rm -R -f html3

build: build-doc build-lolram build-lolram3

install: install-doc install-lolram  install-lolram3

clean-doc:

build-doc:
#	epydoc src/py2/lolram* -o html
	# TODO: epydoc python3 support not yet available 
	#	epydoc src/py3/lolram* -o html3

install-doc:

clean-lolram:
	find src/py2/ -name '*.py[co]' -delete
	find src/py2/ -name '*~' -delete

build-lolram:
	$(PYTHON) setup2.py build

install-lolram:
	$(PYTHON) setup2.py install --prefix $(DESTDIR)/$(PREFIX)

clean-lolram3:
	find src/py3/ -type d -name '__pycache__' -exec rm -r {} +
	find src/py3 -name '*~' -delete

build-lolram3:
	$(PYTHON3) setup3.py build

install-lolram3:
	$(PYTHON3) setup3.py install --prefix $(DESTDIR)/$(PREFIX)

deb-package: make-auto-changelog
	ln -s -T debian.upstream debian || true
	debuild -b -uc -us

MESSAGE="Scripted build. Revision `(bzr nick && bzr revno) || (git name-rev --name-only HEAD && git rev-parse HEAD)`"
make-auto-changelog:
	rm -f ${CHANGELOG_FILENAME}
	debchange --changelog ${CHANGELOG_FILENAME} --preserve \
		--newversion `$(PYTHON3) setup3.py --version`-upstream`date --utc "+%Y%m%d%H%M%S"` \
		--distribution UNRELEASED --force-distribution \
		--create ${MESSAGE} --package lolram

deb-clean-packages:
	rm ../python-lolram_*.deb
	rm ../python3-lolram_*.deb
	rm ../python-lolram-doc_*.deb
	rm ../lolram_*.changes

