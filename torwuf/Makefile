PREFIX?=/usr/local
DESTDIR?=
PYTHON3?=python3.2
PIP3?=pip-3.2

.PHONY: all clean build install package package-lib

all: build

clean:
	$(PYTHON3) setup.py clean --all
	rm -rf build/ build-bundle/ build-bundle[0-9]/ destdir/

build:
	$(PYTHON3) setup.py build

install:
	$(PYTHON3) setup.py install --prefix $(DESTDIR)/$(PREFIX)
	mkdir -p $(DESTDIR)/etc/nginx/sites-available/ \
		$(DESTDIR)/$(PREFIX)/sbin/ \
		$(DESTDIR)/$(PREFIX)/share/ \
		$(DESTDIR)/etc/init/ \
		$(DESTDIR)/etc/cron.d/ \
		$(DESTDIR)/etc/torwuf/
	cp etc/nginx/sites-available/50-torwuf $(DESTDIR)/etc/nginx/sites-available/50-torwuf
	cp etc/torwuf/*[!~] $(DESTDIR)/etc/torwuf/
	cp etc/cron.d/*[!~] $(DESTDIR)/etc/cron.d/
	cp sbin/torwuf-service $(DESTDIR)/$(PREFIX)/sbin/
	cp sbin/torwuf-service-backup $(DESTDIR)/$(PREFIX)/sbin/
	cp -r share/* $(DESTDIR)/$(PREFIX)/share/
	cp etc/init/torwuf-service.conf $(DESTDIR)/etc/init/

build/torwuf_lib.pybundle: requirements.txt
	mkdir -p build/
	$(PIP3) bundle build/torwuf_lib.pybundle -r requirements.txt \
		--use-mirrors --download-cache download-cache/

download-cache/virtualenv-1.9.1.tar.gz:
	mkdir -p download-cache/
	curl - https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.9.1.tar.gz \
		-o download-cache/virtualenv-1.9.1.tar.gz

package-lib: build/torwuf_lib.pybundle download-cache/virtualenv-1.9.1.tar.gz
	$(eval DESTDIR=destdir/)
	$(eval PREFIX=/opt/torwuf/)
	rm -rf destdir/
	mkdir -p $(DESTDIR)/$(PREFIX)/share/
	cp build/torwuf_lib.pybundle $(DESTDIR)/$(PREFIX)/share/
	tar --extract --strip-components=1 \
		--file=download-cache/virtualenv-1.9.1.tar.gz \
		-C $(DESTDIR)/$(PREFIX)/share/ virtualenv-1.9.1/virtualenv.py
	fpm -C $(DESTDIR) -t deb -s dir -n torwuf-lib -v 1.0 \
		-d build-essential \
		-d python3-dev \
		--after-install pkg/lib/after_install.sh \
		.

package: 
	$(eval DESTDIR=destdir/)
	$(eval PREFIX=/opt/torwuf/)
	rm -rf destdir/
	$(MAKE) build install DESTDIR=$(DESTDIR) PREFIX=$(PREFIX)
	fpm -C $(DESTDIR) -t deb -s dir -n torwuf -v `cat -s VERSION` \
		--deb-user root --deb-group root \
		-d python3 \
		-d python3-docutils \
		-d loggerhead \
		-d mongodb \
		-d sqlite3 \
		-d imagemagick \
		-d nginx \
		-d spawn-fcgi \
		-d multiwatch \
		-d torwuf-lib \
		--config-files /etc/cron.d/torwuf-service \
		--config-files /etc/init/torwuf-redmine-service.conf \
		--config-files /etc/init/torwuf-service.conf \
		--config-files /etc/init.d/torwuf-gitlab-service \
		--config-files /etc/nginx/sites-available/50-torwuf \
		--config-files /etc/torwuf/server.crt \
		--config-files /etc/torwuf/server.key \
		--config-files /etc/torwuf/torwuf.conf \
		--config-files /etc/torwuf/torwuf.private.conf \
		--after-install pkg/after_install.sh \
		--before-remove pkg/before_remove.sh \
		.

