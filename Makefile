DESTDIR="out"
PYTHON_DIR="${DESTDIR}/usr/share/pyshared/"

clean: clean-bytecode clean-backup-files

install: install-lolram install-third-party install-lolram3

build: build-doc

build-doc:
	mkdir -p ${DESTDIR}
	epydoc src/lolram* -o ${DESTDIR}/html

clean-bytecode:
	find src/ -name '*.py[co]' -delete

clean-destdir:
	rm -R ${DESTDIR}

clean-backup-files:
	find src/ -name '*~' -delete

clean-unneeded-files: clean-bytecode clean-backup-files

install-lolram: clean-unneeded-files
	mkdir -p ${PYTHON_DIR}
	cp -r src/lolram src/lolram_deprecated_* ${PYTHON_DIR}
	
install-lolram3: clean-unneeded-files
	mkdir -p ${PYTHON_DIR}
	cp -r src/lolram3 ${PYTHON_DIR}
	
install-third-party: clean-unneeded-files
	mkdir -p ${PYTHON_DIR}
	cp -r third-party/bitstring*/bitstring \
		third-party/iso8601*/iso8601 \
		third-party/sqlamp*/sqlamp \
		third-party/tornado*/tornado \
		third-party/urllib3*/urllib3 \
		${PYTHON_DIR}
	rm ${PYTHON_DIR}/iso8601/.??*

deb-package: clean-unneeded-files increment-version
	ln -s -T debian.upstream debian || true
	dpkg-buildpackage -b

MESSAGE="Scripted build. Revision `(bzr nick && bzr revno) || (git name-rev --name-only HEAD && git rev-parse HEAD)`"
increment-version:
	debchange --preserve --newversion `cat VERSION`-upstream`date --utc "+%Y%m%d%H%M%S"` --distribution unstable --force-distribution ${MESSAGE}
	
	
