PYTHON_DIR="${DESTDIR}/usr/share/pyshared/"
PYTHON3_DIR="${DESTDIR}/usr/lib/python3/dist-packages"
CHANGELOG_FILENAME="debian/changelog"
CHANGELOG := ${CHANGELOG_FILENAME}

all: build

clean: clean-bytecode clean-backup-files

clean-bytecode:
	find python2/src/ -name '*.py[co]' -delete
	find python3/src/ -type d -name '__pycache__' -exec rm -r {} +

clean-destdir:
	rm -R ${DESTDIR}

clean-backup-files:
	find python2/src/ -name '*~' -delete
	find python3/src/ -name '*~' -delete

clean-unneeded-files: clean-bytecode clean-backup-files

build:

install: install-python-torwuf install-service

install-python-torwuf:
	mkdir -p ${DESTDIR}/usr/share/torwuf
	cp -r python3/src/* ${DESTDIR}/usr/share/torwuf

install-service:
	mkdir -p ${DESTDIR}/usr/sbin/
	cp scripts/torwuf-service ${DESTDIR}/usr/sbin/
	mkdir -p ${DESTDIR}/etc/
	cp -r etc/* ${DESTDIR}/etc/
	
deb-package: clean-unneeded-files make-auto-changelog
	dpkg-buildpackage -b -uc

MESSAGE="Scripted build. Revision `(bzr nick && bzr revno) || (git name-rev --name-only HEAD && git rev-parse HEAD)`"
make-auto-changelog:
	rm -f ${CHANGELOG_FILENAME}
	debchange --changelog ${CHANGELOG_FILENAME} --preserve \
		--newversion `cat VERSION`-upstream`date --utc "+%Y%m%d%H%M%S"` \
		--distribution UNRELEASED --force-distribution \
		--create ${MESSAGE} --package torwuf

