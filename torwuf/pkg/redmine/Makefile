.PHONY: all package

all:

clean:
	rm -rf destdir/

package:
	mkdir -p destdir/etc/init/
	cp ../../etc/init/torwuf-redmine-service.conf destdir/etc/init/
	chmod 0644 destdir/etc/init/torwuf-redmine-service.conf
	
	fpm -C destdir/ -t deb -s dir -n torwuf-redmine-service -v \
		1.0 \
		--config-files /etc/init/torwuf-redmine-service.conf \
		--after-install after_install.sh \
		--before-remove before_remove.sh \
		-d torwuf \
		.
