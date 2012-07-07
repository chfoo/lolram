PYTHON_DIR="${DESTDIR}/usr/share/pyshared/"
PYTHON3_DIR="${DESTDIR}/usr/lib/python3/dist-packages"
CHANGELOG_FILENAME="debian.upstream/changelog"
CHANGELOG := ${CHANGELOG_FILENAME}

all: build

clean: clean-bytecode clean-backup-files
	rm -R -f html
	rm -R -f html3

build: build-doc

install: install-lolram  install-lolram3

build-doc:
	epydoc src/py2/lolram* -o html
	# TODO: epydoc python3 support not yet available 
	#	epydoc src/py3/lolram* -o html3

clean-bytecode:
	find src/py2/ -name '*.py[co]' -delete
	find src/py3/ -type d -name '__pycache__' -exec rm -r {} +

clean-destdir:
	rm -R ${DESTDIR}

clean-backup-files:
	find src/py2/ -name '*~' -delete
	find src/py3 -name '*~' -delete

clean-unneeded-files: clean-bytecode clean-backup-files

install-lolram: clean-unneeded-files
	mkdir -p ${PYTHON_DIR}
	cp -r src/py2/lolram ${PYTHON_DIR}
	
install-lolram3: clean-unneeded-files
	mkdir -p ${PYTHON3_DIR}
	cp -r src/py3/lolram ${PYTHON3_DIR}

deb-package: clean-unneeded-files make-auto-changelog
	ln -s -T debian.upstream debian || true
	dpkg-buildpackage -b -uc

MESSAGE="Scripted build. Revision `(bzr nick && bzr revno) || (git name-rev --name-only HEAD && git rev-parse HEAD)`"
make-auto-changelog:
	rm -f ${CHANGELOG_FILENAME}
	debchange --changelog ${CHANGELOG_FILENAME} --preserve \
		--newversion `cat VERSION`-upstream`date --utc "+%Y%m%d%H%M%S"` \
		--distribution UNRELEASED --force-distribution \
		--create ${MESSAGE} --package lolram

deb-clean-packages:
	rm ../python-lolram_*.deb
	rm ../python3-lolram_*.deb
	rm ../python-lolram-doc_*.deb
	rm ../lolram_*.changes

deb-package-torwuf:
	make -C torwuf/ deb-package

