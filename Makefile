DESTDIR="out"
PYTHON_DIR="${DESTDIR}/usr/share/pyshared/"
PYTHON3_DIR="${DESTDIR}/usr/lib/python3/dist-packages"

clean: clean-bytecode clean-backup-files

install: install-lolram install-third-party install-lolram3

build: build-doc download build-iso8601 build-sqlamp build-urllib3

download: download-bitstring download-iso8601 download-sqlamp download-urllib3 download-tornado

build-doc:
	mkdir -p ${DESTDIR}
	epydoc src/lolram* -o ${DESTDIR}/html

clean-bytecode:
	find python2/src/ -name '*.py[co]' -delete
	find python3/src/ -type d -name '__pycache__' -exec rm -r {} +

clean-destdir:
	rm -R ${DESTDIR}

clean-backup-files:
	find python2/src/ -name '*~' -delete
	find python3/src/ -name '*~' -delete

clean-unneeded-files: clean-bytecode clean-backup-files

download-bitstring:
	./third_party_download.py bitstring

download-sqlamp:
	./third_party_download.py sqlamp

download-iso8601:
	./third_party_download.py iso8601

download-urllib3:
	./third_party_download.py urllib3

download-tornado:
	./third_party_download.py tornado || true
	wget "http://github.com/downloads/facebook/tornado/tornado-`cat third-party/tornado.version`.tar.gz" -O "third-party/tornado-`cat third-party/tornado.version`.tar.gz"

install-lolram: clean-unneeded-files
	mkdir -p ${PYTHON_DIR}
	cp -r python2/src/lolram python2/src/lolram_deprecated_* ${PYTHON_DIR}
	
install-lolram3: clean-unneeded-files
	mkdir -p ${PYTHON3_DIR}
	cp -r python3/src/lolram ${PYTHON3_DIR}

install-bitstring:
	mkdir -p ${PYTHON_DIR}
	mkdir -p ${PYTHON3_DIR}
	$(eval VER=`cat third-party/bitstring.version`)
	cp -r third-party/bitstring-${VER}/bitstring ${PYTHON_DIR}
	cp -r third-party/bitstring-${VER}/bitstring ${PYTHON3_DIR}

build-iso8601:
	$(eval VER=`cat third-party/iso8601.version`)
	cp -r third-party/iso8601-${VER}/ third-party/iso8601-${VER}-python3/
	2to3 -w third-party/iso8601-${VER}-python3/iso8601

install-iso8601:
	mkdir -p ${PYTHON_DIR}
	mkdir -p ${PYTHON3_DIR}
	$(eval VER=`cat third-party/iso8601.version`)
	cp -r third-party/bitstring-${VER}/iso8601 ${PYTHON_DIR}
	cp -r third-party/bitstring-${VER}-python3/iso8601 ${PYTHON3_DIR}

build-sqlamp:
	$(eval VER=`cat third-party/sqlamp.version`)
	cp -r third-party/sqlamp-${VER}/ third-party/sqlamp-${VER}-python3/
	2to3 -w third-party/sqlamp-${VER}-python3/sqlamp

install-sqlamp:
	mkdir -p ${PYTHON_DIR}
	mkdir -p ${PYTHON3_DIR}
	$(eval VER=`cat third-party/sqlamp.version`
	cp -r third-party/sqlamp-${VER}/sqlamp ${PYTHON_DIR}
	cp -r third-party/sqlamp-${VER}-python3/sqlamp ${PYTHON3_DIR}

build-urllib3:
	$(eval VER=`cat third-party/urllib3.version`
	cp -r third-party/urllib3-${VER}/ third-party/urllib3-${VER}-python3/
	2to3 -w third-party/urllib3-${VER}-python3/urllib3

install-urllib3:
	mkdir -p ${PYTHON_DIR}
	mkdir -p ${PYTHON3_DIR}
	$(eval VER=`cat third-party/urllib3.version`
	cp -r third-party/urllib3-${VER}/urllib3 ${PYTHON_DIR}
	cp -r third-party/urllib3-${VER}-python3/urllib3 ${PYTHON3_DIR}

install-tornado:
	mkdir -p ${PYTHON_DIR}
	mkdir -p ${PYTHON3_DIR}
	$(eval VER=`cat third-party/tornado.version`
	cp -r third-party/tornado-${VER}/tornado ${PYTHON_DIR}
	cp -r third-party/tornado-${VER}/tornado ${PYTHON3_DIR}

install-third-party: clean-unneeded-files install-bitstring install-iso8601 install-sqlamp install-urllib3 install-tornado
#	mkdir -p ${PYTHON_DIR}
#	cp -r third-party/bitstring*/bitstring \
#		third-party/iso8601*/iso8601 \
#		third-party/sqlamp*/sqlamp \
#		third-party/tornado*/tornado \
#		third-party/urllib3*/urllib3 \
#		${PYTHON_DIR}
#	rm ${PYTHON_DIR}/iso8601/.??*

deb-package: clean-unneeded-files increment-version update-third-party-versions
	ln -s -T debian.upstream debian || true
	dpkg-buildpackage -b -uc

MESSAGE="Scripted build (lolram). Revision `(bzr nick && bzr revno) || (git name-rev --name-only HEAD && git rev-parse HEAD)`"
increment-version:
	debchange --preserve --newversion `cat VERSION`-upstream`date --utc "+%Y%m%d%H%M%S"` --distribution unstable --force-distribution ${MESSAGE}

update-third-party-versions: update-version-bitstring update-version-iso8601 update-version-sqlamp update-version-urllib3  update-version-tornado

update-version-bitstring: 
	$(eval VER=`cat third-party/bitstring.version`)
	debchange --preserve --newversion "${VER}~lolram" --distribution unstable \
		--force-distribution ${MESSAGE} \
		--changelog debian/python-bitstring.changelog

update-version-iso8601: 
	$(eval VER=`cat third-party/iso8601.version`)
	debchange --preserve --newversion "${VER}~lolram" --distribution unstable \
		--force-distribution ${MESSAGE} \
		--changelog debian/python-iso8601.changelog

update-version-sqlamp: 
	$(eval VER=`cat third-party/sqlamp.version`)
	debchange --preserve --newversion "${VER}~lolram" --distribution unstable \
		--force-distribution ${MESSAGE} \
		--changelog debian/python-sqlamp.changelog

update-version-urllib3: 
	$(eval VER=`cat third-party/urllib3.version`)
	debchange --preserve --newversion "${VER}~lolram" --distribution unstable \
		--force-distribution ${MESSAGE} \
		--changelog debian/python-urllib3.changelog

update-version-tornado: 
	$(eval VER=`cat third-party/tornado.version`)
	debchange --preserve --newversion "${VER}~lolram" --distribution unstable \
		--force-distribution ${MESSAGE} \
		--changelog debian/python-tornado.changelog


