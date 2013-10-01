#!/bin/bash
scp dist/*.deb root@ajenti.org:/srv/repo/debian/
ssh root@ajenti.org /srv/repo/rebuild-debian.sh
ssh root@ajenti.org /srv/repo/publish.py
