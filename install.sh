#!/bin/sh

locationOfScript=$(dirname "$(readlink -e "$0")")

sed -i "s|INSTDIR|$locationOfScript|" fritzCallMon.service
cp fritzCallMon.service /etc/systemd/system/fritzCallMon.service
chmod +x /etc/systemd/system/fritzCallMon.service
chown root:root /etc/systemd/system/fritzCallMon.service
systemctl daemon-reload
systemctl enable fritzCallMon.service
systemctl start fritzCallMon.service

sed -i "s|INSTDIR|$locationOfScript|" fritzBot.service
cp fritzBot.service /etc/systemd/system/fritzBot.service
chmod +x /etc/systemd/system/fritzBot.service
chown root:root /etc/systemd/system/fritzBot.service
systemctl daemon-reload
systemctl enable fritzBot.service
systemctl start fritzBot.service
