PYTHON_DIR="${DESTDIR}/usr/share/pyshared/"
PYTHON3_DIR="${DESTDIR}/usr/lib/python3/dist-packages"
CHANGELOG_FILENAME="debian.upstream/changelog"
CHANGELOG := ${CHANGELOG_FILENAME}

all: build

clean: clean-bytecode clean-backup-files

build: build-doc

install: install-lolram  install-lolram3

build-doc:
	epydoc python2/src/lolram* -o html
	epydoc python3/src/lolram* -o html3

clean-bytecode:
	find python2/src/ -name '*.py[co]' -delete
	find python3/src/ -type d -name '__pycache__' -exec rm -r {} +

clean-destdir:
	rm -R ${DESTDIR}

clean-backup-files:
	find python2/src/ -name '*~' -delete
	find python3/src/ -name '*~' -delete

clean-unneeded-files: clean-bytecode clean-backup-files

install-lolram: clean-unneeded-files
	mkdir -p ${PYTHON_DIR}
	cp -r python2/src/lolram ${PYTHON_DIR}
	
install-lolram3: clean-unneeded-files
	mkdir -p ${PYTHON3_DIR}
	cp -r python3/src/lolram ${PYTHON3_DIR}

deb-package: clean-unneeded-files make-auto-changelog
	ln -s -T debian.upstream debian || true
	dpkg-buildpackage -b -uc

make-auto-changelog:
	./make_auto_changelog.py --source-package=lolram python-lolram python3-lolram python-lolram-source

deb-clean-packages:
	rm ../python-lolram_*.deb
	rm ../python3-lolram_*.deb
	rm ../python-lolram-doc_*.deb
	rm ../lolram_*.changes
