#!/bin/sh

PYTHONPATH="$PYTHONPATH:../python3/src:../../../../lolram/main/python3/src" \
	python3 ../python3/src/torwuf/ --config local_test.conf \
	--config-glob "local_test.*.conf" \
	--debug-mode --rpc-server --python-2-path ../python2/src/ $@

