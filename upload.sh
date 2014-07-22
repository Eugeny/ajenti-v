#!/bin/bash
scp dist/*.deb root@ajenti.org:/srv/repo/debian/
ssh root@ajenti.org /srv/repo/rebuild-debian.sh

scp dist/*.rpm root@ajenti.org:/srv/repo/centos/repo6
scp dist/*.rpm root@ajenti.org:/srv/repo/centos/repo7
ssh root@ajenti.org /srv/repo/rebuild-centos.sh
ssh root@ajenti.org /srv/repo/rebuild-centos7.sh

#ssh root@ajenti.org /srv/repo/publish.py
