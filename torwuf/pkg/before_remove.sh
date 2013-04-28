#!/bin/sh -e

stop torwuf-service || true
/opt/torwuf/bin/python3 -m pip uninstall torwuf
rm -rf /opt/torwuf/build/torwuf
echo "before_remove script done"
