.PHONY: all package

all:

clean:
	rm -rf destdir/

package:
	mkdir -p destdir/etc/init.d/
	cp ../../etc/init.d/torwuf-gitlab-service destdir/etc/init.d/
	chmod 0755 destdir/etc/init.d/torwuf-gitlab-service
	
	fpm -C destdir/ -t deb -s dir -n torwuf-gitlab-service -v \
		`cat -s ../../VERSION` \
		--config-files /etc/init.d/torwuf-gitlab-service \
		--after-install after_install.sh \
		--before-remove before_remove.sh \
		--after-remove after_remove.sh \
		-d torwuf \
		.
