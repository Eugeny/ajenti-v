#!/bin/bash
scp dist/*.deb root@ajenti.org:/srv/repo/debian/
ssh root@ajenti.org /srv/repo/rebuild-debian.sh

scp dist/*.rpm root@ajenti.org:/srv/repo/centos/repo
ssh root@ajenti.org /srv/repo/rebuild-centos.sh

ssh root@ajenti.org /srv/repo/publish.py
