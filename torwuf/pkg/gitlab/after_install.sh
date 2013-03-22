#!/bin/sh -e

update-rc.d torwuf-gitlab-service defaults 99
invoke-rc.d torwuf-gitlab-service start
