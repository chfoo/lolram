#!/bin/sh

PYTHONPATH="$PYTHONPATH:../src/py3/" \
	python3 -m torwuf \
	--config local_test.conf --debug --host 0.0.0.0 $@

