#!/bin/sh -e

stop torwuf-service || true
rm -rf /opt/torwuf/build/torwuf
echo "before_remove script done"
