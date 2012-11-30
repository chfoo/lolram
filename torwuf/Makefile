PYTHON_DIR="${DESTDIR}/usr/share/pyshared/"
PYTHON3_DIR="${DESTDIR}/usr/lib/python3/dist-packages"
CHANGELOG_FILENAME="debian/changelog"
CHANGELOG := ${CHANGELOG_FILENAME}

all: build

clean: clean-bytecode clean-backup-files

clean-bytecode:
#	find src/py2/ -name '*.py[co]' -delete
	find src/py3/ -type d -name '__pycache__' -exec rm -r {} +

clean-destdir:
	rm -R ${DESTDIR}

clean-backup-files:
#	find src/py2/ -name '*~' -delete
	find src/py3/ -name '*~' -delete

clean-unneeded-files: clean-bytecode clean-backup-files

build:

install: install-python3-torwuf install-service install-data

install-python3-torwuf:
	mkdir -p ${DESTDIR}/usr/share/torwuf/python3
	cp -r src/py3/* ${DESTDIR}/usr/share/torwuf/python3
	
install-python2-torwuf:
	mkdir -p ${DESTDIR}/usr/share/torwuf/python2
	cp -r src/py2/* ${DESTDIR}/usr/share/torwuf/python2

install-service:
	mkdir -p ${DESTDIR}/usr/sbin/
	cp scripts/torwuf-*service* ${DESTDIR}/usr/sbin/
	mkdir -p ${DESTDIR}/etc/
	cp -r etc/* ${DESTDIR}/etc/

install-data:
	mkdir -p ${DESTDIR}/usr/share/torwuf-data
	cp -r share/* ${DESTDIR}/usr/share/torwuf-data

deb-package: clean-unneeded-files make-auto-changelog
	debuild -b -uc -us

MESSAGE="Scripted build. Revision `(bzr nick && bzr revno) || (git name-rev --name-only HEAD && git rev-parse HEAD)`"
make-auto-changelog:
	rm -f ${CHANGELOG_FILENAME}
	debchange --changelog ${CHANGELOG_FILENAME} --preserve \
		--newversion `cat VERSION`-upstream`date --utc "+%Y%m%d%H%M%S"` \
		--distribution UNRELEASED --force-distribution \
		--create ${MESSAGE} --package torwuf

deb-clean-packages:
	rm -f ../torwuf*.deb
	rm -f ../torwuf*.changes
	rm -f ../torwuf*.build
