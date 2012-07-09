#!/bin/sh

PYTHONPATH="$PYTHONPATH:../src/py3:../../../../lolram/main/src/py3" \
	python3 ../src/py3/torwuf/website \
	--config local_test2.conf --config-glob "local_test2.*.conf" \
	--legacy-args "../src/py3/torwuf/deprecated --config local_test.conf \
	--config-glob \"local_test.*.conf\" \
	--debug-mode --rpc-server --python-2-path ../src/py2" $@

